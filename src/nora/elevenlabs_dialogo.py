"""ElevenLabs v4 por diálogo em tempo real (WebSocket `text-to-dialogue/stream-input`).

O v4 não aceita o text-to-speech comum (400 `unsupported_model`); só o Text to Dialogue. Uma
conexão fica aberta entre as respostas:

- 1ª mensagem: `voices` (exatamente uma, a voz da Nora) e `voice_settings` (só `stability` vale);
  a chave vai no cabeçalho `xi-api-key`, nunca na URL nem no log.
- Cada resposta é um turno: o texto vai aos pedaços (`inputs`, o primeiro com `new_turn: true`)
  conforme o modelo escreve, e `flush: true` no fim. O áudio volta aos pedaços (PCM em base64),
  com o alinhamento por caractere (`sync_alignment=true`), e toca conforme chega.
- Entre as respostas, `keep_alive` a cada `manter_viva_s` (o servidor fecha após 20 s sem
  mensagem); sem resposta por `ociosa_s`, a conexão é fechada e reaberta na próxima.
- Barge-in: o turno é cancelado, o áudio para e a conexão é fechada; a próxima resposta abre uma
  limpa (nada de áudio de uma resposta tocando na outra).

Formato das mensagens conferido no SDK oficial (`elevenlabs` 2.77.0, tipos
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
MAX_PALAVRAS = 256  # limite da HUD (hud_contrato.json)
log = logging.getLogger("nora.voz")


def e_modelo_de_dialogo(modelo: str) -> bool:
    """Modelos que só funcionam pelo Text to Dialogue (o v4 e o v4 turbo)."""
    return modelo.startswith("eleven_v4")


def palavras_do_alinhamento(caracteres: list[tuple[str, float, float]]) -> list[dict]:
    """Junta os caracteres alinhados (caractere, início, fim, em ms) em palavras para a HUD: em
    ordem, sem sobreposição, sem as audio tags ([happy]) e no máximo as últimas 256."""
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
    """Uma resposta falada: o texto vai, o áudio volta (`audio`, tocável enquanto chega)."""

    def __init__(self, sessao: SessaoDialogo) -> None:
        self.sessao = sessao
        self.audio, self._por, self._fechar = AudioEmPartes.de_fila(TAXA)
        self.erro: Exception | None = None
        self.cancelado = False
        self.pedido: float | None = None  # perf_counter do primeiro texto enviado
        self.primeiro_pcm: float | None = None
        self.ultimo_audio = 0.0
        self.finalizado_em: float | None = None
        self.terminado = threading.Event()
        self.recebido_ms = 0.0
        self.recebeu_alinhamento = False
        self.recebidas: list[str] = []  # tipos de mensagem do servidor (diagnóstico, sem texto)
        self._caracteres: list[tuple[str, float, float]] = []

    @property
    def recebeu_audio(self) -> bool:
        return self.primeiro_pcm is not None

    def enviar(self, texto: str) -> None:
        """Manda um pedaço do texto (uma frase, conforme o modelo escreve)."""
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
        """Fim da resposta: gera o que ficou no buffer (`flush`)."""
        if self.terminado.is_set() or self.finalizado_em is not None:
            return
        self.finalizado_em = time.monotonic()
        if self.pedido is None:  # nada foi enviado: não há o que esperar
            self._concluir()
            return
        self.sessao._enviar({"flush": True}, self)

    def cancelar(self) -> None:
        """Barge-in: para o áudio na hora e descarta o resto desta resposta."""
        if self.terminado.is_set() and self.audio.cancelado.is_set():
            return
        self.cancelado = True
        self.audio.cancelar()
        self._concluir()
        self.sessao.fechar()

    # chamados pela linha que lê o WebSocket ------------------------------------------------

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
            # O tempo pode vir relativo ao pedaço (começa perto de 0) ou à fala toda: se vier
            # relativo, soma o áudio que já chegou.
            base = (
                self.recebido_ms
                if inicios and self.recebido_ms > 0 and inicios[0] < self.recebido_ms - 50
                else 0.0
            )
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
            # Texto enviado e nenhum áudio: é falha (cai na reserva), não uma resposta muda.
            vistas = ", ".join(dict.fromkeys(self.recebidas)) or "nenhuma mensagem"
            erro = ServicoIndisponivel(f"O ElevenLabs não mandou áudio (recebi: {vistas}).")
            self.sessao.ultimo_erro = f"sem áudio (recebi: {vistas})"
            log.warning("ElevenLabs v4: %s", self.sessao.ultimo_erro)
        if erro is not None and self.erro is None:
            self.erro = erro
        self.terminado.set()
        self._fechar(erro if not self.cancelado else None)


class SessaoDialogo:
    """A conexão com o ElevenLabs, reaproveitada entre as respostas."""

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
        self.conexoes = 0  # quantas vezes abriu (diagnóstico e testes)
        self.ultimo_erro = ""  # tipo e código, nunca texto pessoal nem a chave

    # conexão ---------------------------------------------------------------------------------

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
            # `__enter__`: a conexão fica aberta entre as respostas (fora de um `with`).
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
        """Começa uma resposta. Abre a conexão se ainda não estiver aberta (dá para chamar antes
        do modelo começar a escrever: a conexão fica pronta enquanto ele pensa)."""
        with self._trava:
            anterior = self._turno
            if anterior is not None and not anterior.terminado.is_set():
                anterior.cancelar()
            elif anterior is not None and anterior.erro is not None:
                self._fechar_ws()  # a resposta anterior falhou: começa numa conexão limpa
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

    # leitura (linha própria) -----------------------------------------------------------------

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
            # Erro do ElevenLabs: guarda só o identificador e o código (sem texto da conversa).
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
        """Relógios: fim do turno sem aviso, keep_alive e fechamento por ociosidade."""
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
                return True  # o áudio está chegando: o servidor não está ocioso
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
                return  # já fechada por nós (barge-in, ociosidade)
            self._ws = None
            self.ultimo_erro = motivo
            turno = self._turno
        if turno is not None and not turno.terminado.is_set():
            turno._concluir(ServicoIndisponivel(f"O diálogo do ElevenLabs {motivo}."))
