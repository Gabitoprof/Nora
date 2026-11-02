from types import SimpleNamespace

import pytest

from nora.audio import ler_wav, para_wav
from nora.cli import comando_conferir_dataset
from nora.config import carregar
from nora.dataset_voz import gerar_dataset

numpy = pytest.importorskip("numpy")

from nora.conferir_dataset import acerto, conferir, descartar, medir, palavras  # noqa: E402

TAXA = 22_050


def fala(segundos: float, antes: float = 0.1, depois: float = 0.1) -> bytes:
    """Um 'áudio de fala' falso: tom com volume variando, entre silêncios."""
    t = numpy.arange(int(TAXA * segundos)) / TAXA
    tom = 0.3 * numpy.sin(2 * numpy.pi * 220 * t) * (0.6 + 0.4 * numpy.sin(2 * numpy.pi * 3 * t))
    sinal = numpy.concatenate(
        [numpy.zeros(int(TAXA * antes)), tom, numpy.zeros(int(TAXA * depois))]
    )
    return para_wav(numpy.round(sinal * 32767).astype("<i2").tobytes(), TAXA)


class OuvidoFalso:
    """Devolve a transcrição combinada para cada duração de áudio (16 kHz)."""

    def __init__(self, respostas):
        self.respostas = respostas
        self.pedidos = 0

    def transcrever(self, wav):
        _, taxa, _ = ler_wav(wav)
        assert taxa == 16_000
        resposta = self.respostas[self.pedidos]
        self.pedidos += 1
        return resposta


def montar(pasta, itens):
    (pasta / "wavs").mkdir(parents=True)
    linhas = []
    for numero, (texto, wav) in enumerate(itens, start=1):
        (pasta / "wavs" / f"{numero:04}.wav").write_bytes(wav)
        linhas.append(f"{numero:04}|{texto}")
    (pasta / "metadata.csv").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def test_compara_palavras_sem_acento_nem_pontuacao():
    assert palavras("Você, HOJE?") == ["voce", "hoje"]
    assert acerto("Você quer vir junto?", "voce quer vir junto") == 1.0
    assert acerto("Hoje de manhã eu vou.", "Hoje eu vou.") < 0.85
    assert acerto("Bom dia!", "") == 0.0


def test_mede_silencios_e_fala():
    amostras, taxa, _ = ler_wav(fala(1.0, antes=1.5, depois=0.2))
    medidas = medir(amostras, taxa)
    assert medidas.silencio_inicio == pytest.approx(1.5, abs=0.05)
    assert medidas.silencio_fim == pytest.approx(0.2, abs=0.05)
    assert medidas.fala == pytest.approx(1.0, abs=0.05)
    assert medidas.estouro == 0.0


def test_separa_boas_ruins_e_para_ouvir_e_descarta(tmp_path):
    pasta = tmp_path / "voz"
    textos = [
        "Bom dia, tudo bem com você?",
        "Hoje o céu está limpo e bonito.",
        "Vamos revisar a matéria de cálculo?",
        "A chuva fina deixou o jardim perfumado.",
    ]
    montar(
        pasta,
        [
            (textos[0], fala(1.6)),
            (textos[1], fala(1.8)),
            (textos[2], fala(1.8)),
            (textos[3], fala(2.0, antes=1.4)),
        ],
    )
    ouvido = OuvidoFalso([textos[0], textos[1], "o gato subiu no telhado", textos[3]])
    avaliacoes = conferir(ouvido, pasta, saida=lambda _: None)
    notas = [av.nota for av in avaliacoes]
    assert notas == ["boa", "boa", "ruim", "conferir"]
    assert "silêncio de 1.4 s no começo" in avaliacoes[3].problemas

    descartar(pasta, ["0003"])
    assert (pasta / "descartadas" / "0003.wav").is_file()
    assert not (pasta / "wavs" / "0003.wav").exists()
    assert "0003|" not in (pasta / "metadata.csv").read_text(encoding="utf-8")

    class Voz:
        falas = []

        def sintetizar(self, frase):
            self.falas.append(frase)
            return fala(1.0)

    voz = Voz()
    gerar_dataset(voz, textos, pasta, saida=lambda _: None)
    assert voz.falas == []  # a descartada não é refeita
    assert "0003|" not in (pasta / "metadata.csv").read_text(encoding="utf-8")


def test_comando_conferir(criar_raiz, capsys):
    config = carregar(criar_raiz(), ambiente={})
    pasta = config.pasta_dados / "dataset_voz" / "teste"
    montar(pasta, [("Uma frase boa aqui.", fala(1.2)), ("Outra frase boa.", fala(1.0))])
    ouvido = OuvidoFalso(["Uma frase boa aqui.", "nada a ver com isso mesmo"])
    args = SimpleNamespace(nome="teste", descartar=True)
    assert comando_conferir_dataset(config, args, ouvido) == 0
    saida = capsys.readouterr().out
    assert "1 boas, 0 para ouvir, 1 ruins" in saida
    assert (pasta / "conferencia.csv").read_text(encoding="utf-8-sig").startswith("arquivo;nota")
    assert (pasta / "descartadas" / "0002.wav").is_file()
    assert comando_conferir_dataset(config, SimpleNamespace(nome="nada", descartar=False)) == 1


def test_tirar_frases_escolhidas_sem_conferir(criar_raiz, capsys):
    config = carregar(criar_raiz(), ambiente={})
    pasta = config.pasta_dados / "dataset_voz" / "teste"
    montar(pasta, [("Uma.", fala(1.0)), ("Duas.", fala(1.0)), ("Três.", fala(1.0))])
    (pasta / "metadata.csv").write_text(
        "﻿" + (pasta / "metadata.csv").read_text(encoding="utf-8"), encoding="utf-8"
    )
    args = SimpleNamespace(nome="teste", descartar=False, tirar=["2", "0003.wav"])
    assert comando_conferir_dataset(config, args, ouvido=None) == 0
    assert (pasta / "metadata.csv").read_text(encoding="utf-8") == "0001|Uma.\n"
    assert (pasta / "descartadas.txt").read_text(encoding="utf-8") == "0002\n0003\n"
