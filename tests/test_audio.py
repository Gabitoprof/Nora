from array import array

import pytest

from ella import audio


def pcm(valores):
    return array("h", valores).tobytes()


def test_reamostrar_de_48k_para_16k():
    um_segundo = pcm([1000] * 48_000)
    convertido = audio.reamostrar(um_segundo, 48_000)
    amostras = array("h")
    amostras.frombytes(convertido)
    assert len(amostras) == 16_000
    assert set(amostras) == {1000}


def test_reamostrar_interpola_e_preserva_as_pontas():
    convertido = array("h")
    convertido.frombytes(audio.reamostrar(pcm([0, 100]), 2, 4))
    assert list(convertido) == [0, 33, 66, 100]
    assert audio.reamostrar(pcm([5, 6]), 16_000) == pcm([5, 6])
    assert audio.reamostrar(b"", 48_000) == b""


def test_dispositivo_da_config():
    assert audio.dispositivo("") is None
    assert audio.dispositivo(" 3 ") == 3
    assert audio.dispositivo("Headset") == "Headset"


class SounddeviceFalso:
    """Imita o sounddevice: o fifine aparece no MME (0) e no WASAPI (1); a câmera no MME (2)."""

    class PortAudioError(Exception):
        pass

    APIS = [{"name": "MME"}, {"name": "Windows WASAPI"}]
    DISPOSITIVOS = [
        {
            "name": "Microfone (fifine Microphone)",
            "hostapi": 0,
            "max_input_channels": 2,
            "default_samplerate": 44_100.0,
        },
        {
            "name": "Microfone (fifine Microphone)",
            "hostapi": 1,
            "max_input_channels": 2,
            "default_samplerate": 48_000.0,
        },
        {
            "name": "Microfone (UGREEN Camera Audio)",
            "hostapi": 0,
            "max_input_channels": 1,
            "default_samplerate": 44_100.0,
        },
    ]

    def __init__(self, funciona=lambda indice, canais: True):
        self.funciona = funciona
        self.tentativas = []
        self.aberto_com = None

    def query_devices(self, dispositivo=None, tipo=None):
        if dispositivo is None and tipo is None:
            return self.DISPOSITIVOS
        return self.DISPOSITIVOS[0 if dispositivo is None else dispositivo]

    def query_hostapis(self, indice=None):
        return self.APIS if indice is None else self.APIS[indice]

    def RawInputStream(self, **opcoes):
        indice = 0 if opcoes["device"] is None else opcoes["device"]
        self.tentativas.append((indice, opcoes["channels"]))
        if not self.funciona(indice, opcoes["channels"]):
            raise self.PortAudioError("MME error 11")
        self.aberto_com = opcoes
        taxa, canais = opcoes["samplerate"], opcoes["channels"]

        class Fluxo:
            def __enter__(self):
                opcoes["callback"](
                    pcm([7, -7] * taxa if canais == 2 else [7] * taxa), taxa, None, None
                )
                return self

            def __exit__(self, *args):
                pass

        return Fluxo()


def test_grava_na_taxa_do_microfone_e_entrega_16k(monkeypatch):
    falso = SounddeviceFalso()
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    wav = audio.gravar_ate_enter(lambda _: "", microfone=2)
    assert falso.aberto_com["samplerate"] == 44_100
    assert falso.aberto_com["device"] == 2
    amostras, taxa, canais = audio.ler_wav(wav)
    assert (taxa, canais) == (16_000, 1)
    assert audio.duracao_wav(wav) == pytest.approx(1.0)


def test_se_o_mme_falha_usa_o_mesmo_microfone_no_wasapi_em_estereo(monkeypatch):
    falso = SounddeviceFalso(funciona=lambda indice, canais: indice == 1 and canais == 2)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    wav = audio.gravar_ate_enter(lambda _: "")
    assert falso.tentativas == [(0, 1), (0, 2), (1, 1), (1, 2)]
    assert falso.aberto_com["samplerate"] == 48_000
    amostras = array("h")
    amostras.frombytes(audio.ler_wav(wav)[0])
    assert len(amostras) == 16_000
    assert set(amostras) == {7}  # ficou só o canal esquerdo


def test_erro_do_microfone_vira_mensagem_clara(monkeypatch):
    falso = SounddeviceFalso(funciona=lambda indice, canais: False)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    with pytest.raises(RuntimeError, match="Privacidade e segurança > Microfone"):
        audio.gravar_ate_enter(lambda _: "")
    assert {indice for indice, _ in falso.tentativas} == {0, 1}  # não tentou a câmera
