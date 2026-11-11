"""Voice conversation (part 2 of v0.1.0): press Enter, speak, and Nora answers by speaking.

Ear (whisper-server), brain (Ollama) and voice (Piper) are separate services. The answer is split
into sentences while the model writes: one thread synthesizes the next sentence while another
plays the current one, so Nora starts speaking before she finishes thinking.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import TextIO

from nora import audio
from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import Config
from nora.conversa import COMANDOS_SAIR, Conversa, nova_conversa, pede_retomada
from nora.emocao import FiltroDeTela, emocoes_em
from nora.frases import SeparadorDeFrases
from nora.hud import emitir
from nora.hud_audio import contexto_fala
from nora.melhorias import iniciar as iniciar_melhorias
from nora.melhorias import ler_entrada
from nora.ouvido import OuvidoWhisper, dica_do_ouvido
from nora.prioridade import abafar_outros
from nora.servico import ServicoIndisponivel
from nora.troca_voz import atender_pedido, pedido_de_voz
from nora.voz import (
    VozComReserva,
    VozElevenLabs,
    VozHTTP,
    VozTrocavel,
    achar_dialogo,
    com_pronuncias_aprendidas,
    em_partes,
)

_FIM = object()


def _e_pergunta(frase: str) -> bool:
    return frase.rstrip(" \"'”)»").endswith("?")


# Up to how many characters of sentences already waiting go together in one voice request.
LIMITE_DO_LOTE = 400
# How long a short request (below [voz] juntar_curta) waits for the next sentence to go along.
ESPERA_PARA_JUNTAR = 1.5


@dataclass
class Tempos:
    """Seconds of each stage of an utterance, counted from the end of the recording."""

    transcricao: float = 0.0
    primeira_frase: float = 0.0
    comeco_da_voz: float = 0.0
    erros: list[str] = field(default_factory=list)


class Locutor:
    """Takes sentences and speaks them in order: one thread synthesizes, another plays."""

    def __init__(
        self,
        voz: VozHTTP | VozElevenLabs | VozComReserva,
        tocar: Callable[[bytes], None],
        inicio: float,
        abafar=nullcontext,
        juntar: int = 0,
        espera: float = ESPERA_PARA_JUNTAR,
    ) -> None:
        self.voz = voz
        self.juntar = juntar
        self.espera = espera
        self.tocar = tocar
        self.inicio = inicio
        self.abafar = abafar
        self.tempos = Tempos()
        # Diagnostics (no text): synthesis requests and HTTP path times.
        self.geracoes = 0
        self.primeiro_pedido: float | None = None
        self.primeiro_audio: float | None = None
        self.inicio_som: float | None = None
        self.silencio_ms = 0.0
        self.maior_silencio_ms = 0.0
        self._fim_anterior: float | None = None
        self._frases: queue.Queue = queue.Queue()
        self._audios: queue.Queue = queue.Queue(maxsize=2)
        self._sintese = threading.Thread(target=self._sintetizar, daemon=True)
        self._toque = threading.Thread(target=self._tocar, daemon=True)
        self._sintese.start()
        self._toque.start()

    def falar(self, frase: str) -> None:
        self._frases.put(frase)

    def cancelar(self) -> None:
        """Ctrl+C: what was already requested finishes playing (sentence by sentence cannot be
        cut)."""

    def terminar(self) -> None:
        """Waits for everything requested to be spoken."""
        self._frases.put(_FIM)
        self._sintese.join()
        self._toque.join()

    def _sintetizar(self) -> None:
        """Synthesizes the sentences in order. If several are already waiting (the voice is slower
        than the model, as with ComfyUI), joins them in one request: fewer requests, fewer
        pauses."""
        acabou = False
        anterior = None
        while not acabou:
            frase = self._frases.get()
            if frase is _FIM:
                break
            lote = [frase]
            # A question always closes the request: with the "?" at the end, the voice raises the
            # intonation; in the middle of the text, many models flatten it.
            while sum(len(f) for f in lote) < LIMITE_DO_LOTE and not _e_pergunta(lote[-1]):
                # A short request ("Hahaha, esse atchim!") waits a bit for the next sentence: alone,
                # it becomes a short clip that ends before the next one is ready (a pause), and the
                # voice restarts without context (the tone changes).
                curto = sum(len(f) for f in lote) < self.juntar
                try:
                    proxima = (
                        self._frases.get(timeout=self.espera)
                        if curto
                        else self._frases.get_nowait()
                    )
                except queue.Empty:
                    break
                if proxima is _FIM:
                    acabou = True
                    break
                lote.append(proxima)
            if self.tempos.erros:
                continue
            if isinstance(anterior, audio.AudioEmPartes):
                anterior.baixado.wait()
            try:
                texto = " ".join(lote)
                if self.primeiro_pedido is None:
                    self.primeiro_pedido = time.perf_counter()
                self.geracoes += 1
                anterior = em_partes(self.voz, texto)
                if self.primeiro_audio is None and not isinstance(anterior, audio.AudioEmPartes):
                    self.primeiro_audio = time.perf_counter()
                self._audios.put((anterior, texto))
            except ServicoIndisponivel as erro:
                self.tempos.erros.append(str(erro))
        self._audios.put(_FIM)

    def _tocar(self) -> None:
        item = self._audios.get()
        if item is _FIM:
            return
        with self.abafar():  # the other programs get quieter while she speaks
            while item is not _FIM:
                wav, texto = item
                em_streaming = isinstance(wav, audio.AudioEmPartes)
                if em_streaming:
                    wav.primeira.wait()
                    if self.primeiro_audio is None:
                        self.primeiro_audio = time.perf_counter()
                if not self.tempos.comeco_da_voz:
                    self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
                comeco = time.perf_counter()
                if self._fim_anterior is not None:  # silence between one chunk and the next
                    buraco = (comeco - self._fim_anterior) * 1000
                    self.silencio_ms += buraco
                    self.maior_silencio_ms = max(self.maior_silencio_ms, buraco)
                try:
                    with contexto_fala(texto):
                        self.tocar(wav)
                except Exception as erro:  # a speaker problem does not bring down the conversation
                    self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")
                if self.inicio_som is None:
                    self.inicio_som = (
                        (getattr(wav, "inicio_som", None) or comeco) if em_streaming else comeco
                    )
                if em_streaming:
                    self.silencio_ms += wav.silencio_ms
                    self.maior_silencio_ms = max(self.maior_silencio_ms, wav.maior_silencio_ms)
                self._fim_anterior = time.perf_counter()
                if em_streaming and wav.erro is not None:
                    self.tempos.erros.append(f"A voz parou no meio da frase: {wav.erro}")
                item = self._audios.get()


def texto_restante(frases: list[str], alinhados: list[str]) -> str | None:
    """What is left to say after what the audio already covered, cut at a word boundary.

    `alinhados` are the characters the ElevenLabs alignment already covered (received audio,
    which will play in full). The count uses only letters and digits, without the emotion tags
    ({calma}) and the audio tags ([happy]). A half word is skipped (better than repeating what
    was already heard). Returns None if there is no reliable boundary (no alignment, or a count
    larger than the text)."""

    def letras(texto: str):
        dentro = ""
        for i, c in enumerate(texto):
            if dentro:
                if c == dentro:
                    dentro = ""
                continue
            if c in "{[":
                dentro = "}" if c == "{" else "]"
                continue
            if c.isalnum():
                yield i

    cobertas = sum(1 for _ in letras("".join(alinhados)))
    if cobertas == 0:
        return None
    texto = " ".join(frases)
    posicoes = list(letras(texto))
    if cobertas > len(posicoes):
        return None
    if cobertas == len(posicoes):
        return ""
    corte = posicoes[cobertas - 1] + 1
    while corte < len(texto) and texto[corte].isalnum():  # finish the started word
        corte += 1
    return texto[corte:].lstrip(" ,.;:!?")


class LocutorDialogo:
    """ElevenLabs v4 (dialogue): a single connection; each sentence goes as soon as the brain
    finishes it and the audio plays as it arrives, in continuous playback (no request or play per
    sentence).

    Same interface as `Locutor`. If the dialogue fails, the reason goes to `motivo_reserva` and:
    - before the 1st audio: the fallback (HTTP, sentence by sentence) speaks the whole answer;
    - after it started: the fallback continues from the last word boundary the alignment
      covered, without repeating what was already heard, and only after the received audio
      finishes playing;
    - without a reliable boundary (no alignment): speech stops clearly, `cortada` becomes True
      and the whole answer can be repeated on request ("repete a resposta que caiu")."""

    def __init__(
        self,
        dialogo,
        transformar: Callable[[str], str],
        voz,
        tocar: Callable[[bytes], None],
        inicio: float,
        abafar=nullcontext,
        juntar: int = 0,
    ) -> None:
        self.dialogo, self.transformar, self.voz = dialogo, transformar, voz
        self.tocar, self.inicio, self.abafar, self.juntar = tocar, inicio, abafar, juntar
        self.tempos = Tempos()
        self.frases: list[str] = []
        self.reserva: Locutor | None = None
        self.motivo_reserva = ""
        self.emocao = ""
        self.turno = None
        self._toque: threading.Thread | None = None
        # dropped midway without a reliable boundary: the answer can be repeated
        self.cortada = False
        self.reservas: list[str] = []  # reason for each switch to the fallback (diagnostics)
        try:
            # Opens (or reuses) the connection now, while the brain is still thinking.
            self.turno = dialogo.novo_turno()
        except ServicoIndisponivel as erro:
            self._para_reserva(erro)
        else:
            self._toque = threading.Thread(target=self._tocar, daemon=True, name="nora-v4-toque")
            self._toque.start()

    def falar(self, frase: str) -> None:
        if (
            self.reserva is None
            and not self.cortada
            and self.turno.erro is not None
            and not self.turno.cancelado
        ):
            self._seguir_na_reserva(self.turno.erro)
        if self.cortada:
            self.frases.append(frase)  # speaks no more; keeps it so it can be repeated
            return
        if self.reserva is not None:
            self.frases.append(frase)
            self.reserva.falar(frase)
            return
        if not self.frases:
            emocoes = emocoes_em(frase)
            self.emocao = emocoes[0].nome if emocoes else ""
        self.frases.append(frase)
        self.turno.audio.texto = " ".join(self.frases)  # estimate, if no alignment comes
        self.turno.enviar(self.transformar(frase))

    def cancelar(self) -> None:
        """Barge-in: cuts the audio and closes the connection (the next answer opens a clean
        one)."""
        if self.turno is not None:
            self.turno.cancelar()

    def terminar(self) -> None:
        if self.turno is not None and self.reserva is None and not self.cortada:
            self.turno.finalizar()
            if self._toque is not None:
                self._toque.join()
            if self.turno.erro is not None and not self.turno.cancelado:
                self._seguir_na_reserva(self.turno.erro)
        if self.reserva is not None:
            self.reserva.terminar()

    @property
    def texto(self) -> str:
        return " ".join(self.frases)

    def _seguir_na_reserva(self, erro: Exception) -> None:
        """The dialogue failed: decides between repeating everything, continuing from the boundary
        or stopping."""
        if not self.turno.recebeu_audio:
            self._para_reserva(erro, repetir=True)
            return
        restante = texto_restante(self.frases, [c for c, _, _ in self.turno._caracteres])
        if restante is None:
            self.motivo_reserva = str(erro)
            self.reservas.append(f"{erro} (sem limite confiável: fala encerrada)")
            self.dialogo.usar_reserva(erro)
            self.cortada = True
            self.tempos.erros.append(
                "A voz caiu no meio da resposta e não dá para saber até onde você ouviu. "
                'Diga "repete a resposta que caiu" para ouvir de novo.'
            )
            return
        self._para_reserva(erro, depois_do_que_tocou=True)
        if restante:
            self.reserva.falar(restante)

    def _para_reserva(
        self, erro: Exception, repetir: bool = False, depois_do_que_tocou: bool = False
    ) -> None:
        self.motivo_reserva = str(erro)
        self.reservas.append(str(erro))
        self.dialogo.usar_reserva(erro)
        tocar = self.tocar
        if depois_do_que_tocou and self._toque is not None:
            toque, tocar_agora = self._toque, self.tocar

            def tocar(som, toque=toque, tocar_agora=tocar_agora):  # noqa: F811
                toque.join()  # the v4 audio already received finishes first; nothing overlaps
                tocar_agora(som)

        self.reserva = Locutor(self.voz, tocar, self.inicio, self.abafar, juntar=self.juntar)
        self.reserva.tempos = self.tempos
        if repetir:
            for frase in self.frases:
                self.reserva.falar(frase)

    def _tocar(self) -> None:
        som = self.turno.audio
        som.primeira.wait()
        if not self.turno.recebeu_audio:
            return  # failed or was cancelled before any sound
        if not self.tempos.comeco_da_voz:
            self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
        with self.abafar(), contexto_fala("", emocao=self.emocao, texto_depois=True):
            try:
                self.tocar(som)
            except Exception as erro:  # a speaker problem does not bring down the conversation
                self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")


def abafador(config: Config):
    """What to do with the other programs while Nora speaks, per [audio] prioridade."""
    if not config.audio.prioridade:
        return nullcontext
    return lambda: abafar_outros(config.audio.volume_outros)


def responder_falando(conversa: Conversa, *args, **kwargs) -> Tempos:
    """Asks the brain for the answer, shows the text and speaks sentence by sentence while it
    writes. Meanwhile, `conversa.falando` stays on: the Second Brain and other background tasks wait
    for the voice to finish (they do not compete with it for time)."""
    conversa.falando = True
    try:
        return _responder_falando(conversa, *args, **kwargs)
    finally:
        conversa.falando = False


def _responder_falando(
    conversa: Conversa,
    voz,
    tocar: Callable[[bytes], None],
    texto: str,
    inicio: float,
    transcricao: float,
    escrever: Callable[..., None],
    medir: bool,
) -> Tempos:
    """Asks the brain for the answer, shows the text and speaks sentence by sentence while it
    writes. A voice switch request ("usa a voz do Piper") is handled here, without going to the
    brain."""
    pedido = pedido_de_voz(texto)
    if pedido:
        return trocar_de_voz(conversa, voz, tocar, texto, pedido, escrever)
    # "Repete a resposta que caiu": the last answer whose voice dropped without a reliable boundary
    # is spoken again in full, without asking the brain again.
    cortada = getattr(conversa, "fala_cortada", "")
    repetir = bool(cortada) and pede_retomada(texto)
    if repetir:
        conversa.fala_cortada = ""
    dialogo, transformar = achar_dialogo(voz)
    if dialogo is not None:  # ElevenLabs v4: real-time dialogue, one connection per conversation
        locutor = LocutorDialogo(
            dialogo, transformar, voz, tocar, inicio, abafador(conversa.config),
            juntar=conversa.config.voz.juntar_curta,
        )  # fmt: skip
    else:
        locutor = Locutor(
            voz, tocar, inicio, abafador(conversa.config), juntar=conversa.config.voz.juntar_curta
        )
    locutor.tempos.transcricao = transcricao
    separador = SeparadorDeFrases()
    escrever(f"{conversa.config.assistente.nome}: ", fim="")

    def falar(frases: list[str]) -> None:
        for frase in frases:
            if not locutor.tempos.primeira_frase:
                locutor.tempos.primeira_frase = time.perf_counter() - inicio
            locutor.falar(frase)

    tela = FiltroDeTela()  # the screen does not show the emotion tags; the voice gets everything
    try:
        for pedaco in [cortada] if repetir else conversa.perguntar(texto):
            escrever(tela.alimentar(pedaco), fim="")
            falar(separador.alimentar(pedaco))
        escrever(tela.finalizar(), fim="")
        falar(separador.finalizar())
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    except KeyboardInterrupt:
        escrever("\n(interrompido)")
        locutor.cancelar()
        audio.parar_audio()
    escrever()
    locutor.terminar()
    if getattr(locutor, "cortada", False):
        conversa.fala_cortada = locutor.texto

    tempos = locutor.tempos
    medida = _diagnosticar(conversa, voz, locutor, dialogo)
    if dialogo is not None and dialogo.aviso:
        escrever(f"[voz reserva] {dialogo.aviso}")
        dialogo.aviso = ""
    _observar_voz(conversa, voz, tempos, bool(getattr(voz, "aviso", "")))
    for erro in dict.fromkeys(tempos.erros):
        escrever(f"[erro na voz] {erro}")
    for aviso in audio.avisos_de_saida():
        escrever(f"[som] {aviso}")
    if getattr(voz, "aviso", ""):
        escrever(f"[voz reserva] {voz.aviso}")
        voz.aviso = ""
    for aviso in conversa.avisos_do_cerebro():
        escrever(f"[cérebro] {aviso}")
    for aviso in conversa.avisos_pendentes():
        escrever(f"[memória] {aviso}")
    if medir:
        escrever(
            f"  [{conversa.origem}: transcrição {tempos.transcricao:.2f} s, "
            f"primeira frase {tempos.primeira_frase:.2f} s, "
            f"começou a falar em {tempos.comeco_da_voz:.2f} s, "
            f"lembrou {len(conversa.lembrancas)} fatos, {len(conversa.trechos)} trechos "
            f"e {len(conversa.trechos_de_notas)} notas]"
        )
        if medida is not None:
            escrever(f"  [voz: {resumo_da_voz(medida)}]")
    return tempos


def _nucleo(voz):
    """The voice engine inside the layers (pronunciations, switch, fallback, emphasis)."""
    for _ in range(10):
        proxima = getattr(voz, "principal", None) or getattr(voz, "voz", None)
        if proxima is None or isinstance(voz, VozElevenLabs):
            return voz
        voz = proxima
    return voz


def _diagnosticar(conversa: Conversa, voz, locutor, dialogo):
    """Stores the voice diagnostics of this answer (ElevenLabs): effective model, continuity and
    times. No conversation text. Returns the measurement (or None, for the other voices)."""
    from nora import diagnostico_voz as diag

    config = conversa.config.voz.elevenlabs
    try:
        if dialogo is not None:
            turno = getattr(locutor, "turno", None)
            reserva = getattr(locutor, "reserva", None)
            erro = getattr(dialogo.sessao(), "ultimo_erro", "") or "diálogo indisponível"
            if turno is None or (reserva is not None and not turno.recebeu_audio):
                # Everything through the fallback (the dialogue failed before the 1st audio).
                medida = diag.medir_locutor(
                    reserva, dialogo.reserva.modelo, "http (reserva)", diag.ERRO
                )
                medida.erro = erro
            else:
                continuidade = diag.ATIVA if dialogo.continuidade else diag.DESATIVADA
                medida = diag.medir_turno(turno, dialogo.modelo, continuidade)
                if reserva is not None:  # started on v4 and ended on the fallback
                    medida.via = "dialogo + http (reserva)"
                    medida.continuidade = diag.ERRO
                    medida.erro = erro
                    medida.geracoes += reserva.geracoes
                elif getattr(locutor, "cortada", False):
                    medida.continuidade = diag.ERRO
                    medida.erro = erro
            medida.reservas = list(getattr(locutor, "reservas", []))
        else:
            nucleo = _nucleo(voz)
            if not isinstance(nucleo, VozElevenLabs):
                return None
            if not config.continuidade:
                continuidade = diag.DESATIVADA
            else:
                continuidade = diag.ATIVA if nucleo.continuidade else diag.NAO_SUPORTADA
            medida = diag.medir_locutor(locutor, nucleo.modelo, "http", continuidade)
            if getattr(voz, "aviso", ""):
                medida.reservas.append(voz.aviso)
        diag.registrar(conversa.config.pasta_dados, medida)
        return medida
    except Exception:
        return None


def resumo_da_voz(medida) -> str:
    from nora.diagnostico_voz import resumo

    return resumo(medida)


def _observar_voz(conversa: Conversa, voz, tempos: Tempos, usou_reserva: bool) -> None:
    """Ear and voice times and voice failures, for self-improvement (no text)."""
    observador = getattr(conversa, "observador", None)
    motor = getattr(voz, "motor", "") or conversa.config.voz.motor
    if observador is None:
        return
    interacao = conversa.ultima_interacao
    if tempos.transcricao:
        observador.registrar(
            "stt",
            "transcricao",
            conversa.config.ouvido.motor,
            interacao,
            int(tempos.transcricao * 1000),
        )
    if tempos.comeco_da_voz and tempos.primeira_frase:
        espera = max(0.0, tempos.comeco_da_voz - tempos.primeira_frase)
        observador.registrar("tts", "voz", motor, interacao, int(espera * 1000))
    for _ in dict.fromkeys(tempos.erros):
        observador.registrar("tts", "erro_provedor", motor, interacao, status="sem voz")
    if usou_reserva:
        observador.registrar("tts", "erro_provedor", motor, interacao, status="reserva usada")


def trocar_de_voz(conversa: Conversa, voz, tocar, texto, pedido, escrever) -> Tempos:
    resposta, wav = atender_pedido(voz, pedido, conversa.config.voz.motor)
    emitir("voz_ativa", motor=getattr(voz, "motor", "") or conversa.config.voz.motor)
    escrever(f"{conversa.config.assistente.nome}: {resposta}")
    conversa.historico.registrar("usuario", texto)
    conversa.historico.registrar("assistente", resposta, modelo="comando de voz")
    tempos = Tempos()
    try:
        with contexto_fala(resposta):
            tocar(wav if wav is not None else voz.sintetizar(resposta))
    except Exception as erro:  # a conversa segue mesmo sem voz
        tempos.erros.append(str(erro))
        escrever(f"[erro na voz] {erro}")
    return tempos


def conversar_por_voz(
    config: Config,
    entrada: Callable[[str], str] = input,
    saida: TextIO | None = None,
    medir: bool = False,
    cerebro: CerebroLocal | None = None,
    ouvido: OuvidoWhisper | None = None,
    voz: VozHTTP | VozElevenLabs | VozComReserva | None = None,
    gravar: Callable[[Callable[[str], str]], bytes] | None = None,
    tocar: Callable[[bytes], None] | None = None,
    so_teclado: bool = False,
) -> int:
    """Conversation with a spoken answer. By default, Enter records speech and typed text counts as
    a question; with `so_teclado`, no microphone is used: the person types and Nora answers by
    speaking."""
    saida = saida or sys.stdout
    conversa = nova_conversa(config, cerebro)
    ouvido = ouvido or OuvidoWhisper(config)
    voz = com_pronuncias_aprendidas(voz or VozTrocavel(config), conversa.memoria)
    microfone = audio.dispositivo(config.audio.microfone)
    gravar = gravar or (lambda entrada: audio.gravar_ate_enter(entrada, microfone))
    tocar = tocar or audio.tocador(config.audio)
    nome = config.assistente.nome

    def escrever(texto: str = "", fim: str = "\n") -> None:
        saida.write(texto + fim)
        saida.flush()

    escrever(f"Carregando {config.modelo_local.modelo} na memória...", fim="")
    try:
        escrever(f" pronto em {conversa.cerebro.aquecer():.1f} s.")
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    if so_teclado:
        escrever(f"Conversa com {nome}: digite e ela responde falando. 'sair' encerra.")
    else:
        escrever(
            f"Conversa por voz com {nome}. Aperte Enter, fale e aperte Enter de novo. "
            "Também dá para digitar. 'sair' encerra."
        )
    for aviso in conversa.avisos_pendentes():
        escrever(f"[memória] {aviso}")
    agendador = iniciar_melhorias(conversa, escrever)

    while True:
        try:
            comando = ler_entrada(
                entrada,
                "\nVocê: " if so_teclado else "\n[Enter para falar] ",
                agendador,
                lambda p: escrever(p, fim=""),
            ).strip()
        except (EOFError, KeyboardInterrupt):
            escrever()
            break
        if comando.lower() in COMANDOS_SAIR:
            break
        if comando == "/limpar":
            conversa.limpar()
            escrever("(conversa reiniciada)")
            continue
        if so_teclado and not comando:
            continue

        try:
            if comando:
                texto, inicio, transcricao = comando, time.perf_counter(), 0.0
            else:
                wav = gravar(entrada)
                inicio = time.perf_counter()
                if audio.duracao_wav(wav) < 0.3:
                    escrever("(não ouvi nada)")
                    continue
                texto = ouvido.transcrever(wav, dica=dica_do_ouvido(conversa.config))
                transcricao = time.perf_counter() - inicio
                if not texto:
                    escrever(
                        "(não ouvi fala, só som ou silêncio; tente falar mais perto do microfone)"
                    )
                    continue
                escrever(f"Você: {texto}")
        except (ServicoIndisponivel, RuntimeError) as erro:
            escrever(f"[erro] {erro}")
            continue
        except KeyboardInterrupt:
            escrever("\n(cancelado)")
            continue

        responder_falando(conversa, voz, tocar, texto, inicio, transcricao, escrever, medir)
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    if agendador is not None:
        agendador.parar()
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
