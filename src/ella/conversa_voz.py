"""Conversa por voz (parte 2 da v0.1.0): aperta Enter, fala, e a Ella responde falando.

Ouvido (whisper-server), cérebro (Ollama) e voz (Piper) são serviços separados. A resposta é
cortada em frases enquanto o modelo escreve: uma linha sintetiza a próxima frase enquanto outra
toca a atual, então a Ella começa a falar antes de terminar de pensar.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TextIO

from ella import audio
from ella.cerebro import CerebroIndisponivel, CerebroLocal
from ella.config import Config
from ella.conversa import COMANDOS_SAIR, Conversa
from ella.frases import SeparadorDeFrases
from ella.historico import Historico
from ella.ouvido import OuvidoWhisper
from ella.servico import ServicoIndisponivel
from ella.voz import VozPiper

_FIM = object()


@dataclass
class Tempos:
    """Segundos de cada etapa de uma fala, contados a partir do fim da gravação."""

    transcricao: float = 0.0
    primeira_frase: float = 0.0
    comeco_da_voz: float = 0.0
    erros: list[str] = field(default_factory=list)


class Locutor:
    """Recebe frases e as fala em ordem: uma linha sintetiza, outra toca."""

    def __init__(self, voz: VozPiper, tocar: Callable[[bytes], None], inicio: float) -> None:
        self.voz = voz
        self.tocar = tocar
        self.inicio = inicio
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
        while (frase := self._frases.get()) is not _FIM:
            if self.tempos.erros:
                continue
            try:
                self._audios.put(self.voz.sintetizar(frase))
            except ServicoIndisponivel as erro:
                self.tempos.erros.append(str(erro))
        self._audios.put(_FIM)

    def _tocar(self) -> None:
        while (wav := self._audios.get()) is not _FIM:
            if not self.tempos.comeco_da_voz:
                self.tempos.comeco_da_voz = time.perf_counter() - self.inicio
            try:
                self.tocar(wav)
            except Exception as erro:  # um problema no alto-falante não derruba a conversa
                self.tempos.erros.append(f"Falha ao tocar o áudio: {erro}")


def conversar_por_voz(
    config: Config,
    entrada: Callable[[str], str] = input,
    saida: TextIO | None = None,
    medir: bool = False,
    cerebro: CerebroLocal | None = None,
    ouvido: OuvidoWhisper | None = None,
    voz: VozPiper | None = None,
    gravar: Callable[[Callable[[str], str]], bytes] | None = None,
    tocar: Callable[[bytes], None] | None = None,
) -> int:
    saida = saida or sys.stdout
    conversa = Conversa(config, cerebro or CerebroLocal(config), Historico(config.pasta_dados))
    ouvido = ouvido or OuvidoWhisper(config)
    voz = voz or VozPiper(config)
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
    escrever(
        f"Conversa por voz com {nome}. Aperte Enter, fale e aperte Enter de novo. "
        "Também dá para digitar. 'sair' encerra."
    )

    while True:
        try:
            comando = entrada("\n[Enter para falar] ").strip()
        except (EOFError, KeyboardInterrupt):
            escrever()
            break
        if comando.lower() in COMANDOS_SAIR:
            break
        if comando == "/limpar":
            conversa.limpar()
            escrever("(conversa reiniciada)")
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

        locutor = Locutor(voz, tocar, inicio)
        locutor.tempos.transcricao = transcricao
        separador = SeparadorDeFrases()
        escrever(f"{nome}: ", fim="")
        try:
            for pedaco in conversa.perguntar(texto):
                escrever(pedaco, fim="")
                for frase in separador.alimentar(pedaco):
                    if not locutor.tempos.primeira_frase:
                        locutor.tempos.primeira_frase = time.perf_counter() - inicio
                    locutor.falar(frase)
            for frase in separador.finalizar():
                if not locutor.tempos.primeira_frase:
                    locutor.tempos.primeira_frase = time.perf_counter() - inicio
                locutor.falar(frase)
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
        if medir:
            escrever(
                f"  [transcrição {tempos.transcricao:.2f} s, "
                f"primeira frase {tempos.primeira_frase:.2f} s, "
                f"começou a falar em {tempos.comeco_da_voz:.2f} s]"
            )
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
