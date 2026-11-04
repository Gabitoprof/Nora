"""Confirmações por regra ("sim, pode apagar", "não, deixa"), sem passar por nenhum cérebro:
servem para ações que pedem um "sim" antes (apagar de vez, sair do modo jogo)."""

from __future__ import annotations

import re
import unicodedata


def _sem_acento(texto: str) -> str:
    sem = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem if not unicodedata.combining(c))


def confirmacao(texto: str) -> str | None:
    """ "sim", "nao" ou None (a pessoa falou de outra coisa)."""
    limpo = " ".join(re.sub(r"[^\w\s]", " ", _sem_acento(texto)).split())
    limpo = re.sub(r"^nora\b ?", "", limpo)
    if re.search(r"\b(nao|cancela|cancelar|deixa|deixa pra la|pare|esquece)\b", limpo):
        return "nao"
    if len(limpo.split()) <= 6 and re.match(
        r"(sim|pode|confirmo|confirma|confirmado|claro|com certeza|isso|apaga|manda ver|ok|"
        r"beleza|quero)\b",
        limpo,
    ):
        return "sim"
    return None
