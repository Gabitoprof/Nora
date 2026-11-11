"""Nora: personal voice AI assistant."""

import os
import subprocess
from pathlib import Path

# Single product version: hud/package.json follows this one (0.4.0.dev0 ↔ 0.4.0-dev.0), and
# tests/test_versao.py fails if the two diverge.
__version__ = "0.4.0.dev0"


def versao_legivel(versao: str = __version__) -> str:
    """ "0.1.0.dev0" -> "0.1.0 (em desenvolvimento)"; released versions stay as they are."""
    base, _, extra = versao.partition(".dev")
    return f"{base} (em desenvolvimento)" if extra or versao.endswith(".dev") else versao


def commit() -> str:
    """The commit in use, so acceptance records exactly what was tested: the NORA_COMMIT
    variable, the `_commit.txt` written in the executable build or the checkout's
    `git rev-parse`; otherwise, "desconhecido"."""
    if os.environ.get("NORA_COMMIT"):
        return os.environ["NORA_COMMIT"][:12]
    gravado = Path(__file__).with_name("_commit.txt")  # written in the executable build
    if gravado.is_file():
        return gravado.read_text(encoding="utf-8").strip()[:12] or "desconhecido"
    raiz = Path(__file__).resolve().parents[2]
    if not (raiz / ".git").exists():
        return "desconhecido"
    try:
        saida = subprocess.run(
            ["git", "-C", str(raiz), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "desconhecido"
    return saida.stdout.strip() or "desconhecido"
