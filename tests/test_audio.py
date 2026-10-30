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
    class PortAudioError(Exception):
        pass

    def __init__(self, taxa=48_000, falhar=False):
        self.taxa = taxa
        self.falhar = falhar
        self.aberto_com = None

    def query_devices(self, dispositivo=None, tipo=None):
        return {"default_samplerate": float(self.taxa)}

    def RawInputStream(self, **opcoes):
        if self.falhar:
            raise self.PortAudioError("MME error 11")
        self.aberto_com = opcoes
        falso = self

        class Fluxo:
            def __enter__(self):
                opcoes["callback"](pcm([7] * falso.taxa), falso.taxa, None, None)
                return self

            def __exit__(self, *args):
                pass

        return Fluxo()


def test_grava_na_taxa_do_microfone_e_entrega_16k(monkeypatch):
    falso = SounddeviceFalso(taxa=48_000)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    wav = audio.gravar_ate_enter(lambda _: "", microfone=2)
    assert falso.aberto_com["samplerate"] == 48_000
    assert falso.aberto_com["device"] == 2
    amostras, taxa, canais = audio.ler_wav(wav)
    assert (taxa, canais) == (16_000, 1)
    assert audio.duracao_wav(wav) == pytest.approx(1.0)


def test_erro_do_microfone_vira_mensagem_clara(monkeypatch):
    monkeypatch.setattr(audio, "_sounddevice", lambda: SounddeviceFalso(falhar=True))
    with pytest.raises(RuntimeError, match="Privacidade e segurança > Microfone"):
        audio.gravar_ate_enter(lambda _: "")
