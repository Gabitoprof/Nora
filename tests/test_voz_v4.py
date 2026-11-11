"""ElevenLabs v4 (diálogo por WebSocket) com um servidor falso local: sem rede, sem chave real."""

import base64
import io
import json
import threading
import time
import urllib.parse

import pytest

pytest.importorskip("websockets")

from fake_ollama import OllamaFalso  # noqa: E402
from fake_servico import ServicoFalso  # noqa: E402
from websockets.sync.server import serve  # noqa: E402

from nora import audio, diagnostico_voz, elevenlabs_dialogo, hud  # noqa: E402
from nora.cli import verificar  # noqa: E402
from nora.config import carregar  # noqa: E402
from nora.conversa_voz import LocutorDialogo, conversar_por_voz  # noqa: E402
from nora.elevenlabs_dialogo import SessaoDialogo, palavras_do_alinhamento  # noqa: E402
from nora.voz import VozElevenLabsDialogo, achar_dialogo, criar_voz  # noqa: E402

TAXA = 22_050
MS_POR_CARACTERE = 20
CHAVE = "chave-de-teste-secreta"


def pcm_de(texto: str) -> bytes:
    """PCM falso que carrega o texto (para conferir a ordem) com a duração do alinhamento."""
    tamanho = round(len(texto) * MS_POR_CARACTERE / 1000 * TAXA) * 2
    return (texto.encode() * (tamanho // max(1, len(texto.encode())) + 1))[:tamanho]


class DialogoFalso:
    """Servidor WebSocket do Text to Dialogue, só o que a Nora usa."""

    def __init__(self, modo="normal", pedacos=1, atraso=0.0):
        self.modo, self.pedacos, self.atraso = modo, pedacos, atraso
        self.conexoes: list[dict] = []
        self.fechadas = 0
        self._servidor = serve(self._atender, "127.0.0.1", 0)
        self.url = f"ws://127.0.0.1:{self._servidor.socket.getsockname()[1]}/v1/dialogo"

    def __enter__(self):
        threading.Thread(target=self._servidor.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *_):
        self._servidor.shutdown()

    def mensagens(self, tipo: str, conexao: int = -1) -> list:
        return [m for m in self.conexoes[conexao]["mensagens"] if tipo in m]

    def _atender(self, ws):
        conexao = {
            "caminho": ws.request.path,
            "cabecalhos": {k.lower(): v for k, v in ws.request.headers.raw_items()},
            "mensagens": [],
        }
        self.conexoes.append(conexao)
        try:
            for bruto in ws:
                mensagem = json.loads(bruto)
                conexao["mensagens"].append(mensagem)
                self._reagir(ws, mensagem)
        except Exception:
            pass
        finally:
            self.fechadas += 1

    def _reagir(self, ws, mensagem):
        if "inputs" in mensagem:
            self.entradas = getattr(self, "entradas", 0) + 1
            if self.modo in ("cai_no_meio", "cai_sem_alinhamento") and self.entradas >= 2:
                time.sleep(0.05)
                ws.close(code=1011)  # o servidor cai depois da 1ª frase já ter áudio
                return
            if self.modo == "erro":
                ws.send(
                    json.dumps(
                        {
                            "message": "texto do servidor",
                            "error": "unsupported_model",
                            "code": 400,
                            "param": "model_id",
                        }
                    )
                )
                return
            if self.modo in ("mudo", "calado"):
                return
            texto = mensagem["inputs"][0]["text"]
            pcm = pcm_de(texto)
            corte = len(pcm) // self.pedacos // 2 * 2
            for i in range(self.pedacos):
                parte = pcm[i * corte : (i + 1) * corte if i < self.pedacos - 1 else None]
                envio = {"audio": base64.b64encode(parte).decode()}
                if self.modo == "trechos":
                    # alinhamento repartido: cada trecho traz as palavras do seu áudio, com
                    # tempos relativos ao próprio trecho
                    palavras = texto.split()
                    if i < len(palavras):
                        envio["alignment"] = {
                            "chars": list(palavras[i] + " "),
                            "char_start_times_ms": [10 * j for j in range(len(palavras[i]) + 1)],
                            "char_durations_ms": [10] * (len(palavras[i]) + 1),
                        }
                elif i == 0 and self.modo not in ("sem_alinhamento", "cai_sem_alinhamento"):
                    envio["alignment"] = {
                        "chars": list(texto),
                        "char_start_times_ms": [MS_POR_CARACTERE * j for j in range(len(texto))],
                        "char_durations_ms": [MS_POR_CARACTERE] * len(texto),
                    }
                ws.send(json.dumps(envio))
                if self.atraso:
                    time.sleep(self.atraso)
        elif mensagem.get("flush") and self.modo not in ("sem_fim", "calado"):
            ws.send(json.dumps({"is_final_audio_for_turn": True}))


def config_v4(criar_raiz, extra="", modelo="eleven_v4_turbo", ambiente=None):
    local = (
        '[voz]\nmotor = "elevenlabs"\nreserva = ""\n'
        f'[voz.elevenlabs]\nvoz_id = "voz-da-nora"\nmodelo = "{modelo}"\n{extra}'
    )
    return carregar(
        criar_raiz(local=local),
        ambiente={
            "OLLAMA_HOST": "http://127.0.0.1:9",
            "ELEVENLABS_API_KEY": CHAVE,
            **(ambiente or {}),
        },
    )


@pytest.fixture
def v4(criar_raiz, monkeypatch):
    """Monta a voz v4 apontando para o servidor falso."""

    def montar(servidor, extra="", http=None):
        monkeypatch.setattr(
            elevenlabs_dialogo, "URL", servidor.url if servidor else "ws://127.0.0.1:9/x"
        )
        if http is not None:
            monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{http.url}/v1/text-to-speech")
        config = config_v4(criar_raiz, extra)
        voz = criar_voz(config)
        dialogo, transformar = achar_dialogo(voz)
        assert isinstance(dialogo, VozElevenLabsDialogo)
        return config, voz, dialogo, transformar

    return montar


def tocar_tudo(tocados):
    def tocar(som):
        tocados.append(som if isinstance(som, bytes) else b"".join(som.partes()))

    return tocar


def falar(dialogo, transformar, voz, frases, tocados):
    locutor = LocutorDialogo(dialogo, transformar, voz, tocar_tudo(tocados), time.perf_counter())
    for frase in frases:
        locutor.falar(frase)
    locutor.terminar()
    return locutor


# --- streaming --------------------------------------------------------------------------------


def test_streaming_numa_conexao_so_com_new_turn_e_flush(v4):
    frases = ["Oi, tudo bem?", "Hoje faz sol.", "Quer sair?"]
    with DialogoFalso() as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        tocados = []
        locutor = falar(dialogo, transformar, voz, frases, tocados)
        segunda = []
        falar(dialogo, transformar, voz, ["De novo."], segunda)
    assert len(servidor.conexoes) == 1  # a segunda resposta reaproveitou a conexão
    conexao = servidor.conexoes[0]
    consulta = urllib.parse.parse_qs(urllib.parse.urlsplit(conexao["caminho"]).query)
    assert consulta == {
        "model_id": ["eleven_v4_turbo"],
        "output_format": ["pcm_22050"],
        "sync_alignment": ["true"],
    }
    assert conexao["cabecalhos"]["xi-api-key"] == CHAVE
    assert CHAVE not in conexao["caminho"]
    assert conexao["mensagens"][0] == {
        "voices": ["voz-da-nora"],
        "voice_settings": {"stability": 0.5},
    }
    entradas = [m["inputs"][0] for m in servidor.mensagens("inputs")]
    assert [e["text"] for e in entradas] == [f + " " for f in frases] + ["De novo. "]
    assert [e.get("new_turn", False) for e in entradas] == [True, False, False, True]
    assert all(e["voice_id"] == "voz-da-nora" for e in entradas)
    assert len(servidor.mensagens("flush")) == 2
    # um toque só por resposta, com o áudio de todas as frases, em ordem
    assert tocados == [b"".join(pcm_de(f + " ") for f in frases)]
    assert segunda == [pcm_de("De novo. ")]
    assert locutor.reserva is None and not locutor.tempos.erros


def test_texto_vai_antes_do_audio_voltar_e_toca_conforme_chega(v4):
    with DialogoFalso(pedacos=4, atraso=0.05) as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        partes, quando = [], []

        def tocar(som):
            for parte in som.partes():
                partes.append(parte)
                quando.append(time.perf_counter())

        locutor = LocutorDialogo(dialogo, transformar, voz, tocar, time.perf_counter())
        locutor.falar("Uma frase comprida para chegar em pedaços.")
        locutor.terminar()
    assert len(partes) >= 3  # o áudio chegou e tocou em partes, não de uma vez no fim
    assert quando[-1] - quando[0] >= 0.1
    assert locutor.tempos.comeco_da_voz > 0


# --- alignment --------------------------------------------------------------------------------


def test_palavras_do_alinhamento_tiram_tags_e_mantem_a_ordem():
    texto = "[happy] Oi, Gabriel! ..."
    caracteres = [(c, 10.0 * i, 10.0 * i + 10) for i, c in enumerate(texto)]
    palavras = palavras_do_alinhamento(caracteres)
    assert [p["texto"] for p in palavras] == ["Oi,", "Gabriel!"]
    assert palavras[0]["inicio_ms"] == 80.0 and palavras[0]["fim_ms"] == 110.0
    assert all(a["fim_ms"] <= b["inicio_ms"] for a, b in zip(palavras, palavras[1:], strict=False))
    muitas = palavras_do_alinhamento([(c, i, i + 1) for i, c in enumerate("a " * 300)])
    assert len(muitas) == 256


def test_alinhamento_relativo_ao_pedaco_vira_tempo_da_fala_toda():
    sessao = SessaoDialogo("x", "v", "eleven_v4_turbo")
    turno = elevenlabs_dialogo.Turno(sessao)
    um_segundo = b"\x00\x00" * TAXA
    alinhar = {
        "chars": list("Oi"),
        "char_start_times_ms": [0, 100],
        "char_durations_ms": [100, 100],
    }
    turno._receber(um_segundo, alinhar)
    turno._receber(um_segundo, {**alinhar, "chars": list("tu")})
    palavras = turno.audio.palavras
    # o 2º pedaço começa depois de 1 s de áudio (o tempo veio relativo ao pedaço)
    assert palavras == [{"texto": "Oitu", "inicio_ms": 0.0, "fim_ms": 1200.0, "destaque": False}]
    assert turno.recebeu_alinhamento


@pytest.fixture
def ponte(monkeypatch):
    p = hud.PonteHUD()
    monkeypatch.setattr(hud, "_ponte", p)
    p.privacidade(True)
    yield p
    if p._audio is not None:
        p._audio.encerrar()


class SaidaFalsa:
    """sounddevice falso: chama o callback de saída em blocos, como a placa de som."""

    PortAudioError = RuntimeError

    class CallbackStop(Exception):
        pass

    def __init__(self):
        self.tocado = bytearray()

    def RawOutputStream(self, callback, finished_callback, channels, **_):  # noqa: N802
        dono = self

        class Fluxo:
            def __enter__(self):
                while True:
                    saida = bytearray(512 * 2 * channels)
                    try:
                        callback(saida, 512, None, None)
                    except dono.CallbackStop:
                        dono.tocado.extend(saida)
                        break
                    dono.tocado.extend(saida)
                    time.sleep(512 / TAXA)  # em tempo real, como a placa de som
                finished_callback()
                return self

            def __exit__(self, *_):
                return False

        return Fluxo()


def tocar_na_saida(eventos):
    saida = SaidaFalsa()

    def tocar(som):
        fila = hud._ponte.assinar()
        hud.reproducao(True)
        try:
            audio._tocar_partes(saida, som, 0, None)
            time.sleep(0.2)  # a HUD publica numa linha própria, a 20 Hz
        finally:
            hud.reproducao(False)
        while not fila.empty():
            evento = fila.get()
            if evento.get("tipo") == "fala_temporizada":
                eventos.append(evento)

    return tocar


@pytest.mark.parametrize("modo,precisao", [("normal", "alinhada"), ("sem_alinhamento", "estimada")])
def test_hud_recebe_as_palavras_alinhadas_ou_a_estimativa(v4, ponte, modo, precisao):
    with DialogoFalso(modo=modo) as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        eventos = []
        locutor = LocutorDialogo(
            dialogo, transformar, voz, tocar_na_saida(eventos), time.perf_counter()
        )
        locutor.falar("{alegre} Bom dia, Gabriel.")
        locutor.terminar()
    assert eventos, "a HUD não recebeu as palavras"
    fala = eventos[-1]
    fala = fala.get("dados", fala)
    assert fala["precisao"] == precisao
    assert [p["texto"] for p in fala["palavras"]] == ["Bom", "dia,", "Gabriel."]
    assert ponte.estado["emocao"] == "alegre"


# --- connection: keep_alive, idleness and barge-in ---------------------------------------------


def test_keep_alive_entre_as_respostas_e_fecha_quando_ociosa():
    with DialogoFalso() as servidor:
        sessao = SessaoDialogo(
            CHAVE, "v", "eleven_v4_turbo", url=servidor.url, manter_viva_s=0.2, ociosa_s=1.2
        )
        turno = sessao.novo_turno()
        turno.enviar("Oi.")
        turno.finalizar()
        assert turno.terminado.wait(3)
        time.sleep(0.8)
        assert len(servidor.mensagens("keep_alive")) >= 2
        assert all(m == {"keep_alive": True} for m in servidor.mensagens("keep_alive"))
        assert sessao.aberta()
        prazo = time.monotonic() + 3
        while sessao.aberta() and time.monotonic() < prazo:
            time.sleep(0.05)
        assert not sessao.aberta()  # ociosa: fechou sozinha
        sessao.novo_turno().cancelar()
    assert len(servidor.conexoes) == 2  # a próxima resposta abriu outra


def test_keep_alive_enquanto_o_cerebro_pensa():
    with DialogoFalso() as servidor:
        sessao = SessaoDialogo(CHAVE, "v", "eleven_v4_turbo", url=servidor.url, manter_viva_s=0.2)
        turno = sessao.novo_turno()  # aberto, nada enviado ainda
        time.sleep(0.7)
        assert servidor.mensagens("keep_alive")
        turno.enviar("Pronto.")
        turno.finalizar()
        assert turno.terminado.wait(3) and turno.erro is None


def test_barge_in_fecha_a_sessao_e_a_proxima_nao_mistura_audio(v4):
    with DialogoFalso(pedacos=20, atraso=0.05) as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        tocados = []
        locutor = LocutorDialogo(
            dialogo, transformar, voz, tocar_tudo(tocados), time.perf_counter()
        )
        locutor.falar("Primeira resposta que vai ser cortada no meio.")
        assert locutor.turno.audio.primeira.wait(3)
        locutor.cancelar()
        locutor.terminar()
        assert locutor.turno.cancelado and not locutor.tempos.erros
        assert locutor.reserva is None  # cortar não é falha: nada de reserva
        prazo = time.monotonic() + 3
        while servidor.fechadas < 1 and time.monotonic() < prazo:
            time.sleep(0.02)
        assert servidor.fechadas == 1  # a conexão do barge-in foi fechada
        nova = []
        falar(dialogo, transformar, voz, ["Segunda."], nova)
    assert len(servidor.conexoes) == 2
    assert nova == [pcm_de("Segunda. ")]  # nada da primeira resposta
    assert len(tocados[0]) < len(pcm_de("Primeira resposta que vai ser cortada no meio. "))


# --- fallback (HTTP flash) --------------------------------------------------------------------


def test_erro_do_dialogo_cai_no_flash_por_http_e_guarda_o_motivo(v4):
    pcm = b"\x01\x00" * 2205
    with (
        DialogoFalso(modo="erro") as servidor,
        ServicoFalso(lambda *_: (200, "audio/pcm", pcm)) as nuvem,
    ):
        _, voz, dialogo, transformar = v4(servidor, http=nuvem)
        tocados = []
        locutor = falar(dialogo, transformar, voz, ["Oi.", "Tudo bem?"], tocados)
    assert locutor.reserva is not None
    assert "unsupported_model (400)" in locutor.motivo_reserva
    assert "texto do servidor" not in locutor.motivo_reserva  # só o código, não a mensagem
    assert "eleven_flash_v2_5" in dialogo.aviso
    corpos = [json.loads(p[2]) for p in nuvem.pedidos]
    assert {c["model_id"] for c in corpos} == {"eleven_flash_v2_5"}
    assert " ".join(c["text"] for c in corpos).split() == ["Oi.", "Tudo", "bem?"]
    assert tocados and not locutor.tempos.erros


@pytest.mark.parametrize(
    "modo,motivo",
    [("mudo", "recebi: is_final_audio_for_turn"), ("calado", "recebi: nenhuma mensagem")],
)
def test_turno_sem_audio_e_falha_e_cai_no_flash(v4, modo, motivo):
    pcm = b"\x01\x00" * 2205
    with (
        DialogoFalso(modo=modo) as servidor,
        ServicoFalso(lambda *_: (200, "audio/pcm", pcm)) as nuvem,
    ):
        _, voz, dialogo, transformar = v4(servidor, http=nuvem)
        dialogo.sessao().fim_do_turno_s = 0.5
        tocados = []
        locutor = falar(dialogo, transformar, voz, ["Oi."], tocados)
    assert locutor.reserva is not None and motivo in locutor.motivo_reserva
    assert "Oi." not in locutor.motivo_reserva  # o motivo não leva o texto
    assert len(nuvem.pedidos) == 1 and tocados  # a resposta saiu pelo flash


def test_sessao_reabre_depois_de_um_turno_que_falhou():
    with DialogoFalso(modo="calado") as servidor:
        sessao = SessaoDialogo(
            CHAVE, "v", "eleven_v4_turbo", url=servidor.url, primeiro_audio_s=0.5
        )
        turno = sessao.novo_turno()
        turno.enviar("Oi.")
        assert turno.terminado.wait(3) and "em 0 s" not in str(turno.erro)
        assert "não mandou áudio" in str(turno.erro)
        sessao.novo_turno().cancelar()
    assert len(servidor.conexoes) == 2


def test_sem_conexao_cai_no_flash_desde_o_inicio(v4):
    pcm = b"\x01\x00" * 2205
    with ServicoFalso(lambda *_: (200, "audio/pcm", pcm)) as nuvem:
        _, voz, dialogo, transformar = v4(None, http=nuvem)
        dialogo.sessao().timeout = 2
        tocados = []
        locutor = falar(dialogo, transformar, voz, ["Oi."], tocados)
        assert locutor.reserva is not None and "diálogo do ElevenLabs" in locutor.motivo_reserva
        # em pausa: a próxima resposta já vai direto pelo HTTP
        assert dialogo.em_reserva
        falar(dialogo, transformar, voz, ["De novo."], tocados)
    assert len(nuvem.pedidos) == 2


def test_fala_avulsa_tambem_usa_o_dialogo(v4):
    with DialogoFalso() as servidor:
        _, voz, _, _ = v4(servidor)
        wav = voz.sintetizar("Teste.")
    assert audio.ler_wav(wav)[0] == pcm_de("Teste. ")


# --- diagnostics ------------------------------------------------------------------------------


def test_conversa_v4_de_ponta_a_ponta_grava_o_diagnostico(criar_raiz, monkeypatch):
    resposta = "Claro, posso ajudar. O que precisa?"
    with OllamaFalso([resposta]) as ollama, DialogoFalso() as servidor:
        monkeypatch.setattr(elevenlabs_dialogo, "URL", servidor.url)
        config = config_v4(criar_raiz, ambiente={"OLLAMA_HOST": ollama.host})
        tocados, saida = [], io.StringIO()
        comandos = iter(["informação pessoal secreta", "sair"])
        conversar_por_voz(
            config,
            entrada=lambda _: next(comandos),
            saida=saida,
            medir=True,
            tocar=tocar_tudo(tocados),
        )
    assert len(servidor.conexoes) == 1 and len(tocados) == 1
    texto = saida.getvalue()
    assert "[voz: eleven_v4_turbo (dialogo), continuidade ativa" in texto
    medida = diagnostico_voz.ler(config.pasta_dados)
    assert medida.modelo == "eleven_v4_turbo" and medida.via == "dialogo"
    assert medida.alinhamento and medida.pedido_ate_primeiro_pcm_ms is not None
    bruto = (config.pasta_dados / diagnostico_voz.ARQUIVO).read_text(encoding="utf-8")
    for proibido in (CHAVE, "secreta", "ajudar"):
        assert proibido not in bruto
    linhas = verificar(config)
    assert any("Modelo efetivo" in linha and "eleven_v4_turbo" in linha for linha in linhas)
    assert any("Continuidade ElevenLabs" in linha and "ativa" in linha for linha in linhas)
    assert any("Última fala" in linha for linha in linhas)


def test_verificar_mostra_flash_e_continuidade_desativada(criar_raiz):
    config = config_v4(criar_raiz, extra="continuidade = false\n", modelo="eleven_flash_v2_5")
    linhas = verificar(config)
    assert any(
        "Modelo efetivo" in linha and "eleven_flash_v2_5 (http)" in linha for linha in linhas
    )
    assert any("Continuidade ElevenLabs" in linha and "desativada" in linha for linha in linhas)


# --- alignment time reference ---------------------------------------------------------------------


def _turno_com(trechos):
    """Turno que recebe (pcm_ms, chars, inicios) em sequência; devolve as palavras finais."""
    sessao = SessaoDialogo("x", "v", "eleven_v4_turbo")
    turno = elevenlabs_dialogo.Turno(sessao)
    for duracao_ms, chars, inicios in trechos:
        pcm = b"\x00\x00" * round(duracao_ms / 1000 * TAXA)
        alinhar = {
            "chars": list(chars),
            "char_start_times_ms": inicios,
            "char_durations_ms": [50] * len(chars),
        }
        turno._receber(pcm, alinhar)
    return turno


def test_alinhamento_relativo_ao_trecho_vira_posicao_no_pcm():
    # 3 trechos de 500 ms; cada um traz "ab " com tempos a partir de 0 (relativos ao trecho)
    turno = _turno_com(
        [(500, "um ", [0, 60, 120]), (500, "do ", [0, 60, 120]), (500, "tr", [0, 60])]
    )
    inicios = [p["inicio_ms"] for p in turno.audio.palavras]
    assert inicios == [0.0, 500.0, 1000.0]  # cada palavra onde o seu áudio está no PCM
    assert turno.referencia == "trecho"


def test_alinhamento_absoluto_no_turno_nao_soma_de_novo():
    turno = _turno_com(
        [(500, "um ", [0, 60, 120]), (500, "do ", [500, 560, 620]), (500, "tr", [1000, 1060])]
    )
    assert [p["inicio_ms"] for p in turno.audio.palavras] == [0.0, 500.0, 1000.0]
    assert turno.referencia == "turno"


def test_referencia_decidida_uma_vez_nao_salta_no_meio_da_fala():
    # 2º trecho decide "trecho"; o 3º vem com tempo grande (parece absoluto), mas continua relativo
    turno = _turno_com(
        [(500, "um ", [0, 60, 120]), (500, "do ", [0, 60, 120]), (500, "tr", [700, 760])]
    )
    inicios = [p["inicio_ms"] for p in turno.audio.palavras]
    assert inicios == sorted(inicios) and inicios[-1] == 1700.0


def test_silencio_inicial_desloca_as_palavras_junto_com_o_som():
    from nora.audio import _deslocar

    palavras = [{"texto": "oi", "inicio_ms": 0.0, "fim_ms": 100.0, "destaque": False}]
    assert _deslocar(palavras, 200)[0]["inicio_ms"] == 200.0
    assert _deslocar(palavras, 0) == palavras


def test_servidor_falso_com_varios_trechos_de_offsets_conhecidos(v4):
    """Vários trechos de áudio por frase, alinhamento relativo a cada trecho: as palavras ficam na
    posição real do PCM (a soma das durações dos trechos anteriores)."""
    with DialogoFalso(pedacos=3, modo="trechos") as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        turno = dialogo.novo_turno()
        turno.enviar("abc def")
        turno.finalizar()
        assert turno.terminado.wait(5)
        palavras = turno.audio.palavras
    assert [p["texto"] for p in palavras] == ["abc", "def"]
    # "def" começa no 2º trecho: posição = duração do 1º trecho
    pcm_total = len(pcm_de("abc def "))
    primeiro_ms = (pcm_total // 3 // 2 * 2) / 2 / TAXA * 1000
    assert palavras[1]["inicio_ms"] == pytest.approx(primeiro_ms, abs=1)


# --- fallback mid-speech --------------------------------------------------------------------------


def _flash(pedidos_texto):
    def responder(caminho, cabecalhos, corpo):
        pedidos_texto.append(json.loads(corpo)["text"])
        return 200, "audio/pcm", b"\x01\x00" * 2205

    return responder


def test_falha_depois_do_audio_continua_na_reserva_sem_repetir(v4):
    ditos = []
    with DialogoFalso(modo="cai_no_meio") as servidor, ServicoFalso(_flash(ditos)) as nuvem:
        _, voz, dialogo, transformar = v4(servidor, http=nuvem)
        tocados, ordem = [], []
        locutor = None

        def tocar(som):
            ordem.append("v4" if som is locutor.turno.audio else "flash")
            tocados.append(som if isinstance(som, bytes) else b"".join(som.partes()))

        locutor = LocutorDialogo(dialogo, transformar, voz, tocar, time.perf_counter())
        locutor.falar("Primeira frase inteira.")
        assert locutor.turno.audio.primeira.wait(3)
        time.sleep(0.2)
        locutor.falar("Segunda frase.")
        time.sleep(0.4)
        locutor.falar("Terceira frase.")
        locutor.terminar()
    assert tocados[0] == pcm_de("Primeira frase inteira. ")  # o que já tinha chegado tocou inteiro
    # a reserva continua da 2ª frase: nada da 1ª se repete, e na ordem
    assert " ".join(ditos).split() == ["Segunda", "frase.", "Terceira", "frase."]
    assert ordem[0] == "v4" and set(ordem[1:]) == {"flash"}
    assert locutor.reservas and "eleven_flash_v2_5" in dialogo.aviso
    assert not locutor.cortada and not locutor.tempos.erros


def test_falha_sem_alinhamento_para_de_modo_claro_e_permite_repetir(v4):
    ditos = []
    with DialogoFalso(modo="cai_sem_alinhamento") as servidor, ServicoFalso(_flash(ditos)) as nuvem:
        _, voz, dialogo, transformar = v4(servidor, http=nuvem)
        tocados = []
        locutor = LocutorDialogo(
            dialogo, transformar, voz, tocar_tudo(tocados), time.perf_counter()
        )
        locutor.falar("Uma frase.")
        assert locutor.turno.audio.primeira.wait(3)
        time.sleep(0.2)
        locutor.falar("Outra frase.")
        time.sleep(0.4)
        locutor.falar("Mais uma.")
        locutor.terminar()
    assert locutor.cortada and not ditos  # sem limite confiável: não chuta onde continuar
    assert any("repete a resposta que caiu" in e for e in locutor.tempos.erros)
    assert locutor.texto == "Uma frase. Outra frase. Mais uma."


def test_texto_restante_corta_em_palavra_e_ignora_etiquetas():
    from nora.conversa_voz import texto_restante

    frases = ["{alegre} Oi, Gabriel!", "Tudo certo por aqui."]
    assert texto_restante(frases, list("[happy] Oi, Gabriel! ")) == "Tudo certo por aqui."
    assert texto_restante(frases, list("Oi, Gabriel! Tu")) == "certo por aqui."  # pula a palavra
    assert texto_restante(frases, list("Oi Gabriel Tudo certo por aqui")) == ""
    assert texto_restante(frases, []) is None
    assert texto_restante(frases, list("x" * 200)) is None


def test_audio_sem_alinhamento_continua_tocando_sem_reserva(v4):
    with DialogoFalso(modo="sem_alinhamento") as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        tocados = []
        locutor = falar(dialogo, transformar, voz, ["Sem tempo das palavras."], tocados)
    assert tocados == [pcm_de("Sem tempo das palavras. ")]
    assert locutor.reserva is None and not locutor.tempos.erros
    assert not locutor.turno.recebeu_alinhamento


def test_cancelar_e_retomar_nao_repete_nem_embaralha_palavras(v4):
    with DialogoFalso(pedacos=20, atraso=0.05) as servidor:
        _, voz, dialogo, transformar = v4(servidor)
        locutor = LocutorDialogo(dialogo, transformar, voz, tocar_tudo([]), time.perf_counter())
        locutor.falar("Palavras velhas da resposta cortada.")
        assert locutor.turno.audio.primeira.wait(3)
        locutor.cancelar()
        locutor.terminar()
        nova = LocutorDialogo(dialogo, transformar, voz, tocar_tudo([]), time.perf_counter())
        nova.falar("Agora a nova resposta.")
        nova.terminar()
        palavras = [p["texto"] for p in nova.turno.audio.palavras]
    assert palavras == ["Agora", "a", "nova", "resposta."]  # sem sobras, na ordem


def test_repete_a_resposta_que_caiu_sem_chamar_o_cerebro(criar_raiz):
    from nora.conversa import nova_conversa
    from nora.conversa_voz import responder_falando

    class CerebroQueNaoPodeSerChamado:
        situacao = "completa"

        def responder(self, mensagens):
            raise AssertionError("não devia perguntar de novo ao cérebro")

    config = carregar(
        criar_raiz(local='[voz]\nmotor = "piper"\nreserva = ""\n[memoria]\nativa = false\n'),
        ambiente={"OLLAMA_HOST": "http://127.0.0.1:9"},
    )
    conversa = nova_conversa(
        config, CerebroQueNaoPodeSerChamado(), memoria=None, notas=None, observador=None
    )
    conversa.fala_cortada = "Resposta que tinha caído."

    class VozEco:
        def sintetizar(self, frase):
            return frase.encode()

    tocados, saida = [], []
    responder_falando(
        conversa, VozEco(), tocados.append, "repete a resposta que caiu", time.perf_counter(), 0.0,
        lambda *a, **k: saida.append(a[0] if a else ""), False,
    )  # fmt: skip
    assert b"".join(tocados).decode() == "Resposta que tinha caído."
    assert conversa.fala_cortada == ""


def test_diagnostico_da_resposta_que_trocou_para_a_reserva_no_meio(criar_raiz, monkeypatch):
    resposta = "Primeira parte da resposta. Segunda parte. Terceira parte."
    ditos = []
    with (
        OllamaFalso([resposta]) as ollama,
        DialogoFalso(modo="cai_no_meio") as servidor,
        ServicoFalso(_flash(ditos)) as nuvem,
    ):
        monkeypatch.setattr(elevenlabs_dialogo, "URL", servidor.url)
        monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{nuvem.url}/v1/text-to-speech")
        config = config_v4(criar_raiz, ambiente={"OLLAMA_HOST": ollama.host})
        saida = io.StringIO()
        comandos = iter(["pergunta pessoal secreta", "sair"])
        conversar_por_voz(
            config, entrada=lambda _: next(comandos), saida=saida, medir=True, tocar=tocar_tudo([])
        )
    medida = diagnostico_voz.ler(config.pasta_dados)
    assert medida.via == "dialogo + http (reserva)" and medida.continuidade == diagnostico_voz.ERRO
    assert medida.geracoes >= 2 and medida.reservas
    assert "Primeira" not in " ".join(ditos)  # a reserva não repetiu o que já tocou
    bruto = (config.pasta_dados / diagnostico_voz.ARQUIVO).read_text(encoding="utf-8")
    for proibido in (CHAVE, "secreta", "Primeira", "Segunda"):
        assert proibido not in bruto
    assert "gerações" in saida.getvalue() and "reserva:" in saida.getvalue()


def test_diagnostico_http_conta_geracoes_e_tempos(criar_raiz, monkeypatch):
    with (
        OllamaFalso(
            ["Uma frase longa o bastante para ir sozinha. E outra frase também longa aqui."]
        ) as ollama,
        ServicoFalso(_flash([])) as nuvem,
    ):
        monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{nuvem.url}/v1/text-to-speech")
        config = config_v4(
            criar_raiz, modelo="eleven_flash_v2_5", ambiente={"OLLAMA_HOST": ollama.host}
        )
        comandos = iter(["oi", "sair"])
        conversar_por_voz(
            config,
            entrada=lambda _: next(comandos),
            saida=io.StringIO(),
            medir=True,
            tocar=tocar_tudo([]),
        )
    medida = diagnostico_voz.ler(config.pasta_dados)
    assert medida.via == "http" and medida.geracoes >= 1
    assert (
        medida.pedido_ate_primeiro_pcm_ms is not None
        and medida.pedido_ate_reproducao_ms is not None
    )


def test_diagnostico_le_arquivo_de_versao_anterior(tmp_path):
    (tmp_path / diagnostico_voz.ARQUIVO).write_text(
        json.dumps({"modelo": "m", "via": "http", "continuidade": "ativa", "campo_velho": 1}),
        encoding="utf-8",
    )
    medida = diagnostico_voz.ler(tmp_path)
    assert medida.modelo == "m" and medida.geracoes == 0 and medida.reservas == []
