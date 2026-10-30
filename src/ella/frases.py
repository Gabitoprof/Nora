"""Corta a resposta do modelo em frases, conforme ela chega, para a voz começar cedo."""

from __future__ import annotations

import re

# Fim de frase: . ! ? … (talvez seguido de aspas ou parênteses) e espaço; ou quebra de linha.
_FIM = re.compile(r"(?<=[.!?…])[\"'”)\]]*\s+|\n+")
# Abreviações comuns que terminam em ponto e não fecham a frase.
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
        """Recebe um pedaço do texto e devolve as frases que já ficaram completas."""
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
        """Devolve o que sobrou no fim da resposta."""
        resto, self._buffer = self._buffer.strip(), ""
        return [resto] if resto else []
