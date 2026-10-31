"""Confere um conjunto de treino de voz frase por frase, para separar os áudios bons dos ruins
antes do treino do Piper.

Para cada .wav: o Whisper transcreve e o texto é comparado com o esperado (palavra trocada,
faltando ou sobrando), e o áudio é medido (ritmo da fala, silêncios longos, volume, distorção).
O Whisper corrige sotaque ao transcrever ("houje" vira "hoje"), então pronúncia estranha ainda
pede ouvido; o resto ele pega bem.
"""

from __future__ import annotations

import csv
import difflib
import re
import shutil
import statistics
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from nora.audio import _para_mono, ler_wav, para_wav, reamostrar_qualidade
from nora.dataset_voz import DESCARTADAS, descartadas

_PALAVRA = re.compile(r"[a-z0-9]+")

# Limites (ajustados para frases curtas de assistente, 1 a 10 s)
ACERTO_BOM = 0.85
ACERTO_RUIM = 0.6
SILENCIO_PONTA_S = 1.0
PAUSA_LONGA_S = 1.5
RITMO_LIMITE = 1.6  # vezes a mediana do conjunto (para mais ou para menos)
RITMO_RUIM = 2.2
VOLUME_BAIXO_DB = -35.0
ESTOURO = 0.001  # fração de amostras no limite


def palavras(texto: str) -> list[str]:
    """Minúsculas, sem acento e sem pontuação: 'Você, hoje?' -> ['voce', 'hoje']."""
    sem_acento = unicodedata.normalize("NFD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return _PALAVRA.findall(sem_acento)


def acerto(esperado: str, ouvido: str) -> float:
    """Quanto da frase o Whisper ouviu igual (0 a 1), comparando palavra por palavra."""
    a, b = palavras(esperado), palavras(ouvido)
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


@dataclass
class Medidas:
    duracao: float
    fala: float  # segundos com voz (sem os silêncios)
    silencio_inicio: float
    silencio_fim: float
    maior_pausa: float
    volume_db: float
    estouro: float


def medir(amostras: bytes, taxa: int, quadro_s: float = 0.02) -> Medidas:
    """Mede o áudio PCM 16 bits mono em quadros de 20 ms."""
    import numpy

    sinal = numpy.frombuffer(amostras, dtype="<i2").astype(numpy.float64) / 32768.0
    duracao = len(sinal) / taxa
    tamanho = max(1, int(taxa * quadro_s))
    quadros = len(sinal) // tamanho
    if quadros == 0:
        return Medidas(duracao, 0.0, duracao, 0.0, 0.0, -120.0, 0.0)
    energia = numpy.sqrt((sinal[: quadros * tamanho].reshape(quadros, tamanho) ** 2).mean(axis=1))
    db = 20 * numpy.log10(numpy.maximum(energia, 1e-6))
    limiar = max(-50.0, float(db.max()) - 35.0)
    com_voz = numpy.flatnonzero(db > limiar)
    estouro = float(numpy.mean(numpy.abs(sinal) >= 32767 / 32768))
    if len(com_voz) == 0:
        return Medidas(duracao, 0.0, duracao, 0.0, 0.0, float(db.max()), estouro)
    pausas = numpy.diff(com_voz) - 1
    trecho = sinal[com_voz[0] * tamanho : (com_voz[-1] + 1) * tamanho]
    return Medidas(
        duracao=duracao,
        fala=len(com_voz) * quadro_s,
        silencio_inicio=com_voz[0] * quadro_s,
        silencio_fim=duracao - (com_voz[-1] + 1) * quadro_s,
        maior_pausa=float(pausas.max()) * quadro_s if len(pausas) else 0.0,
        volume_db=float(20 * numpy.log10(max(numpy.sqrt(numpy.mean(trecho**2)), 1e-6))),
        estouro=estouro,
    )


@dataclass
class Avaliacao:
    ident: str
    texto: str
    transcricao: str
    acerto: float
    medidas: Medidas
    ritmo: float  # letras por segundo de fala
    problemas: list[str] = field(default_factory=list)
    grave: bool = False

    @property
    def nota(self) -> str:
        if self.grave:
            return "ruim"
        return "conferir" if self.problemas else "boa"


def _julgar(av: Avaliacao, ritmo_mediano: float) -> None:
    m = av.medidas
    tem_numero = any(c.isdigit() for c in av.transcricao)
    if not av.transcricao:
        av.problemas.append("o Whisper não ouviu fala")
        av.grave = True
    elif av.acerto < ACERTO_RUIM and not tem_numero:
        av.problemas.append("palavras trocadas, faltando ou sobrando")
        av.grave = True
    elif av.acerto < ACERTO_BOM:
        av.problemas.append(
            "números: confira de ouvido" if tem_numero else "alguma palavra diferente"
        )
    if m.duracao < 0.6:
        av.problemas.append("curto demais")
        av.grave = True
    if ritmo_mediano and av.ritmo:
        proporcao = av.ritmo / ritmo_mediano
        if proporcao > RITMO_LIMITE:
            av.problemas.append("rápida demais (cortou ou engoliu palavras?)")
            av.grave = av.grave or proporcao > RITMO_RUIM
        elif proporcao < 1 / RITMO_LIMITE:
            av.problemas.append("lenta demais (arrastou ou repetiu?)")
            av.grave = av.grave or proporcao < 1 / RITMO_RUIM
    if m.silencio_inicio > SILENCIO_PONTA_S:
        av.problemas.append(f"silêncio de {m.silencio_inicio:.1f} s no começo")
    if m.silencio_fim > SILENCIO_PONTA_S:
        av.problemas.append(f"silêncio de {m.silencio_fim:.1f} s no fim")
    if m.maior_pausa > PAUSA_LONGA_S:
        av.problemas.append(f"pausa de {m.maior_pausa:.1f} s no meio")
    if m.volume_db < VOLUME_BAIXO_DB:
        av.problemas.append("volume baixo")
    if m.estouro > ESTOURO:
        av.problemas.append("áudio estourado (distorção)")


def ler_metadata(pasta: Path) -> list[tuple[str, str]]:
    linhas = (pasta / "metadata.csv").read_text(encoding="utf-8").splitlines()
    return [
        (ident.removesuffix(".wav"), texto.strip())
        for ident, _, texto in (linha.partition("|") for linha in linhas if linha.strip())
    ]


def conferir(
    ouvido,
    pasta: Path,
    saida: Callable[[str], None] = print,
) -> list[Avaliacao]:
    """Avalia cada frase do conjunto. `ouvido` precisa de transcrever(wav) -> texto."""
    frases = ler_metadata(pasta)
    saida(f"Conferindo {len(frases)} frases (o Whisper ouve cada uma)...")
    avaliacoes = []
    for posicao, (ident, texto) in enumerate(frases, start=1):
        arquivo = pasta / "wavs" / f"{ident}.wav"
        if not arquivo.is_file():
            saida(f"  {ident}: sem áudio, pulada")
            continue
        wav = arquivo.read_bytes()
        amostras, taxa, canais = ler_wav(wav)
        amostras = _para_mono(amostras, canais)
        medidas = medir(amostras, taxa)
        para_ouvir = para_wav(reamostrar_qualidade(amostras, taxa, 16_000), 16_000)
        transcricao = ouvido.transcrever(para_ouvir)
        letras = len("".join(palavras(texto)))
        avaliacoes.append(
            Avaliacao(
                ident=ident,
                texto=texto,
                transcricao=transcricao,
                acerto=acerto(texto, transcricao),
                medidas=medidas,
                ritmo=letras / medidas.fala if medidas.fala else 0.0,
            )
        )
        if posicao % 20 == 0:
            saida(f"  {posicao}/{len(frases)}")
    ritmos = [av.ritmo for av in avaliacoes if av.ritmo]
    mediano = statistics.median(ritmos) if ritmos else 0.0
    for av in avaliacoes:
        _julgar(av, mediano)
    return avaliacoes


def salvar_relatorio(avaliacoes: list[Avaliacao], arquivo: Path) -> None:
    """Planilha (abre no Excel) com a pior frase primeiro."""
    ordem = {"ruim": 0, "conferir": 1, "boa": 2}
    with arquivo.open("w", encoding="utf-8-sig", newline="") as saida:
        escritor = csv.writer(saida, delimiter=";")
        escritor.writerow(["arquivo", "nota", "acerto", "problemas", "texto", "o Whisper ouviu"])
        for av in sorted(avaliacoes, key=lambda a: (ordem[a.nota], a.acerto)):
            escritor.writerow(
                [
                    f"{av.ident}.wav",
                    av.nota,
                    f"{av.acerto:.0%}",
                    "; ".join(av.problemas),
                    av.texto,
                    av.transcricao,
                ]
            )


def descartar(pasta: Path, idents: list[str]) -> None:
    """Tira os áudios do conjunto (vão para descartadas/) e do metadata.csv, e anota para o
    gerar-dataset não refazê-los iguais."""
    if not idents:
        return
    destino = pasta / "descartadas"
    destino.mkdir(exist_ok=True)
    for ident in idents:
        wav = pasta / "wavs" / f"{ident}.wav"
        if wav.is_file():
            shutil.move(str(wav), destino / wav.name)
    lista = sorted(descartadas(pasta) | set(idents))
    (pasta / DESCARTADAS).write_text("\n".join(lista) + "\n", encoding="utf-8")
    fora = set(idents)
    linhas = [f"{ident}|{texto}" for ident, texto in ler_metadata(pasta) if ident not in fora]
    (pasta / "metadata.csv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
