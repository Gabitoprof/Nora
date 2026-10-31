"""Toda dependência do pyproject.toml precisa estar em docs/LICENCAS.md, com a licença."""

import re
import tomllib

from nora.config import RAIZ


def _pacotes() -> set[str]:
    projeto = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    especificacoes = list(projeto.get("dependencies", []))
    for extra in projeto.get("optional-dependencies", {}).values():
        especificacoes += extra
    return {re.match(r"[A-Za-z0-9_.-]+", item).group(0).lower() for item in especificacoes}


def test_toda_dependencia_tem_licenca_documentada():
    pagina = (RAIZ / "docs" / "LICENCAS.md").read_text(encoding="utf-8").lower()
    faltando = sorted(pacote for pacote in _pacotes() if pacote not in pagina)
    assert not faltando, f"Inclua em docs/LICENCAS.md, com a licença conferida: {faltando}"
