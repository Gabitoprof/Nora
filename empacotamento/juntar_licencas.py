"""Copia os avisos de licença de cada pacote Python que vai dentro do nora.exe para
`<destino>/licencas/<pacote>/`, mais a do próprio Python. As licenças MIT/BSD/Apache dos pacotes
pedem que o aviso acompanhe a distribuição.

    python empacotamento/juntar_licencas.py dist/nora
"""

from __future__ import annotations

import re
import shutil
import sys
from importlib import metadata
from pathlib import Path

NOMES = ("LICENSE", "LICENCE", "COPYING", "NOTICE", "AUTHORS")
EXTRAS = ("voz", "memoria", "nuvem")  # os que vão dentro do nora.exe (kokoro e dev ficam de fora)


def _nome(texto: str) -> str:
    return re.sub(r"[-_.]+", "-", texto).lower()


def dependencias(raiz: str = "nora", extras=EXTRAS) -> set[str]:
    """Os pacotes que a Nora (com os extras do executável) puxa, recursivamente."""
    vistos: set[str] = set()
    pendentes = [(raiz, set(extras))]
    while pendentes:
        nome, extras_pedidos = pendentes.pop()
        try:
            requisitos = metadata.requires(nome) or []
        except metadata.PackageNotFoundError:
            continue
        for requisito in requisitos:
            pacote, _, condicao = requisito.partition(";")
            alvo = _nome(re.match(r"[A-Za-z0-9_.-]+", pacote.strip()).group(0))
            extra = re.search(r"extra\s*==\s*['\"]([^'\"]+)", condicao)
            if extra and extra.group(1) not in extras_pedidos:
                continue
            if "sys_platform" in condicao and "win32" in condicao and sys.platform != "win32":
                continue
            if alvo not in vistos:
                vistos.add(alvo)
                pendentes.append((alvo, set()))
    return vistos


def juntar(destino: Path) -> list[str]:
    pasta = destino / "licencas"
    pasta.mkdir(parents=True, exist_ok=True)
    copiados = []
    incluir = dependencias()
    for distribuicao in metadata.distributions():
        nome = distribuicao.metadata["Name"]
        if not nome or _nome(nome) not in incluir:
            continue
        arquivos = [
            arquivo
            for arquivo in distribuicao.files or []
            if Path(arquivo).name.upper().startswith(NOMES)
        ]
        if not arquivos:
            continue
        alvo = pasta / nome
        alvo.mkdir(exist_ok=True)
        for arquivo in arquivos:
            origem = Path(distribuicao.locate_file(arquivo))
            if origem.is_file():
                shutil.copyfile(origem, alvo / origem.name)
        licenca = distribuicao.metadata.get("License-Expression") or distribuicao.metadata.get(
            "License", ""
        )
        copiados.append(
            f"{nome} {distribuicao.version}: {licenca.splitlines()[0] if licenca else '?'}"
        )
    python = Path(sys.base_prefix) / "LICENSE.txt"
    if python.is_file():
        shutil.copyfile(python, pasta / "Python-LICENSE.txt")
        copiados.append(f"Python {sys.version.split()[0]}: PSF-2.0")
    (pasta / "LEIA-ME.txt").write_text(
        "Avisos de licença dos componentes de terceiros que vêm dentro da Nora.\n"
        "O código da Nora em si é de todos os direitos reservados (veja LICENSE).\n\n"
        + "\n".join(sorted(copiados))
        + "\n",
        encoding="utf-8",
    )
    return copiados


if __name__ == "__main__":
    print(f"{len(juntar(Path(sys.argv[1])))} componentes com aviso de licença copiado")
