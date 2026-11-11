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
from nora.conversa import COMANDOS_SAIR, Conversa, nova_conversa
from nora.emocao import FiltroDeTela
from nora.frases import SeparadorDeFrases
from nora.melhorias import iniciar as iniciar_melhorias
from nora.melhorias import ler_entrada
from nora.ouvido import OuvidoWhisper
from nora.prioridade import abafar_outros
from nora.servico import ServicoIndisponivel
from nora.troca_voz import atender_pedido, pedido_de_voz
from nora.voz import (
    VozComReserva,
    VozElevenLabs,
    VozHTTP,
    VozTrocavel,
    com_pronuncias_aprendidas,
)

_FIM = object()


def _e_pergunta(frase: str) -> bool:
    return frase.rstrip(" \"'”)»").endswith("?")


# Up to how many characters of sentences already waiting go together in one voice request.
LIMITE_DO_LOTE = 400


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
    ) -> None:
        self.voz = voz
        self.tocar = tocar
        self.inicio = inicio
        self.abafar = abafar
        self.tempos = Tempos()
        self._frases: queue.Queue = queue.Queue()
        self._audios: queue.Queue = queue.Queue(maxsize=2)
        self._sintese = threading.Thread(target=self._sintetizar, daemon=True)
        self._toque = threading.Thread(target=self._tocar, daemon=True)
        self._sintese.start()
        self._toque.start()

    def falar(self, frase: str) -> None:
        self._frases.put(frase)

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
        while not acabou:
            frase = self._frases.get()
            if frase is _FIM:
                break
            lote = [frase]
            # A question always closes the request: with the "?" at the end, the voice raises the
            # intonation; in the middle of the text, many models flatten it.
            while sum(len(f) for f in lote) < LIMITE_DO_LOTE and not _e_pergunta(lote[-1]):
                try:
                    proxima = self._frases.get_nowait()
                except queue.Empty:
                    break
                if proxima is _FIM:
                    acabou = True
                    break
                lote.append(proxima)
            if self.tempos.erros:
                continue
            try:
                self._audios.put(self.voz.sintetizar(" ".join(lote)))
            except ServicoIndisponivel as erro:
                self.tempos.erros.append(str(erro))
        self._audios.put(_FIM)

    def _tocar(self) -> None:
        wav = self._audios.get()
        if wav is _FIM:
            return
        with self.abafar():  # the other programs get quieter while she speaks
            while wav is not _FIM:
                if not self.tempos.comeco_da_voz:
                    self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
                try:
                    self.tocar(wav)
                except Exception as erro:  # a speaker problem does not bring down the conversation
                    self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")
                wav = self._audios.get()


def abafador(config: Config):
    """What to do with the other programs while Nora speaks, per [audio] prioridade."""
    if not config.audio.prioridade:
        return nullcontext
    return lambda: abafar_outros(config.audio.volume_outros)


def responder_falando(
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
    locutor = Locutor(voz, tocar, inicio, abafador(conversa.config))
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
        for pedaco in conversa.perguntar(texto):
            escrever(tela.alimentar(pedaco), fim="")
            falar(separador.alimentar(pedaco))
        escrever(tela.finalizar(), fim="")
        falar(separador.finalizar())
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    except KeyboardInterrupt:
        escrever("\n(interrompido)")
        audio.parar_audio()
    escrever()
    locutor.terminar()

    tempos = locutor.tempos
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
    return tempos


def _observar_voz(conversa: Conversa, voz, tempos: Tempos, usou_reserva: bool) -> None:
    """Ear and voice times and voice failures, for self-improvement (no text)."""
    observador = getattr(conversa, "observador", None)
    if observador is None:
        return
    interacao = conversa.ultima_interacao
    motor = getattr(voz, "motor", "") or conversa.config.voz.motor
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
    escrever(f"{conversa.config.assistente.nome}: {resposta}")
    conversa.historico.registrar("usuario", texto)
    conversa.historico.registrar("assistente", resposta, modelo="comando de voz")
    tempos = Tempos()
    try:
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
                texto = ouvido.transcrever(wav)
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
