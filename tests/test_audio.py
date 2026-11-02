from array import array

import pytest

from nora import audio


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

    def __init__(self, funciona=lambda indice, canais: True, falha_ao_comecar=lambda i: False):
        self.funciona = funciona
        self.falha_ao_comecar = falha_ao_comecar
        self.parados = 0
        self.fechados = 0
        self.tentativas = []
        self.aberto_com = None

    def query_devices(self, dispositivo=None, tipo=None):
        if dispositivo is None and tipo is None:
            return self.DISPOSITIVOS
        return self.DISPOSITIVOS[0 if dispositivo is None else dispositivo]

    class WasapiSettings:
        def __init__(self, auto_convert=False):
            self.auto_convert = auto_convert

    def query_hostapis(self, indice=None):
        return self.APIS if indice is None else self.APIS[indice]

    def RawInputStream(self, **opcoes):
        indice = 0 if opcoes["device"] is None else opcoes["device"]
        self.tentativas.append((indice, opcoes["channels"]))
        if not self.funciona(indice, opcoes["channels"]):
            raise self.PortAudioError("MME error 11")
        self.aberto_com = opcoes
        taxa, canais = opcoes["samplerate"], opcoes["channels"]
        falso = self

        class Fluxo:
            def start(self):
                if falso.falha_ao_comecar(indice):
                    raise falso.PortAudioError("WdmSyncIoctl: GLE = 0x0000048F")
                opcoes["callback"](
                    pcm([7, -7] * taxa if canais == 2 else [7] * taxa), taxa, None, None
                )

            def stop(self):
                falso.parados += 1

            def close(self):
                falso.fechados += 1

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
    assert falso.tentativas[:2] == [(0, 1), (0, 2)]  # o padrão (MME) primeiro, mono e estéreo
    assert falso.tentativas[-2:] == [(1, 1), (1, 2)]  # depois o WASAPI, que abre em estéreo
    assert {indice for indice, _ in falso.tentativas} == {0, 1}
    assert falso.aberto_com["samplerate"] == 48_000
    amostras = array("h")
    amostras.frombytes(audio.ler_wav(wav)[0])
    assert len(amostras) == 16_000
    assert set(amostras) == {7}  # ficou só o canal esquerdo


def test_microfone_bluetooth_so_abre_em_16k(monkeypatch):
    falso = SounddeviceFalso(funciona=lambda indice, canais: True)
    original = falso.RawInputStream

    def so_16k(**opcoes):
        if opcoes["samplerate"] != 16_000:
            raise falso.PortAudioError("MME error 11")
        return original(**opcoes)

    falso.RawInputStream = so_16k
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    wav = audio.gravar_ate_enter(lambda _: "")
    assert falso.aberto_com["samplerate"] == 16_000
    assert audio.ler_wav(wav)[1] == 16_000


def test_wasapi_abre_com_conversao_automatica(monkeypatch):
    falso = SounddeviceFalso(funciona=lambda indice, canais: indice == 1)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    audio.gravar_ate_enter(lambda _: "")
    assert falso.aberto_com["extra_settings"].auto_convert is True


def test_acha_a_versao_wdm_ks_do_fone_bluetooth(monkeypatch):
    falso = SounddeviceFalso(funciona=lambda indice, canais: indice == 3)
    falso.APIS = [*falso.APIS, {"name": "Windows WDM-KS"}]
    falso.DISPOSITIVOS = [
        {
            "name": "Headset (HAYLOU S40)",
            "hostapi": 0,
            "max_input_channels": 1,
            "default_samplerate": 44_100.0,
        },
        {
            "name": "Headset (HAYLOU S40)",
            "hostapi": 1,
            "max_input_channels": 1,
            "default_samplerate": 16_000.0,
        },
        {
            "name": "Microfone (fifine Microphone)",
            "hostapi": 0,
            "max_input_channels": 1,
            "default_samplerate": 44_100.0,
        },
        {
            "name": "Headset (@System32\\drivers\\bthhfenum.sys,#2;%1 Hands-Free%0\n;(HAYLOU S40))",
            "hostapi": 2,
            "max_input_channels": 1,
            "default_samplerate": 16_000.0,
        },
    ]
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    audio.gravar_ate_enter(lambda _: "")
    assert falso.aberto_com["device"] == 3
    assert 2 not in {indice for indice, _ in falso.tentativas}  # não tentou o fifine


def test_microfone_que_abre_mas_nao_comeca_passa_para_o_proximo(monkeypatch):
    falso = SounddeviceFalso(falha_ao_comecar=lambda indice: indice == 0)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    wav = audio.gravar_ate_enter(lambda _: "")
    assert falso.aberto_com["device"] == 1
    assert audio.duracao_wav(wav) == pytest.approx(1.0)
    assert falso.parados == 1
    assert falso.fechados >= 2  # o que falhou ao começar e o que gravou


def test_erro_do_microfone_vira_mensagem_clara(monkeypatch):
    falso = SounddeviceFalso(funciona=lambda indice, canais: False)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    with pytest.raises(RuntimeError, match="Privacidade e segurança > Microfone") as erro:
        audio.gravar_ate_enter(lambda _: "")
    assert "Tentativas:" in str(erro.value)
    assert "1 Microfone (fifine Microphone) [Windows WASAPI], taxas 48000, 44100, 16000" in str(
        erro.value
    )
    assert "padrão Microfone (fifine Microphone) [MME]" in str(erro.value)
    assert {indice for indice, _ in falso.tentativas} == {0, 1}  # não tentou a câmera


class SaidaFalsa:
    """Imita um RawOutputStream que só aceita callback (como o WDM-KS) e uma taxa."""

    class PortAudioError(Exception):
        pass

    class CallbackStop(Exception):
        pass

    def __init__(self, taxa_aceita=16_000):
        self.taxa_aceita = taxa_aceita
        self.tocado = bytearray()
        self.taxas = []

    def query_devices(self, dispositivo=None, tipo=None):
        return {"default_samplerate": float(self.taxa_aceita)}

    def RawOutputStream(self, **opcoes):
        self.taxas.append(opcoes["samplerate"])
        if opcoes["samplerate"] != self.taxa_aceita:
            raise self.PortAudioError("Invalid sample rate")
        if "callback" not in opcoes:
            raise self.PortAudioError("Blocking API not supported yet")
        falso = self

        class Fluxo:
            def __enter__(self):
                tamanho = 2 * opcoes["channels"] * 160
                while True:
                    bloco = bytearray(tamanho)
                    try:
                        opcoes["callback"](bloco, 160, None, None)
                    except falso.CallbackStop:
                        falso.tocado += bloco
                        break
                    falso.tocado += bloco
                opcoes["finished_callback"]()
                return self

            def __exit__(self, *args):
                pass

        return Fluxo()


def test_toca_por_callback_e_converte_para_a_taxa_da_saida(monkeypatch):
    falso = SaidaFalsa(taxa_aceita=16_000)
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    um_segundo_24k = audio.para_wav(pcm([5] * 24_000), taxa=24_000)
    audio.tocar_wav(um_segundo_24k, alto_falante=17)
    assert falso.taxas == [24_000, 16_000]
    tocado = array("h")
    tocado.frombytes(bytes(falso.tocado))
    assert tocado.count(5) == 16_000  # o áudio inteiro, convertido
    assert set(tocado[16_000:]) <= {0}  # o resto do último bloco é silêncio


def test_saida_que_nao_abre_cai_na_padrao_e_avisa(monkeypatch):
    falso = SaidaFalsa(taxa_aceita=16_000)
    original = falso.RawOutputStream

    def so_a_padrao(**opcoes):
        if opcoes["device"] == 17:
            raise falso.PortAudioError("Invalid device")
        return original(**opcoes)

    falso.RawOutputStream = so_a_padrao
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    audio.avisos_de_saida()  # começa limpo
    audio.tocar_wav(audio.para_wav(pcm([5] * 16_000)), alto_falante=17)
    assert array("h", bytes(falso.tocado)).count(5) == 16_000
    avisos = audio.avisos_de_saida()
    assert len(avisos) == 1 and "A saída '17' não abriu" in avisos[0]
    assert audio.avisos_de_saida() == []


def test_saida_padrao_que_falha_continua_dando_erro(monkeypatch):
    falso = SaidaFalsa(taxa_aceita=16_000)
    falso.RawOutputStream = lambda **_: (_ for _ in ()).throw(falso.PortAudioError("sem som"))
    monkeypatch.setattr(audio, "_sounddevice", lambda: falso)
    with pytest.raises(falso.PortAudioError):
        audio.tocar_wav(audio.para_wav(pcm([5] * 160)))


def test_reamostrar_com_qualidade_corta_o_que_nao_cabe_na_taxa_nova():
    np = pytest.importorskip("numpy")
    taxa = 44_100
    t = np.arange(taxa) / taxa
    # 1 kHz (voz) + 15 kHz (acima do limite de 11.025 Hz da taxa de 22.050)
    sinal = 8000 * np.sin(2 * np.pi * 1000 * t) + 8000 * np.sin(2 * np.pi * 15_000 * t)
    entrada = sinal.astype("<i2").tobytes()
    saida = np.frombuffer(audio.reamostrar_qualidade(entrada, taxa, 22_050), dtype="<i2")
    assert len(saida) == 22_050
    espectro = np.abs(np.fft.rfft(saida))
    freq = np.fft.rfftfreq(len(saida), 1 / 22_050)
    voz = espectro[np.argmin(abs(freq - 1000))]
    dobra = espectro[np.argmin(abs(freq - (22_050 - 15_000)))]  # onde o chiado apareceria
    assert dobra < voz / 100  # os 15 kHz não viraram chiado em 7 kHz
    assert audio.reamostrar_qualidade(entrada, taxa, taxa) == entrada
