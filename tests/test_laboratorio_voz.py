from types import SimpleNamespace

import numpy as np
import pytest

from nora.audio import duracao_wav
from nora.cli import laboratorio_de_voz
from nora.config import carregar
from nora.servidor_kokoro import Sintetizador, ler_receita


def test_ler_receita():
    assert ler_receita("pf_dora") == [("pf_dora", 1.0)]
    assert ler_receita(" pf_dora:3 + af_heart:1 ") == [("pf_dora", 0.75), ("af_heart", 0.25)]
    for ruim in ["", "pf_dora:abc", "pf_dora:0", "+"]:
        with pytest.raises(ValueError):
            ler_receita(ruim)


class KokoroFalso:
    VOZES = {"pf_dora": 1.0, "af_heart": 3.0, "pm_alex": 5.0}

    def __init__(self):
        self.estilos = []

    def get_voices(self):
        return list(self.VOZES)

    def get_voice_style(self, nome):
        return np.full((510, 1, 256), self.VOZES[nome], dtype=np.float32)

    def create(self, texto, voice, speed, lang):
        self.estilos.append(float(voice[0, 0, 0]))
        return np.zeros(2400, dtype=np.float32), 24_000


def sintetizador_falso(receita="pf_dora"):
    s = Sintetizador.__new__(Sintetizador)
    s.kokoro, s.voz, s.velocidade, s.idioma = KokoroFalso(), receita, 1.0, "pt-br"
    s._misturas = {}
    import threading

    s._trava = threading.Lock()
    return s


def test_mistura_de_vozes_e_voz_desconhecida():
    s = sintetizador_falso()
    s.sintetizar("oi", "pf_dora:0.75 + af_heart:0.25")
    assert s.kokoro.estilos == [pytest.approx(0.75 * 1 + 0.25 * 3)]
    s.sintetizar("oi")  # a voz padrão, sozinha
    assert s.kokoro.estilos[-1] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="Voz desconhecida: xx_nada"):
        s.sintetizar("oi", "pf_dora + xx_nada")


def test_laboratorio_testa_e_salva_a_amostra(criar_raiz, capsys):
    config = carregar(criar_raiz(), ambiente={})
    tocados = []
    args = SimpleNamespace(
        acao="testar", receita="pf_dora:0.7+pm_alex:0.3", frase="", velocidade=1.1
    )
    assert laboratorio_de_voz(config, args, sintetizador_falso(), tocados.append) == 0
    texto = capsys.readouterr().out
    assert 'voz = "pf_dora:0.7+pm_alex:0.3"' in texto
    amostra = config.pasta_dados / "vozes" / "pf_dora_0_7_pm_alex_0_3_v1.1.wav"
    assert amostra.is_file() and duracao_wav(amostra.read_bytes()) == pytest.approx(0.1)
    assert len(tocados) == 1

    args = SimpleNamespace(acao="listar", receita=None, frase="", velocidade=None)
    assert laboratorio_de_voz(config, args, sintetizador_falso(), tocados.append) == 0
    texto = capsys.readouterr().out
    assert "português (Brasil): pf_dora, pm_alex" in texto
    assert "inglês (EUA): af_heart" in texto

    args = SimpleNamespace(acao="testar", receita="zz_nada", frase="", velocidade=None)
    assert laboratorio_de_voz(config, args, sintetizador_falso(), tocados.append) == 1
