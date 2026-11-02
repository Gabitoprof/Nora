from types import SimpleNamespace

import pytest

from nora.audio import ler_wav, para_wav
from nora.cli import comando_gerar_dataset
from nora.config import RAIZ, carregar
from nora.dataset_voz import frases_de_texto, gerar_dataset, ler_frases
from nora.servico import ServicoIndisponivel


class VozFalsa:
    def __init__(self, falhar_em=None):
        self.falas = []
        self.falhar_em = falhar_em

    def sintetizar(self, frase):
        if frase == self.falhar_em:
            raise ServicoIndisponivel("ComfyUI fechado")
        self.falas.append(frase)
        return para_wav(b"\x01\x00\xff\xff" * 24_000, taxa=24_000, canais=2)  # 1 s estéreo


def test_gera_no_formato_do_piper_e_continua_de_onde_parou(tmp_path):
    frases = ["Primeira frase de teste.", "Segunda | com barra.", "Terceira frase."]
    pasta = tmp_path / "minha_voz"
    with pytest.raises(ServicoIndisponivel):
        gerar_dataset(VozFalsa(falhar_em="Terceira frase."), frases, pasta, saida=lambda _: None)
    voz = VozFalsa()
    assert gerar_dataset(voz, frases, pasta, saida=lambda _: None) == 1
    assert voz.falas == ["Terceira frase."]  # só a que faltava
    amostras, taxa, canais = ler_wav((pasta / "wavs" / "0001.wav").read_bytes())
    assert (taxa, canais) == (22_050, 1)
    assert len(amostras) // 2 == 22_050
    assert (pasta / "metadata.csv").read_text(encoding="utf-8").splitlines() == [
        "0001|Primeira frase de teste.",
        "0002|Segunda   com barra.",
        "0003|Terceira frase.",
    ]


def test_corta_texto_corrido_em_frases_boas():
    texto = (
        "Era uma vez uma cidade pequena à beira do rio. Curta. "
        "Todos os dias, ao amanhecer, os pescadores saíam com seus barcos!\n"
        "Era uma vez uma cidade pequena à beira do rio. " + "palavra " * 40
    )
    assert frases_de_texto(texto) == [
        "Era uma vez uma cidade pequena à beira do rio.",
        "Todos os dias, ao amanhecer, os pescadores saíam com seus barcos!",
    ]


def test_lista_de_frases_do_projeto():
    frases = ler_frases(RAIZ / "recursos" / "frases_pt.txt", uma_por_linha=True)
    assert len(frases) >= 100
    assert not any(f.startswith("#") for f in frases)
    assert len(set(frases)) == len(frases)


def test_comando_usa_so_a_voz_principal(criar_raiz, tmp_path, capsys):
    arquivo = tmp_path / "frases.txt"
    arquivo.write_text("# comentário\nUma frase.\nOutra frase.\nUma frase.\n", encoding="utf-8")
    config = carregar(criar_raiz(), ambiente={})
    voz = VozFalsa()
    args = SimpleNamespace(texto="", frases=str(arquivo), nome="teste", limite=0)
    assert comando_gerar_dataset(config, args, voz) == 0
    assert voz.falas == ["Uma frase.", "Outra frase."]
    assert (config.pasta_dados / "dataset_voz" / "teste" / "metadata.csv").is_file()
    args = SimpleNamespace(texto="", frases=str(tmp_path / "nada.txt"), nome="x", limite=0)
    assert comando_gerar_dataset(config, args, voz) == 1
