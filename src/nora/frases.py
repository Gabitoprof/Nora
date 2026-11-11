"""Splits the model's answer into sentences as it arrives, so the voice starts early."""

from __future__ import annotations

import re

# End of sentence: . ! ? … (maybe followed by quotes or parentheses) and a space; or a line break.
_FIM = re.compile(r"(?<=[.!?…])[\"'”)\]]*\s+|\n+")
# Common abbreviations that end in a period and do not close the sentence.
_ABREVIACOES = {
    "sr.",
    "sra.",
    "dr.",
    "dra.",
    "prof.",
    "profa.",
    "av.",
    "ex.",
    "etc.",
    "obs.",
    "pág.",
    "nº.",
    "vs.",
    "aprox.",
    "tel.",
}
_MINIMO = 4


class SeparadorDeFrases:
    def __init__(self) -> None:
        self._buffer = ""

    def alimentar(self, pedaco: str) -> list[str]:
        """Takes a chunk of text and returns the sentences that are already complete."""
        self._buffer += pedaco
        frases: list[str] = []
        inicio = 0
        for corte in _FIM.finditer(self._buffer):
            candidata = self._buffer[inicio : corte.end()].strip()
            ultima_palavra = candidata.rsplit(maxsplit=1)[-1].lower() if candidata else ""
            if len(candidata) < _MINIMO or ultima_palavra in _ABREVIACOES:
                continue
            frases.append(candidata)
            inicio = corte.end()
        self._buffer = self._buffer[inicio:]
        return frases

    def finalizar(self) -> list[str]:
        """Returns what is left at the end of the answer."""
        resto, self._buffer = self._buffer.strip(), ""
        return [resto] if resto else []
