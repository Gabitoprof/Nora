"""Conversa por voz (parte 2 da v0.1.0): aperta Enter, fala, e a Nora responde falando.

Ouvido (whisper-server), cérebro (Ollama) e voz (Piper) são serviços separados. A resposta é
cortada em frases enquanto o modelo escreve: uma linha sintetiza a próxima frase enquanto outra
toca a atual, então a Nora começa a falar antes de terminar de pensar.
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
from nora.frases import SeparadorDeFrases
from nora.ouvido import OuvidoWhisper
from nora.prioridade import abafar_outros
from nora.servico import ServicoIndisponivel
from nora.voz import VozComReserva, VozElevenLabs, VozHTTP, criar_voz

_FIM = object()
# Até quantos caracteres de frases que já estão esperando vão juntos num pedido à voz.
LIMITE_DO_LOTE = 400


@dataclass
class Tempos:
    """Segundos de cada etapa de uma fala, contados a partir do fim da gravação."""

    transcricao: float = 0.0
    primeira_frase: float = 0.0
    comeco_da_voz: float = 0.0
    erros: list[str] = field(default_factory=list)


class Locutor:
    """Recebe frases e as fala em ordem: uma linha sintetiza, outra toca."""

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
        """Espera tudo o que foi pedido ser falado."""
        self._frases.put(_FIM)
        self._sintese.join()
        self._toque.join()

    def _sintetizar(self) -> None:
        """Sintetiza as frases em ordem. Se várias já estão esperando (a voz é mais lenta que
        o modelo, como no ComfyUI), junta-as num pedido só: menos pedidos, menos pausas."""
        acabou = False
        while not acabou:
            frase = self._frases.get()
            if frase is _FIM:
                break
            lote = [frase]
            while sum(len(f) for f in lote) < LIMITE_DO_LOTE:
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
        with self.abafar():  # os outros programas ficam mais baixos enquanto ela fala
            while wav is not _FIM:
                if not self.tempos.comeco_da_voz:
                    self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
                try:
                    self.tocar(wav)
                except Exception as erro:  # um problema no alto-falante não derruba a conversa
                    self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")
                wav = self._audios.get()


def abafador(config: Config):
    """O que fazer com os outros programas enquanto a Nora fala, conforme [audio] prioridade."""
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
    """Pede a resposta ao cérebro, mostra o texto e fala frase por frase enquanto ele escreve."""
    locutor = Locutor(voz, tocar, inicio, abafador(conversa.config))
    locutor.tempos.transcricao = transcricao
    separador = SeparadorDeFrases()
    escrever(f"{conversa.config.assistente.nome}: ", fim="")

    def falar(frases: list[str]) -> None:
        for frase in frases:
            if not locutor.tempos.primeira_frase:
                locutor.tempos.primeira_frase = time.perf_counter() - inicio
            locutor.falar(frase)

    try:
        for pedaco in conversa.perguntar(texto):
            escrever(pedaco, fim="")
            falar(separador.alimentar(pedaco))
        falar(separador.finalizar())
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    except KeyboardInterrupt:
        escrever("\n(interrompido)")
        audio.parar_audio()
    escrever()
    locutor.terminar()

    tempos = locutor.tempos
    for erro in dict.fromkeys(tempos.erros):
        escrever(f"[erro na voz] {erro}")
    for aviso in audio.avisos_de_saida():
        escrever(f"[som] {aviso}")
    if getattr(voz, "aviso", ""):
        escrever(f"[voz reserva] {voz.aviso}")
        voz.aviso = ""
    for aviso in conversa.avisos_pendentes():
        escrever(f"[memória] {aviso}")
    if medir:
        escrever(
            f"  [transcrição {tempos.transcricao:.2f} s, "
            f"primeira frase {tempos.primeira_frase:.2f} s, "
            f"começou a falar em {tempos.comeco_da_voz:.2f} s, "
            f"lembrou {len(conversa.lembrancas)} fatos e {len(conversa.trechos)} trechos]"
        )
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
    """Conversa com resposta falada. Por padrão, Enter grava a fala e texto digitado vale como
    pergunta; com `so_teclado`, não usa microfone: a pessoa digita e a Nora responde falando."""
    saida = saida or sys.stdout
    conversa = nova_conversa(config, cerebro)
    ouvido = ouvido or OuvidoWhisper(config)
    voz = voz or criar_voz(config)
    microfone = audio.dispositivo(config.audio.microfone)
    alto_falante = audio.dispositivo(config.audio.alto_falante)
    gravar = gravar or (lambda entrada: audio.gravar_ate_enter(entrada, microfone))
    tocar = tocar or (lambda wav: audio.tocar_wav(wav, alto_falante))
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

    while True:
        try:
            comando = entrada("\nVocê: " if so_teclado else "\n[Enter para falar] ").strip()
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
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
