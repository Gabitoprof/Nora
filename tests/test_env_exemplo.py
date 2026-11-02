"""O .env.example acompanha o .env: toda variável que o código lê está nele, sem valor pessoal."""

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SENSIVEIS = re.compile(r"(KEY|TOKEN|SECRET|SENHA|PASSWORD)")


def _exemplo() -> dict[str, str]:
    variaveis = {}
    for linha in (RAIZ / ".env.example").read_text("utf-8").splitlines():
        linha = linha.strip().lstrip("#").strip()
        if re.fullmatch(r"[A-Z][A-Z0-9_]*=.*", linha):
            nome, valor = linha.split("=", 1)
            variaveis[nome] = valor.strip()
    return variaveis


def test_toda_variavel_lida_pelo_codigo_esta_no_env_example():
    codigo = "\n".join(p.read_text("utf-8") for p in (RAIZ / "src").rglob("*.py"))
    lidas = set(re.findall(r"(?:ambiente|environ)\.get\(\s*\"([A-Z][A-Z0-9_]*)\"", codigo))
    lidas |= set(re.findall(r"environ\[\s*\"([A-Z][A-Z0-9_]*)\"", codigo))
    faltando = sorted(lidas - set(_exemplo()))
    assert not faltando, f"Acrescente ao .env.example (sem valor pessoal): {faltando}"


def test_env_example_nao_tem_chave_preenchida():
    preenchidas = [n for n, v in _exemplo().items() if SENSIVEIS.search(n) and v]
    assert not preenchidas, f"Chaves com valor no .env.example: {preenchidas}"


def test_env_fica_fora_do_git():
    ignorados = (RAIZ / ".gitignore").read_text("utf-8").splitlines()
    assert any(linha.strip() in (".env", "/.env") for linha in ignorados)
