"""Instalação limpa: gera o wheel, instala num venv novo fora do checkout e confere que o pacote
funciona sozinho (sem o repositório ao lado).

    python scripts/testar_instalacao_limpa.py

Roda no CI (job `instalacao`, só Linux). Sai com código 1 e explica o que faltou se algo falhar.

Também roda `nora --verificar` instalada, com a pasta do usuário num lugar temporário
(`NORA_HOME`): a config padrão vem de dentro do pacote e a pasta pessoal é criada na hora.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
IGNORAR = (".git", "build", "dist", "*.egg-info", "node_modules", "data", ".venv", "__pycache__")

# Roda dentro do venv novo, com `python -I` (sem PYTHONPATH nem a pasta atual) e fora do checkout.
CONFERIR = r"""
import importlib.resources as recursos, json, sys
from pathlib import Path

raiz = Path(sys.argv[1]).resolve()
import nora
pacote = Path(nora.__file__).resolve().parent
assert raiz not in pacote.parents, f"nora veio do checkout ({pacote}), não do wheel"

import nora.paleta
cores = nora.paleta.cores_por_emocao()
assert cores["calma"] == "#66D4CB" and len(cores) > 10, cores

import nora.segundo_cerebro
assert nora.segundo_cerebro.CORES_DAS_EMOCOES["curiosa"] == "#DF876A"

arquivos = [
    "paleta.json", "hud_contrato.json", "segundo_cerebro_contrato.json", "mapa_memoria.html"
]
faltando = [n for n in arquivos if not recursos.files("nora").joinpath(n).is_file()]
assert not faltando, f"fora do pacote instalado: {faltando}"
json.loads(recursos.files("nora").joinpath("segundo_cerebro_contrato.json").read_text("utf-8"))

from nora.mapa_memoria import pagina
assert "obsidian://open" in pagina('{"nos": [], "ligacoes": []}')

print(f"ok: nora {nora.__version__} instalada em {pacote}")
"""


def rodar(*comando: str | Path, **opcoes) -> subprocess.CompletedProcess:
    resultado = subprocess.run([str(c) for c in comando], capture_output=True, text=True, **opcoes)
    if resultado.returncode != 0:
        print(resultado.stdout[-3000:], resultado.stderr[-3000:], sep="\n", file=sys.stderr)
        raise SystemExit(f"falhou: {' '.join(str(c) for c in comando)}")
    return resultado


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nora-instalacao-") as pasta:
        pasta = Path(pasta)
        dist = pasta / "dist"
        # Uma cópia limpa: o `build/` do checkout pode ter módulos velhos que iriam para o wheel.
        fonte = pasta / "fonte"
        shutil.copytree(RAIZ, fonte, ignore=shutil.ignore_patterns(*IGNORAR))
        rodar(sys.executable, "-m", "pip", "wheel", str(fonte), "--no-deps", "-w", dist)
        rodas = list(dist.glob("nora-*.whl"))
        assert len(rodas) == 1, rodas
        print(f"wheel: {rodas[0].name}")
        venv.create(pasta / "venv", with_pip=True)
        python = (
            pasta / "venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        rodar(python, "-m", "pip", "install", "--no-index", "--no-deps", rodas[0])
        saida = rodar(python, "-I", "-c", CONFERIR, RAIZ, cwd=pasta)
        print(saida.stdout.strip())
        # `nora --verificar` instalada: lê o padrão do pacote e cria a pasta do usuário.
        casa = pasta / "casa"
        ambiente = {**os.environ, "NORA_HOME": str(casa)}
        ambiente.pop("PYTHONPATH", None)
        verificar = rodar(python, "-I", "-m", "nora", "--verificar", cwd=pasta, env=ambiente)
        primeira = next(
            linha for linha in verificar.stdout.splitlines() if linha.startswith("Versão")
        )
        assert (casa / "config" / "local.toml").is_file() and (casa / ".env").is_file()
        assert "site-packages" in verificar.stdout and "nora.toml" in verificar.stdout
        print(f"ok: nora --verificar instalada ({primeira}); pasta do usuário criada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
