from nora.conversa_voz import Locutor, abafador
from nora.prioridade import abafar_outros


class Volume:
    def __init__(self, valor):
        self.valor = valor

    def GetMasterVolume(self):
        return self.valor

    def SetMasterVolume(self, valor, contexto):
        self.valor = valor


def test_abafa_e_devolve_o_volume_dos_outros():
    musica, video = Volume(1.0), Volume(0.5)
    with abafar_outros(0.2, sessoes=[("spotify.exe", musica), ("chrome.exe", video)]):
        assert (musica.valor, video.valor) == (0.2, 0.1)
    assert (musica.valor, video.valor) == (1.0, 0.5)


def test_devolve_o_volume_mesmo_com_erro():
    musica = Volume(0.8)
    try:
        with abafar_outros(0.25, sessoes=[("spotify.exe", musica)]):
            raise KeyboardInterrupt
    except KeyboardInterrupt:
        pass
    assert musica.valor == 0.8


def test_abafa_uma_vez_durante_a_resposta_inteira(criar_raiz):
    from nora.config import carregar

    eventos = []

    class Abafar:
        def __enter__(self):
            eventos.append("abafa")

        def __exit__(self, *args):
            eventos.append("devolve")

    class VozFalsa:
        def sintetizar(self, frase):
            return frase.encode()

    locutor = Locutor(VozFalsa(), lambda wav: eventos.append(wav.decode()), 0.0, Abafar)
    for frase in ["Primeira frase.", "Segunda frase."]:
        locutor.falar(frase)
    locutor.terminar()
    assert eventos == ["abafa", "Primeira frase.", "Segunda frase.", "devolve"]

    sem = carregar(criar_raiz(local="[audio]\nprioridade = false\n"), ambiente={})
    assert abafador(sem)().__enter__() is None  # nullcontext: não mexe em nada
    com = carregar(criar_raiz(local="[audio]\nvolume_outros = 0.3\n"), ambiente={})
    assert abafador(com) is not None
