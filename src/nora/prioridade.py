"""Voice priority: while Nora speaks, lowers the volume of other programs and then restores it
(Windows, through the pycaw library). Outside Windows, or without pycaw, it does nothing."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager


def _sessoes_de_audio():
    """The other programs' audio sessions, as (name, volume control)."""
    from pycaw.pycaw import AudioUtilities

    for sessao in AudioUtilities.GetAllSessions():
        processo = sessao.Process
        if processo is None or processo.pid == os.getpid():
            continue
        yield processo.name(), sessao.SimpleAudioVolume


@contextmanager
def abafar_outros(volume: float, sessoes=None):
    """During the block, the other programs play at `volume` (0 to 1) of the volume they had."""
    if sessoes is None:
        if sys.platform != "win32":
            yield
            return
        try:
            import comtypes

            comtypes.CoInitialize()  # each thread needs to initialize COM
            sessoes = list(_sessoes_de_audio())
        except Exception:  # no pycaw or no access to audio: just do not duck
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
