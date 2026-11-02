"""Prioridade da voz: enquanto a Nora fala, abaixa o volume dos outros programas e depois
devolve (Windows, pela biblioteca pycaw). Fora do Windows, ou sem a pycaw, não faz nada."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager


def _sessoes_de_audio():
    """As sessões de áudio dos outros programas, como (nome, controle de volume)."""
    from pycaw.pycaw import AudioUtilities

    for sessao in AudioUtilities.GetAllSessions():
        processo = sessao.Process
        if processo is None or processo.pid == os.getpid():
            continue
        yield processo.name(), sessao.SimpleAudioVolume


@contextmanager
def abafar_outros(volume: float, sessoes=None):
    """Durante o bloco, os outros programas tocam a `volume` (0 a 1) do volume que tinham."""
    if sessoes is None:
        if sys.platform != "win32":
            yield
            return
        try:
            import comtypes

            comtypes.CoInitialize()  # cada linha de execução precisa iniciar o COM
            sessoes = list(_sessoes_de_audio())
        except Exception:  # sem pycaw ou sem acesso ao áudio: só não abafa
            yield
            return
    originais = []
    for _, controle in sessoes:
        try:
            atual = controle.GetMasterVolume()
            controle.SetMasterVolume(atual * volume, None)
            originais.append((controle, atual))
        except Exception:
            continue
    try:
        yield
    finally:
        for controle, atual in originais:
            try:
                controle.SetMasterVolume(atual, None)
            except Exception:
                continue
