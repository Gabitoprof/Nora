"""Hands-free conversation (part 3 of v0.1.0): Nora keeps listening and answers when the speech
starts with her name. After answering, you can keep going for a few seconds without saying the
name. While she speaks, what the microphone picks up is discarded (there is no echo cancellation
yet, so she would hear her own voice)."""

from __future__ import annotations

import queue
import sys
import threading
import time
from collections.abc import Callable, Iterable
from typing import TextIO

from nora import audio
from nora.ativacao import e_despedida, extrair_pedido
from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import RAIZ, Config
from nora.conversa import COMANDOS_SAIR, nova_conversa
from nora.conversa_voz import responder_falando
from nora.melhorias import iniciar as iniciar_melhorias
from nora.ouvido import OuvidoWhisper
from nora.servico import ServicoIndisponivel
from nora.vad import DetectorDeFala, SileroVAD, baixar_modelo, em_quadros, falas
from nora.voz import VozTrocavel, com_pronuncias_aprendidas

MODELO_VAD = "models/silero_vad.onnx"


def preparar_falas(config: Config, microfone: audio.Microfone):
    """Connects the microphone to the VAD and returns (utterance generator, function to restart
    listening, function to pause listening while Nora speaks)."""
    vad = SileroVAD(baixar_modelo(RAIZ / MODELO_VAD))
    detector = DetectorDeFala(limiar=config.escuta.limiar, silencio_ms=config.escuta.silencio_ms)

    def recomecar() -> None:
        microfone.limpar()
        microfone.retomar()
        vad.reiniciar()
        detector.reiniciar()

    return falas(em_quadros(microfone.blocos()), vad, detector), recomecar, microfone.pausar


def _ler_teclado(entrada: Callable[[str], str], destino: queue.Queue) -> None:
    """Reads typed lines and hands them to the main loop (runs on a separate thread)."""
    try:
        while True:
            linha = entrada("").strip()
            if linha:
                destino.put(linha)
    except (EOFError, KeyboardInterrupt, StopIteration, RuntimeError, OSError):
        destino.put(None)


def conversar_maos_livres(
    config: Config,
    saida: TextIO | None = None,
    medir: bool = False,
    mostrar_ignoradas: bool = False,
    gravar_falas: bool = False,
    cerebro: CerebroLocal | None = None,
    ouvido: OuvidoWhisper | None = None,
    voz=None,
    tocar: Callable[[bytes], None] | None = None,
    fontes: tuple[Iterable[bytes], Callable[[], None], Callable[[], None]] | None = None,
    relogio: Callable[[], float] = time.monotonic,
    teclado: bool = True,
    entrada: Callable[[str], str] = input,
) -> int:
    saida = saida or sys.stdout
    conversa = nova_conversa(config, cerebro)
    ouvido = ouvido or OuvidoWhisper(config)
    voz = com_pronuncias_aprendidas(voz or VozTrocavel(config), conversa.memoria)
    tocar = tocar or audio.tocador(config.audio)
    nome = config.assistente.nome
    palavra = config.assistente.palavra_de_ativacao
    # A full sentence: with only "Nora, ", Whisper sometimes assumes the name was already said
    # and does not write it again.
    dica = f"Conversa com a assistente {nome}."

    def escrever(texto: str = "", fim: str = "\n") -> None:
        saida.write(texto + fim)
        saida.flush()

    def dizer(frase: str) -> None:
        escrever(f"{nome}: {frase}")
        try:
            tocar(voz.sintetizar(frase))
        except Exception as erro:  # the conversation goes on even without voice
            escrever(f"[erro na voz] {erro}")

    escrever(f"Carregando {config.modelo_local.modelo} na memória...", fim="")
    try:
        escrever(f" pronto em {conversa.cerebro.aquecer():.1f} s.")
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")

    microfone = None
    agendador = None
    try:
        if fontes is None:
            microfone = audio.Microfone(audio.dispositivo(config.audio.microfone)).__enter__()
            fontes = preparar_falas(config, microfone)
        falas_detectadas, recomecar, pausar = fontes
        escrever(
            f'Ouvindo. Comece a frase com "{palavra}" (ex.: "{palavra}, que horas são?"). '
            "Ctrl+C encerra."
        )
        if gravar_falas:
            escrever(f"(gravando cada fala ouvida em {config.pasta_dados / 'falas'})")

        if teclado:
            escrever("Também dá para digitar: escreva e aperte Enter ('sair' encerra).")
        for aviso in conversa.avisos_pendentes():
            escrever(f"[memória] {aviso}")
        agendador = iniciar_melhorias(conversa, escrever)
        digitados: queue.Queue[str | None] = queue.Queue()
        if teclado:
            threading.Thread(target=_ler_teclado, args=(entrada, digitados), daemon=True).start()

        janela_ate = 0.0
        pasta_falas = config.pasta_dados / "falas"

        def atender(texto: str, pedido: str, inicio: float, transcricao: float) -> None:
            nonlocal janela_ate
            if config.escuta.pausar_microfone:
                pausar()  # so she does not hear herself through the speaker
            if e_despedida(pedido):
                dizer("Até mais!")
                janela_ate = 0.0
            elif not pedido:
                dizer("Oi, pode falar.")
                janela_ate = relogio() + config.escuta.janela_s
            else:
                responder_falando(
                    conversa, voz, tocar, pedido, inicio, transcricao, escrever, medir
                )
                janela_ate = relogio() + config.escuta.janela_s
            recomecar()

        numero = 0
        sair = False
        for fala in falas_detectadas:
            if agendador is not None:
                agendador.apresentar_pendentes()
            # What was typed: does not need her name.
            while not digitados.empty():
                linha = digitados.get_nowait()
                if linha is None:
                    continue
                if linha.lower() in COMANDOS_SAIR:
                    sair = True
                    break
                pedido = extrair_pedido(linha, palavra)
                escrever(f"Você (digitado): {linha}")
                atender(linha, linha if pedido is None else pedido, time.perf_counter(), 0.0)
            if sair:
                break
            if fala is None:
                continue

            numero += 1
            inicio = time.perf_counter()
            if gravar_falas:
                pasta_falas.mkdir(parents=True, exist_ok=True)
                arquivo = pasta_falas / f"{time.strftime('%Y-%m-%d_%H-%M-%S')}_{numero:03}.wav"
                arquivo.write_bytes(audio.para_wav(fala))
            try:
                texto = ouvido.transcrever(audio.para_wav(fala), dica=dica)
            except ServicoIndisponivel as erro:
                escrever(f"[erro] {erro}")
                continue
            transcricao = time.perf_counter() - inicio
            if not texto:
                continue

            pedido = extrair_pedido(texto, palavra)
            if pedido is None and relogio() < janela_ate:
                pedido = texto  # continuing the conversation, without needing the name
            if pedido is None:
                if mostrar_ignoradas:
                    escrever(f"  (ignorado: {texto})")
                continue

            escrever(f"Você: {texto}")
            atender(texto, pedido, inicio, transcricao)
    except KeyboardInterrupt:
        escrever()
    except RuntimeError as erro:
        escrever(f"[erro] {erro}")
        return 1
    finally:
        if agendador is not None:
            agendador.parar()
        if microfone is not None:
            microfone.__exit__(None, None, None)
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
