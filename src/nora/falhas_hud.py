"""HUD (visualization) failures, counted without stopping speech.

The HUD can never interrupt the audio: its errors are swallowed on the acoustic path. But not
silently: each (place, error type) becomes a log line the first time and, after that, is only
counted. It never records the error message, which may contain conversation text, nor audio.

Safe in the audio callback: no lock (an approximate counter is enough) and at most one log line
per error type in the whole session.
"""

from __future__ import annotations

import logging

log = logging.getLogger("nora.hud")
_contagem: dict[tuple[str, str], int] = {}


def registrar(onde: str, erro: BaseException) -> None:
    """Counts the failure; the first of each type, in each place, becomes a log line."""
    try:
        chave = (onde, type(erro).__name__)
        vezes = _contagem.get(chave, 0) + 1
        _contagem[chave] = vezes
        if vezes == 1:
            log.warning(
                "HUD: falha em %s (%s); a fala continua. As próximas iguais só são contadas.",
                *chave,
            )
    except Exception:
        pass  # not even logging may stop the audio


def contagem() -> dict[str, int]:
    """{"lugar: TipoDoErro": count}, for diagnostics and tests."""
    return {f"{onde}: {tipo}": vezes for (onde, tipo), vezes in dict(_contagem).items()}


def zerar() -> None:
    _contagem.clear()
