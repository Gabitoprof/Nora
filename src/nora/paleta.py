"""Cores das emoções da Nora: uma fonte só, `src/nora/paleta.json`, dentro do pacote (vai junto
no wheel), lida pela HUD (TypeScript, importa o mesmo arquivo) e por qualquer parte em Python (ex.:
o mapa do Second Brain). Não copie as cores para outro lugar.

`cores` tem os grupos (neutra, alegria, carinho, calma, seriedade, tristeza, curiosidade);
`aliases` liga cada nome de emoção da Nora (as etiquetas de emocao.py e os nomes antigos da
HUD) a um grupo; `dinamica` é a intensidade do movimento de cada grupo na HUD.
"""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path

ARQUIVO = Path(__file__).with_name("paleta.json")


@lru_cache(maxsize=1)
def paleta() -> dict:
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def _chave(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome.strip().lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def grupo(emocao: str) -> str:
    """O grupo de cor de uma emoção ("curiosa" → "curiosidade"); desconhecida → "neutra"."""
    aliases = paleta()["aliases"]
    return aliases.get(emocao.strip().lower()) or aliases.get(_chave(emocao)) or "neutra"


def cor(emocao: str) -> str:
    """A cor (#RRGGBB) de uma emoção, igual à da HUD."""
    return paleta()["cores"][grupo(emocao)]


def cores_por_emocao() -> dict[str, str]:
    """Todos os nomes conhecidos → cor (a mesma tabela `cores` de hud/src/state.ts)."""
    return {nome: paleta()["cores"][g] for nome, g in paleta()["aliases"].items()}
