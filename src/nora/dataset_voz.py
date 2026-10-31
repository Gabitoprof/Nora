"""Gera um conjunto de treino de voz (formato LJSpeech, o que o treino do Piper usa) falando
muitas frases com a voz configurada, por exemplo um fluxo seu do ComfyUI.

Saída: <pasta>/wavs/0001.wav ... (mono, 16 bits, 22.050 Hz) e <pasta>/metadata.csv com
"0001|texto da frase". Pode ser interrompido: na próxima vez continua de onde parou.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from pathlib import Path

from nora.audio import _para_mono, duracao_wav, ler_wav, para_wav, reamostrar_qualidade

TAXA_DO_PIPER = 22_050
DESCARTADAS = "descartadas.txt"
_FIM_DE_FRASE = re.compile(r"(?<=[.!?…])\s+")


def frases_de_texto(texto: str, minimo: int = 20, maximo: int = 180) -> list[str]:
    """Corta um texto corrido (ex.: um livro de domínio público) em frases boas para treino:
    nem curtas demais, nem longas demais, sem repetidas."""
    vistas, frases = set(), []
    for bloco in texto.splitlines():
        for frase in _FIM_DE_FRASE.split(bloco):
            frase = " ".join(frase.split()).strip(" -—–\"'“”")
            if minimo <= len(frase) <= maximo and frase not in vistas:
                vistas.add(frase)
                frases.append(frase)
    return frases


def ler_frases(arquivo: Path, uma_por_linha: bool) -> list[str]:
    texto = arquivo.read_text(encoding="utf-8")
    if uma_por_linha:
        linhas = (" ".join(linha.split()) for linha in texto.splitlines())
        return list(dict.fromkeys(linha for linha in linhas if linha and not linha.startswith("#")))
    return frases_de_texto(texto)


def gerar_dataset(
    voz,
    frases: list[str],
    pasta: Path,
    saida: Callable[[str], None] = print,
) -> int:
    """Fala cada frase com a voz dada e salva no formato do treino. Devolve quantas gerou."""
    wavs = pasta / "wavs"
    wavs.mkdir(parents=True, exist_ok=True)
    # As que o conferir-dataset descartou não são refeitas (sairiam iguais, com a mesma semente).
    fora = descartadas(pasta)
    pendentes, puladas = [], 0
    for numero, frase in enumerate(frases, start=1):
        if f"{numero:04}" in fora:
            puladas += 1
        elif not (wavs / f"{numero:04}.wav").is_file():
            pendentes.append((numero, frase))
    prontas = len(frases) - len(pendentes) - puladas
    aviso = f", {puladas} descartadas" if puladas else ""
    saida(f"{len(frases)} frases; {prontas} já prontas{aviso}, {len(pendentes)} a gerar.")
    inicio, geradas, segundos = time.perf_counter(), 0, 0.0
    for posicao, (numero, frase) in enumerate(pendentes, start=1):
        amostras, taxa, canais = ler_wav(voz.sintetizar(frase))
        amostras = _para_mono(amostras, canais)
        wav = para_wav(reamostrar_qualidade(amostras, taxa, TAXA_DO_PIPER), TAXA_DO_PIPER)
        (wavs / f"{numero:04}.wav").write_bytes(wav)
        geradas += 1
        segundos += duracao_wav(wav)
        decorrido = time.perf_counter() - inicio
        restante = decorrido / posicao * (len(pendentes) - posicao)
        saida(f"  {numero:04}  {frase[:60]}  (faltam ~{restante / 60:.0f} min)")
    _escrever_metadata(pasta, frases)
    saida(f"Pronto: {geradas} novas ({segundos / 60:.1f} min de fala). Conjunto em {pasta}")
    return geradas


def descartadas(pasta: Path) -> set[str]:
    """Números das frases tiradas pelo conferir-dataset (descartadas.txt)."""
    arquivo = pasta / DESCARTADAS
    if not arquivo.is_file():
        return set()
    return {linha.strip() for linha in arquivo.read_text(encoding="utf-8").splitlines() if linha}


def _escrever_metadata(pasta: Path, frases: list[str]) -> None:
    """metadata.csv só com as frases que têm áudio, no formato 'id|texto'."""
    linhas = [
        f"{numero:04}|{frase.replace('|', ' ')}"
        for numero, frase in enumerate(frases, start=1)
        if (pasta / "wavs" / f"{numero:04}.wav").is_file()
    ]
    (pasta / "metadata.csv").write_text("\n".join(linhas) + "\n", encoding="utf-8")
