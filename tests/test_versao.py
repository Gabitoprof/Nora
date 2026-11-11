"""A single version for the product: Python (nora.__version__) and the HUD (hud/package.json)."""

import json
import re
from pathlib import Path

from nora import __version__, commit

RAIZ = Path(__file__).resolve().parents[1]


def para_npm(versao: str) -> str:
    """PEP 440 → npm semver: "0.4.0.dev0" → "0.4.0-dev.0"; "0.4.0" stays the same."""
    base, _, dev = versao.partition(".dev")
    return f"{base}-dev.{dev or 0}" if ".dev" in versao else versao


def test_python_e_hud_tem_a_mesma_versao():
    pacote = json.loads((RAIZ / "hud" / "package.json").read_text(encoding="utf-8"))
    assert pacote["version"] == para_npm(__version__)
    assert __version__ == "0.4.0.dev0"


def test_hud_privada_e_sem_licenca_aberta():
    pacote = json.loads((RAIZ / "hud" / "package.json").read_text(encoding="utf-8"))
    assert pacote["private"] is True and pacote["license"] == "UNLICENSED"


def test_commit_do_checkout_ou_da_variavel(monkeypatch):
    assert re.fullmatch(r"[0-9a-f]{7,12}|desconhecido", commit())
    monkeypatch.setenv("NORA_COMMIT", "abcdef1234567890")
    assert commit() == "abcdef123456"


def test_verificar_mostra_versao_e_commit(criar_raiz):
    from nora.cli import verificar
    from nora.config import carregar

    linhas = verificar(carregar(criar_raiz(), ambiente={}))
    assert linhas[0].startswith(f"Versão: {__version__} (commit ")
