"""v0.3.1: a voz do ElevenLabs em streaming começa a tocar com a primeira parte do áudio."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from nora import audio
from nora.audio import AudioEmPartes, _tocar_partes
from nora.conversa_voz import Locutor
from nora.servico import ServicoIndisponivel
from nora.voz import VozComReserva, VozElevenLabs, em_partes


class NuvemAosPedacos:
    """ElevenLabs falso: manda a primeira parte do áudio e segura o resto até `liberar`."""

    def __init__(self, partes, status=200):
        self.partes, self.status = partes, status
        self.liberar = threading.Event()
        self.pedidos = []
        dono = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                corpo = self.rfile.read(int(self.headers["Content-Length"]))
                dono.pedidos.append((self.path, json.loads(corpo)))
                if dono.status != 200:
                    dados = b'{"detail": "sem creditos"}'
                    self.send_response(dono.status)
                    self.send_header("Content-Length", str(len(dados)))
                    self.end_headers()
                    self.wfile.write(dados)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "audio/pcm")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                for i, parte in enumerate(dono.partes):
                    if i == 1:
                        dono.liberar.wait(5)
                    self.wfile.write(f"{len(parte):x}\r\n".encode() + parte + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")

            def log_message(self, *args):
                pass

        self.servidor = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.servidor.server_port}"

    def __enter__(self):
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *args):
        self.liberar.set()
        self.servidor.shutdown()


def _eleven(url, monkeypatch):
    monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{url}/v1/text-to-speech")
    return VozElevenLabs("chave", "voz1", "eleven_flash_v2_5", intensidade=0.0)


def test_elevenlabs_entrega_a_primeira_parte_antes_do_resto(monkeypatch):
    partes = [b"\x01\x00" * 100, b"\x02\x00" * 100]
    with NuvemAosPedacos(partes) as nuvem:
        voz = _eleven(nuvem.url, monkeypatch)
        som = voz.sintetizar_em_partes("Daqui a 24 dias será domingo.")
        assert som.primeira.wait(3)  # a primeira parte chegou com o resto ainda preso
        assert not som.baixado.is_set()
        nuvem.liberar.set()
        assert som.tudo() == b"".join(partes)
    caminho, corpo = nuvem.pedidos[0]
    assert caminho == "/v1/text-to-speech/voz1/stream?output_format=pcm_22050"
    assert corpo["text"] == "Daqui a 24 dias será domingo."
    assert voz.ultima_duracao > 0


def test_recusa_do_elevenlabs_aparece_antes_e_a_reserva_fala(monkeypatch):
    class Reserva:
        def sintetizar(self, texto):
            return b"wav da reserva"

    with NuvemAosPedacos([], status=401) as nuvem:
        voz = VozComReserva(_eleven(nuvem.url, monkeypatch), Reserva())
        assert em_partes(voz, "Oi.") == b"wav da reserva"
    assert "401" in voz.aviso


def test_partes_com_amostra_cortada_no_meio():
    som = AudioEmPartes(iter([b"\x01", b"\x00\x02", b"\x00"]), 22_050)
    assert list(som.partes()) == [b"\x01\x00", b"\x02\x00"]


def test_queda_no_meio_entrega_o_que_chegou_e_guarda_o_erro():
    def partes():
        yield b"\x01\x00"
        raise OSError("conexão caiu")

    som = AudioEmPartes(partes(), 22_050)
    assert list(som.partes()) == [b"\x01\x00"]
    assert isinstance(som.erro, OSError)
    with pytest.raises(OSError):
        AudioEmPartes(partes(), 22_050).tudo()


# --- Locutor ----------------------------------------------------------------------------------


class VozEmStreaming:
    def __init__(self, falhar_no_meio=False):
        self.pedidos = []
        self.falhar_no_meio = falhar_no_meio

    def sintetizar(self, texto):
        raise AssertionError("o Locutor deve usar o streaming")

    def sintetizar_em_partes(self, texto):
        self.pedidos.append((texto, time.perf_counter()))

        def partes():
            yield texto.encode()[:2]
            time.sleep(0.1)
            if self.falhar_no_meio:
                raise OSError("caiu")
            yield texto.encode()[2:]

        return AudioEmPartes(partes(), 22_050, canais=1)


def test_locutor_toca_em_streaming_e_pede_uma_frase_por_vez():
    voz = VozEmStreaming()
    tocados = []
    locutor = Locutor(voz, lambda som: tocados.append(som.tudo().decode()), 0.0)
    locutor.falar("Primeira frase longa o bastante.")
    time.sleep(0.02)
    locutor.falar("Segunda frase também longa.")
    locutor.terminar()
    assert tocados == ["Primeira frase longa o bastante.", "Segunda frase também longa."]
    assert voz.pedidos[1][1] - voz.pedidos[0][1] >= 0.09  # esperou o primeiro chegar inteiro
    assert locutor.tempos.comeco_da_voz > 0 and not locutor.tempos.erros


def test_locutor_avisa_quando_a_voz_cai_no_meio():
    locutor = Locutor(VozEmStreaming(falhar_no_meio=True), lambda som: list(som.partes()), 0.0)
    locutor.falar("Uma frase qualquer.")
    locutor.terminar()
    assert any("parou no meio" in erro for erro in locutor.tempos.erros)


# --- tocar em streaming -----------------------------------------------------------------------


class SomFalso:
    """sounddevice falso: chama o callback em blocos, como a placa de som."""

    class PortAudioError(Exception):
        pass

    class CallbackStop(Exception):
        pass

    def __init__(self, recusar_taxa=None, padrao=48_000):
        self.recusar_taxa = recusar_taxa
        self.padrao = padrao
        self.tocado = bytearray()
        self.taxas = []

    def query_devices(self, dispositivo, tipo):
        return {"default_samplerate": self.padrao}

    def RawOutputStream(self, device, samplerate, channels, dtype, callback, finished_callback):  # noqa: N802
        if samplerate == self.recusar_taxa:
            raise self.PortAudioError("taxa recusada")
        self.taxas.append(samplerate)
        dono = self

        class Fluxo:
            def __enter__(self):
                def rodar():
                    while True:
                        saida = bytearray(256)
                        try:
                            callback(saida, 128, None, None)
                        except dono.CallbackStop:
                            dono.tocado.extend(saida)
                            break
                        dono.tocado.extend(saida)
                        time.sleep(0.001)
                    finished_callback()

                threading.Thread(target=rodar, daemon=True).start()
                return self

            def __exit__(self, *args):
                pass

        return Fluxo()


def test_toca_o_silencio_inicial_e_todas_as_partes_em_ordem():
    sd = SomFalso()
    pcm = bytes(range(256)) * 8
    partes = [pcm[i : i + 300] for i in range(0, len(pcm), 300)]
    _tocar_partes(sd, AudioEmPartes(iter(partes), 1000), silencio_ms=10, alto_falante=None)
    silencio = b"\x00\x00" * 10
    assert sd.taxas == [1000]
    assert bytes(sd.tocado)[: len(silencio) + len(pcm)] == silencio + pcm


def test_saida_que_recusa_a_taxa_recebe_o_audio_convertido(monkeypatch):
    sd = SomFalso(recusar_taxa=22_050, padrao=44_100)
    pcm = b"\x10\x00" * 2205  # 0,1 s
    _tocar_partes(sd, AudioEmPartes(iter([pcm]), 22_050), silencio_ms=0, alto_falante=None)
    assert sd.taxas == [44_100]
    assert len(bytes(sd.tocado).rstrip(b"\x00")) == pytest.approx(len(pcm) * 2, abs=8)


def test_tocador_escolhe_streaming_ou_wav(monkeypatch):
    chamadas = []
    monkeypatch.setattr(audio, "tocar_partes", lambda som, alto, ms: chamadas.append("partes"))
    monkeypatch.setattr(audio, "tocar_wav", lambda wav, alto: chamadas.append("wav"))

    class ConfigAudio:
        alto_falante = ""
        silencio_inicial_ms = 0

    tocar = audio.tocador(ConfigAudio())
    tocar(AudioEmPartes(iter([b"\x00\x00"]), 22_050))
    tocar(audio.para_wav(b"\x00\x00"))
    assert chamadas == ["partes", "wav"]


def test_falha_na_reserva_e_na_principal(monkeypatch):
    class Quebrada:
        def sintetizar(self, texto):
            raise ServicoIndisponivel("fora do ar")

    with pytest.raises(ServicoIndisponivel, match="reserva também falhou"):
        em_partes(VozComReserva(Quebrada(), Quebrada()), "oi")


def test_hud_recebe_motor_real_quando_o_primeiro_pcm_chega(monkeypatch):
    eventos = []
    monkeypatch.setattr("nora.voz.emitir", lambda tipo, **dados: eventos.append((tipo, dados)))
    with NuvemAosPedacos([b"\x01\x00" * 100, b"\x02\x00" * 100]) as nuvem:
        som = _eleven(nuvem.url, monkeypatch).sintetizar_em_partes("Olá, teste local.")
        assert som.primeira.wait(3)
        assert eventos == [("voz_ativa", {"motor": "ElevenLabs"})]
        assert not som.baixado.is_set()  # informar o motor não espera baixar tudo
        nuvem.liberar.set()
        som.tudo()
    assert len(eventos) == 1


def test_recusa_do_motor_nao_emite_voz_ativa_incorreta(monkeypatch):
    eventos = []
    monkeypatch.setattr("nora.voz.emitir", lambda tipo, **dados: eventos.append((tipo, dados)))
    with NuvemAosPedacos([], status=401) as nuvem:
        with pytest.raises(ServicoIndisponivel):
            _eleven(nuvem.url, monkeypatch).sintetizar_em_partes("Teste local.")
    assert eventos == []


def test_motor_so_e_informado_quando_chega_uma_amostra_completa(monkeypatch):
    eventos = []
    monkeypatch.setattr("nora.voz.emitir", lambda tipo, **dados: eventos.append((tipo, dados)))

    class Resposta:
        partes = iter([b"\x01", b"\x00", b""])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read1(self, tamanho):
            return next(self.partes)

    voz = VozElevenLabs("chave sintética", "voz sintética", "eleven_flash_v2_5")
    partes = voz._ler(Resposta(), time.perf_counter())
    assert next(partes) == b"\x01"
    assert eventos == []
    assert next(partes) == b"\x00"
    assert eventos == [("voz_ativa", {"motor": "ElevenLabs"})]
    assert list(partes) == []


def test_wrappers_preservam_stream_e_personalizacoes_sem_esperar_pcm(monkeypatch):
    from nora.voz import VozComPronuncias, VozComRealce, VozTrocavel

    chamadas = []
    fluxo = object()

    class Voz:
        def sintetizar_em_partes(self, texto):
            chamadas.append(texto)
            return fluxo

        def sintetizar(self, texto):
            raise AssertionError("Não converter streaming em WAV antes de tocar")

    # A pronúncia aprendida e o realce de pergunta continuam passando pelo mesmo domínio.
    voz = VozComPronuncias(VozComRealce(Voz(), "duplo"), lambda: {"Nora": "Nóra"})
    assert em_partes(voz, "Nora, tudo bem?") is fluxo
    assert chamadas == ["Nóra, tudo bem??"]
    trocavel = object.__new__(VozTrocavel)
    trocavel.voz = voz
    assert trocavel.sintetizar_em_partes("Nora.") is fluxo
    assert chamadas[-1] == "Nóra."


def test_fonte_de_pronuncia_indisponivel_nao_perde_stream():
    from nora.voz import VozComPronuncias

    fluxo = object()

    class Voz:
        def sintetizar_em_partes(self, texto):
            assert texto == "Oi."
            return fluxo

    def fonte():
        raise RuntimeError("memória indisponível")

    assert em_partes(VozComPronuncias(Voz(), fonte), "Oi.") is fluxo


def test_queda_apos_primeiro_pcm_nao_emenda_reserva(monkeypatch):
    reservas = []

    class Resposta:
        primeira = True

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read1(self, tamanho):
            if self.primeira:
                self.primeira = False
                return b"\x01\x00"
            raise OSError("conexão sintética interrompida")

    class Reserva:
        def sintetizar(self, texto):
            reservas.append(texto)
            return b"outra resposta"

    principal = VozElevenLabs("chave sintética", "voz sintética", "eleven_flash_v2_5")
    monkeypatch.setattr(principal, "_abrir", lambda corpo: Resposta())
    som = em_partes(VozComReserva(principal, Reserva()), "Teste local.")
    assert som.baixado.wait(3)
    assert list(som.partes()) == [b"\x01\x00"]
    assert isinstance(som.erro, OSError)
    assert reservas == []


def test_enviar_normaliza_falha_de_leitura_do_corpo(monkeypatch):
    import urllib.request

    from nora.servico import enviar

    class Resposta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            raise OSError("falha de leitura sintética")

    monkeypatch.setattr("nora.servico.abrir", lambda *args: Resposta())
    with pytest.raises(ServicoIndisponivel, match="parou de responder no meio"):
        enviar("serviço de teste", urllib.request.Request("http://127.0.0.1:1"), 1)
