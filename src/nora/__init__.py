"""Nora: assistente de IA pessoal por voz."""

import os
import subprocess
from pathlib import Path

# Versão única do produto: o hud/package.json segue esta (0.4.0.dev0 ↔ 0.4.0-dev.0), e o
# tests/test_versao.py falha se as duas divergirem.
__version__ = "0.4.0.dev0"


def versao_legivel(versao: str = __version__) -> str:
    """ "0.1.0.dev0" -> "0.1.0 (em desenvolvimento)"; versões lançadas ficam como estão."""
    base, _, extra = versao.partition(".dev")
    return f"{base} (em desenvolvimento)" if extra or versao.endswith(".dev") else versao


def commit() -> str:
    """O commit em uso, para a homologação registrar exatamente o que foi testado: a variável
    NORA_COMMIT (instalação empacotada) ou o `git rev-parse` do checkout; senão, "desconhecido"."""
    if os.environ.get("NORA_COMMIT"):
        return os.environ["NORA_COMMIT"][:12]
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
