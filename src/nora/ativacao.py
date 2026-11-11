"""Wake word by transcription: speech only becomes a request if it starts with her name.

Whisper may write the name in similar ways; so the comparison ignores accents, capitals,
doubled letters and a trailing "h" ("Nora" = "NORA" = "Norah" = "Nóra").
"""

from __future__ import annotations

import re
import unicodedata

_PALAVRA = re.compile(r"\w+", re.UNICODE)
SAUDACOES = {"oi", "ei", "ola", "hey", "ok", "alo", "e", "ai"}
DESPEDIDAS = {
    "tchau",
    "ate mais",
    "ate logo",
    "pode parar",
    "so isso",
    "e so isso",
    "obrigado e so isso",
    "obrigada e so isso",
    "valeu",
}


def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(_PALAVRA.findall(sem_acento))


def _encolher(palavra: str) -> str:
    """Comparable form: no doubled letters and no trailing "h" ('norah' -> 'nora')."""
    return re.sub(r"(.)\1+", r"\1", palavra).removesuffix("h") or palavra


def extrair_pedido(texto: str, palavra_de_ativacao: str) -> str | None:
    """If the speech starts with the wake word (maybe after 'oi', 'ei'...), returns the rest of
    the speech ("" if only the name was called). Otherwise, returns None."""
    alvo = [_encolher(p) for p in normalizar(palavra_de_ativacao).split()]
    tokens = list(_PALAVRA.finditer(texto))
    if not alvo or not tokens:
        return None
    formas = [_encolher(normalizar(t.group())) for t in tokens]
    inicio = 0
    while (
        inicio < min(2, len(formas)) and formas[inicio] in SAUDACOES and formas[inicio] != alvo[0]
    ):
        inicio += 1
    fim = inicio + len(alvo)
    if formas[inicio:fim] != alvo:
        return None
    resto = texto[tokens[fim - 1].end() :]
    return resto.lstrip(" ,.;:!?-–—").strip()


def e_despedida(texto: str) -> bool:
    return normalizar(texto) in DESPEDIDAS
