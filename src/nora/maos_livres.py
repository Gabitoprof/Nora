"""Conversa mãos livres (parte 3 da v0.1.0): a Nora fica ouvindo e responde quando a fala
começa com o nome dela. Depois de responder, dá para continuar por alguns segundos sem dizer
o nome. Enquanto ela fala, o que o microfone capta é descartado (ainda não há cancelamento de
eco, então ela ouviria a própria voz)."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Iterable
from typing import TextIO

from nora import audio
from nora.ativacao import e_despedida, extrair_pedido
from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import RAIZ, Config
from nora.conversa import nova_conversa
from nora.conversa_voz import responder_falando
from nora.ouvido import OuvidoWhisper
from nora.servico import ServicoIndisponivel
from nora.vad import DetectorDeFala, SileroVAD, baixar_modelo, em_quadros, falas
from nora.voz import criar_voz

MODELO_VAD = "models/silero_vad.onnx"


def preparar_falas(config: Config, microfone: audio.Microfone):
    """Liga o microfone ao VAD e devolve (gerador de falas, função para recomeçar a escuta,
    função para pausar a escuta enquanto a Nora fala)."""
    vad = SileroVAD(baixar_modelo(RAIZ / MODELO_VAD))
    detector = DetectorDeFala(limiar=config.escuta.limiar, silencio_ms=config.escuta.silencio_ms)

    def recomecar() -> None:
        microfone.limpar()
        microfone.retomar()
        vad.reiniciar()
        detector.reiniciar()

    return falas(em_quadros(microfone.blocos()), vad, detector), recomecar, microfone.pausar


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
) -> int:
    saida = saida or sys.stdout
    conversa = nova_conversa(config, cerebro)
    ouvido = ouvido or OuvidoWhisper(config)
    voz = voz or criar_voz(config)
    alto_falante = audio.dispositivo(config.audio.alto_falante)
    tocar = tocar or (lambda wav: audio.tocar_wav(wav, alto_falante))
    nome = config.assistente.nome
    palavra = config.assistente.palavra_de_ativacao
    # Uma frase completa: com só "Nora, ", o Whisper às vezes entende que o nome já foi dito
    # e não o escreve de novo.
    dica = f"Conversa com a assistente {nome}."

    def escrever(texto: str = "", fim: str = "\n") -> None:
        saida.write(texto + fim)
        saida.flush()

    def dizer(frase: str) -> None:
        escrever(f"{nome}: {frase}")
        try:
            tocar(voz.sintetizar(frase))
        except Exception as erro:  # a conversa segue mesmo sem voz
            escrever(f"[erro na voz] {erro}")

    escrever(f"Carregando {config.modelo_local.modelo} na memória...", fim="")
    try:
        escrever(f" pronto em {conversa.cerebro.aquecer():.1f} s.")
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")

    microfone = None
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

        janela_ate = 0.0
        pasta_falas = config.pasta_dados / "falas"
        for numero, fala in enumerate(falas_detectadas, start=1):
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
                pedido = texto  # continuação da conversa, sem precisar do nome
            if pedido is None:
                if mostrar_ignoradas:
                    escrever(f"  (ignorado: {texto})")
                continue

            escrever(f"Você: {texto}")
            if config.escuta.pausar_microfone:
                pausar()  # para não se ouvir pela caixa de som
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
    except KeyboardInterrupt:
        escrever()
    except RuntimeError as erro:
        escrever(f"[erro] {erro}")
        return 1
    finally:
        if microfone is not None:
            microfone.__exit__(None, None, None)
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
