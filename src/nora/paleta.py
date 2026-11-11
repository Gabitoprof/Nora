"""Colors of Nora's emotions: a single source, `src/nora/paleta.json`, inside the package (it ships
in the wheel), read by the HUD (TypeScript, imports the same file) and by any Python part (e.g.
the Second Brain map). Do not copy the colors anywhere else.

`cores` has the groups (neutra, alegria, carinho, calma, seriedade, tristeza, curiosidade);
`aliases` maps each of Nora's emotion names (the emocao.py tags and the HUD's old names) to a
group; `dinamica` is the movement intensity of each group in the HUD.
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
    """The color group of an emotion ("curiosa" → "curiosidade"); unknown → "neutra"."""
    aliases = paleta()["aliases"]
    return aliases.get(emocao.strip().lower()) or aliases.get(_chave(emocao)) or "neutra"


def cor(emocao: str) -> str:
    """The color (#RRGGBB) of an emotion, the same as the HUD's."""
    return paleta()["cores"][grupo(emocao)]


def cores_por_emocao() -> dict[str, str]:
    """All known names → color (the same `cores` table as hud/src/state.ts)."""
    return {nome: paleta()["cores"][g] for nome, g in paleta()["aliases"].items()}
