"""ElevenLabs v4 through real-time dialogue (WebSocket `text-to-dialogue/stream-input`).

v4 does not accept regular text-to-speech (400 `unsupported_model`); only Text to Dialogue. One
connection stays open between answers:

- 1st message: `voices` (exactly one, Nora's voice) and `voice_settings` (only `stability`
  counts); the key goes in the `xi-api-key` header, never in the URL or the log.
- Each answer is a turn: the text goes in chunks (`inputs`, the first with `new_turn: true`) as
  the model writes, and `flush: true` at the end. The audio comes back in chunks (base64 PCM),
  with per-character alignment (`sync_alignment=true`), and plays as it arrives.
- Between answers, `keep_alive` every `manter_viva_s` (the server closes after 20 s without a
  message); with no answer for `ociosa_s`, the connection is closed and reopened on the next one.
- Barge-in: the turn is cancelled, the audio stops and the connection is closed; the next answer
  opens a clean one (no audio from one answer playing into another).

Message format checked against the official SDK (`elevenlabs` 2.77.0, types
`TextToDialogueWebsocket*`).
"""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
import urllib.parse

from nora.audio import AudioEmPartes
from nora.servico import ServicoIndisponivel

URL = "wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input"
TAXA = 22_050
MAX_PALAVRAS = 256  # HUD limit (hud_contrato.json)
log = logging.getLogger("nora.voz")


def e_modelo_de_dialogo(modelo: str) -> bool:
    """Models that only work through Text to Dialogue (v4 and v4 turbo)."""
    return modelo.startswith("eleven_v4")


def palavras_do_alinhamento(caracteres: list[tuple[str, float, float]]) -> list[dict]:
    """Joins the aligned characters (character, start, end, in ms) into words for the HUD: in
    order, without overlap, without the audio tags ([happy]) and at most the last 256."""
    palavras: list[dict] = []
    atual, inicio, fim, dentro_de_tag = "", 0.0, 0.0, False

    def fechar() -> None:
        nonlocal atual
        texto = atual.strip()
        if texto and any(c.isalnum() for c in texto):
            anterior = palavras[-1]["fim_ms"] if palavras else 0.0
            comeco = max(inicio, anterior)
            palavras.append(
                {
                    "texto": texto[:80],
                    "inicio_ms": round(comeco, 3),
                    "fim_ms": round(max(fim, comeco + 1), 3),
                    "destaque": False,
                }
            )
        atual = ""

    for caractere, comeco, termino in caracteres:
        if caractere == "[":
            fechar()
            dentro_de_tag = True
            continue
        if dentro_de_tag:
            dentro_de_tag = caractere != "]"
            continue
        if caractere.isspace():
            fechar()
            continue
        if not atual:
            inicio = comeco
        atual += caractere
        fim = termino
    fechar()
    return palavras[-MAX_PALAVRAS:]


class Turno:
    """One spoken answer: the text goes out, the audio comes back (`audio`, playable as it
    arrives)."""

    def __init__(self, sessao: SessaoDialogo) -> None:
        self.sessao = sessao
        self.audio, self._por, self._fechar = AudioEmPartes.de_fila(TAXA)
        self.erro: Exception | None = None
        self.cancelado = False
        self.pedido: float | None = None  # perf_counter of the first text sent
        self.primeiro_pcm: float | None = None
        self.ultimo_audio = 0.0
        self.finalizado_em: float | None = None
        self.terminado = threading.Event()
        self.recebido_ms = 0.0
        self.recebeu_alinhamento = False
        self.recebidas: list[str] = []  # server message types (diagnostics, no text)
        self._caracteres: list[tuple[str, float, float]] = []
        # Reference for the alignment times, decided once per turn and fixed from then on:
        # "trecho" (each message starts near 0) or "turno" (counted from the start of the speech).
        self.referencia: str | None = None

    @property
    def recebeu_audio(self) -> bool:
        return self.primeiro_pcm is not None

    def enviar(self, texto: str) -> None:
        """Sends a piece of the text (a sentence, as the model writes)."""
        if self.terminado.is_set() or not texto.strip():
            return
        primeiro = self.pedido is None
        if primeiro:
            self.pedido = time.perf_counter()
        entrada = {"text": texto if texto.endswith(" ") else texto + " "}
        entrada["voice_id"] = self.sessao.voz_id
        if primeiro:
            entrada["new_turn"] = True
        self.sessao._enviar({"inputs": [entrada]}, self)

    def finalizar(self) -> None:
        """End of the answer: generates what is left in the buffer (`flush`)."""
        if self.terminado.is_set() or self.finalizado_em is not None:
            return
        self.finalizado_em = time.monotonic()
        if self.pedido is None:  # nothing was sent: nothing to wait for
            self._concluir()
            return
        self.sessao._enviar({"flush": True}, self)

    def cancelar(self) -> None:
        """Barge-in: stops the audio immediately and discards the rest of this answer."""
        if self.terminado.is_set() and self.audio.cancelado.is_set():
            return
        self.cancelado = True
        self.audio.cancelar()
        self._concluir()
        self.sessao.fechar()

    # called by the thread that reads the WebSocket -----------------------------------------

    def _receber(self, pcm: bytes, alinhamento: dict | None) -> None:
        if self.terminado.is_set():
            return
        agora = time.perf_counter()
        if self.primeiro_pcm is None:
            self.primeiro_pcm = agora
        self.ultimo_audio = time.monotonic()
        if alinhamento and alinhamento.get("chars"):
            inicios = alinhamento.get("char_start_times_ms") or []
            duracoes = alinhamento.get("char_durations_ms") or []
            # The official SDK documents, for the TTS WebSocket, times relative to the returned
            # chunk. The dialogue one does not say; so the reference is decided on the first
            # alignment that arrives after some audio and does not change again in the turn (a
            # server that switched between the two does not shift the words mid-speech).
            if self.referencia is None and inicios and self.recebido_ms > 0:
                self.referencia = "trecho" if inicios[0] < self.recebido_ms - 50 else "turno"
            # Base = position, in this turn's PCM, where this message's audio starts.
            base = self.recebido_ms if self.referencia == "trecho" else 0.0
            for caractere, comeco, duracao in zip(
                alinhamento["chars"], inicios, duracoes, strict=False
            ):
                self._caracteres.append((caractere, base + comeco, base + comeco + duracao))
            self.recebeu_alinhamento = True
            self.audio.definir_palavras(palavras_do_alinhamento(self._caracteres))
        self.recebido_ms += len(pcm) / (2 * TAXA) * 1000
        self._por(pcm)

    def _concluir(self, erro: Exception | None = None) -> None:
        if self.terminado.is_set():
            return
        if (
            erro is None
            and not self.cancelado
            and self.pedido is not None
            and not self.recebeu_audio
        ):
            # Text sent and no audio: it is a failure (falls back), not a silent answer.
            vistas = ", ".join(dict.fromkeys(self.recebidas)) or "nenhuma mensagem"
            erro = ServicoIndisponivel(f"O ElevenLabs não mandou áudio (recebi: {vistas}).")
            self.sessao.ultimo_erro = f"sem áudio (recebi: {vistas})"
            log.warning("ElevenLabs v4: %s", self.sessao.ultimo_erro)
        if erro is not None and self.erro is None:
            self.erro = erro
        self.terminado.set()
        self._fechar(erro if not self.cancelado else None)


class SessaoDialogo:
    """The connection to ElevenLabs, reused across answers."""

    def __init__(
        self,
        chave: str,
        voz_id: str,
        modelo: str,
        estabilidade: float = 0.5,
        url: str | None = None,
        manter_viva_s: float = 10.0,
        ociosa_s: float = 120.0,
        fim_do_turno_s: float = 4.0,
        timeout: float = 10.0,
        primeiro_audio_s: float = 10.0,
    ) -> None:
        self.chave, self.voz_id, self.modelo = chave, voz_id, modelo
        self.estabilidade = estabilidade
        self.url = url or URL
        self.manter_viva_s, self.ociosa_s = manter_viva_s, ociosa_s
        self.fim_do_turno_s, self.timeout = fim_do_turno_s, timeout
        self.primeiro_audio_s = primeiro_audio_s
        self._trava = threading.RLock()
        self._ws = None
        self._turno: Turno | None = None
        self._ultimo_envio = 0.0
        self._ultima_atividade = 0.0
        self.conexoes = 0  # how many times it opened (diagnostics and tests)
        self.ultimo_erro = ""  # type and code, never personal text nor the key

    # connection ------------------------------------------------------------------------------

    def _endereco(self) -> str:
        consulta = urllib.parse.urlencode(
            {"model_id": self.modelo, "output_format": f"pcm_{TAXA}", "sync_alignment": "true"}
        )
        return f"{self.url}?{consulta}"

    def _abrir(self) -> None:
        try:
            from websockets.sync.client import connect
        except ImportError as erro:
            raise ServicoIndisponivel(
                'Falta o pacote websockets para o ElevenLabs v4: python -m pip install -e ".[voz]"'
            ) from erro
        destino = urllib.parse.urlsplit(self.url)
        local = destino.hostname in ("127.0.0.1", "localhost", "::1")
        try:
            # `__enter__`: the connection stays open between answers (outside a `with`).
            self._ws = connect(
                self._endereco(),
                additional_headers={"xi-api-key": self.chave},
                open_timeout=self.timeout,
                max_size=None,
                **({"proxy": None} if local else {}),
            ).__enter__()
            self._ws.send(
                json.dumps(
                    {"voices": [self.voz_id], "voice_settings": {"stability": self.estabilidade}}
                )
            )
        except Exception as erro:
            self._ws = None
            self.ultimo_erro = f"conexão ({type(erro).__name__})"
            raise ServicoIndisponivel(
                f"Não consegui abrir o diálogo do ElevenLabs ({type(erro).__name__})."
            ) from erro
        self.conexoes += 1
        self._ultimo_envio = self._ultima_atividade = time.monotonic()
        threading.Thread(target=self._ler, args=(self._ws,), daemon=True, name="nora-v4").start()

    def aberta(self) -> bool:
        return self._ws is not None

    def novo_turno(self) -> Turno:
        """Starts an answer. Opens the connection if it is not open yet (it can be called before
        the model starts writing: the connection gets ready while it thinks)."""
        with self._trava:
            anterior = self._turno
            if anterior is not None and not anterior.terminado.is_set():
                anterior.cancelar()
            elif anterior is not None and anterior.erro is not None:
                self._fechar_ws()  # the previous answer failed: start on a clean connection
            if self._ws is None:
                self._abrir()
            self._turno = Turno(self)
            self._ultima_atividade = time.monotonic()
            return self._turno

    def _enviar(self, mensagem: dict, turno: Turno) -> None:
        with self._trava:
            ws = self._ws
            if ws is None or turno is not self._turno:
                turno._concluir(ServicoIndisponivel("O diálogo do ElevenLabs fechou."))
                return
            try:
                ws.send(json.dumps(mensagem))
            except Exception as erro:
                self.ultimo_erro = f"envio ({type(erro).__name__})"
                turno._concluir(
                    ServicoIndisponivel(f"O diálogo do ElevenLabs caiu ({type(erro).__name__}).")
                )
                self._fechar_ws()
                return
            self._ultimo_envio = self._ultima_atividade = time.monotonic()

    def fechar(self) -> None:
        with self._trava:
            self._fechar_ws()

    def _fechar_ws(self) -> None:
        ws, self._ws = self._ws, None
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

    # reading (own thread) --------------------------------------------------------------------

    def _ler(self, ws) -> None:
        from websockets.exceptions import ConnectionClosed

        while True:
            try:
                bruto = ws.recv(timeout=0.25)
            except TimeoutError:
                bruto = None
            except ConnectionClosed as erro:
                self._caiu(ws, f"fechou ({getattr(erro.rcvd, 'code', '?')})")
                return
            except Exception as erro:
                self._caiu(ws, f"leitura ({type(erro).__name__})")
                return
            if bruto is not None:
                self._mensagem(ws, bruto)
            if not self._cuidar(ws):
                return

    def _mensagem(self, ws, bruto) -> None:
        try:
            mensagem = json.loads(bruto)
        except (TypeError, ValueError):
            return
        turno = self._turno
        if turno is not None:
            for tipo in mensagem if not mensagem.get("audio") else ["audio"]:
                if tipo not in turno.recebidas and len(turno.recebidas) < 10:
                    turno.recebidas.append(str(tipo)[:40])
        if mensagem.get("error") or ("message" in mensagem and "code" in mensagem):
            # ElevenLabs error: keep only the identifier and the code (no conversation text).
            self.ultimo_erro = f"{mensagem.get('error', 'erro')} ({mensagem.get('code', '?')})"
            log.warning("ElevenLabs v4 recusou: %s", self.ultimo_erro)
            if turno is not None:
                turno._concluir(
                    ServicoIndisponivel(f"O ElevenLabs recusou o diálogo: {self.ultimo_erro}.")
                )
            return
        if turno is None:
            return
        if mensagem.get("audio"):
            try:
                pcm = base64.b64decode(mensagem["audio"])
            except (TypeError, ValueError):
                return
            turno._receber(pcm, mensagem.get("alignment"))
        if mensagem.get("is_final_audio_for_turn") and turno.finalizado_em is not None:
            turno._concluir()

    def _cuidar(self, ws) -> bool:
        """Timers: end of turn without notice, keep_alive and closing on idleness."""
        agora = time.monotonic()
        with self._trava:
            if ws is not self._ws:
                return False
            turno = self._turno
            ativo = turno is not None and not turno.terminado.is_set()
            if (
                ativo
                and turno.pedido is not None
                and not turno.recebeu_audio
                and time.perf_counter() - turno.pedido > self.primeiro_audio_s
            ):
                turno._concluir(
                    ServicoIndisponivel(
                        f"O ElevenLabs não mandou áudio em {self.primeiro_audio_s:g} s."
                    )
                )
                self.ultimo_erro = "sem áudio (tempo esgotado)"
                ativo = False
            if ativo and turno.finalizado_em is not None:
                ultimo = max(turno.finalizado_em, turno.ultimo_audio)
                if agora - ultimo > self.fim_do_turno_s:
                    turno._concluir()
                    ativo = False
            if ativo and turno.finalizado_em is not None:
                return True  # audio is arriving: the server is not idle
            if not ativo and agora - self._ultima_atividade > self.ociosa_s:
                self._fechar_ws()
                return False
            if agora - self._ultimo_envio > self.manter_viva_s:
                try:
                    ws.send(json.dumps({"keep_alive": True}))
                    self._ultimo_envio = agora
                except Exception:
                    self._fechar_ws()
                    return False
        return True

    def _caiu(self, ws, motivo: str) -> None:
        with self._trava:
            if ws is not self._ws:
                return  # already closed by us (barge-in, idleness)
            self._ws = None
            self.ultimo_erro = motivo
            turno = self._turno
        if turno is not None and not turno.terminado.is_set():
            turno._concluir(ServicoIndisponivel(f"O diálogo do ElevenLabs {motivo}."))
