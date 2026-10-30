"""Palavra de ativação por transcrição: a fala só vira pedido se começar com o nome dela.

O nome "Ella" se pronuncia "Élha", e o Whisper escreve de vários jeitos; por isso a comparação
ignora acentos, maiúsculas, letras dobradas e o "h" do "lh" ("Ella" = "Elha" = "Ela").
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
    """Forma comparável: tira letras dobradas e trata 'lh' como 'l', porque o Whisper escreve o
    nome "Élha" como 'Ella', 'Elha' ou 'Ela'."""
    return re.sub(r"(.)\1+", r"\1", palavra.replace("lh", "l"))


def extrair_pedido(texto: str, palavra_de_ativacao: str) -> str | None:
    """Se a fala começa com a palavra de ativação (talvez depois de 'oi', 'ei'...), devolve o
    resto da fala ("" se só chamou o nome). Senão, devolve None."""
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
