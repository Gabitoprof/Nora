"""Where Nora stores and looks for things, running from the repository or installed (.exe, wheel).

- **In the repository** (a checkout with `pyproject.toml`): everything stays where it always was,
  at the repository root (`config/local.toml`, `.env`, `data/`, `models/`, `hud/dist`).
- **Installed:** the program lives in a read-only folder (e.g. `C:\\Program Files\\Nora`). The
  personal config, the `.env`, the memory and the models go to the user folder: `%APPDATA%\\Nora`
  on Windows, `~/.nora` elsewhere. The default config (`nora.toml`) and the HUD build ship in the
  package.
- `NORA_HOME` (a system variable, not a `.env` one) changes the user folder in both cases.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPOSITORIO = Path(__file__).resolve().parents[2]
CONFIG_PADRAO = Path(__file__).with_name("nora.toml")

LOCAL_INICIAL = """# Sua config pessoal da Nora. Só o que você mudar em relação ao padrão.
# O padrão, com a explicação de cada opção, está no nora.toml que vem com o programa.

# [usuario]
# nome = "Seu nome"

# Instalada (nora.exe), a voz é a do ElevenLabs: as vozes locais (Kokoro, Piper) usam programas
# GPL e não vêm no instalador. Ponha a chave em ELEVENLABS_API_KEY no .env desta pasta e o id
# da voz abaixo (ElevenLabs: Voices > ... > Copy voice ID).
[voz]
motor = "elevenlabs"
reserva = ""

[voz.elevenlabs]
voz_id = ""
"""

ENV_INICIAL = """# Chaves e endereços da Nora (fora do Git e de qualquer envio). Exemplos:
# OPENAI_API_KEY=
# ANTHROPIC_API_KEY=
# ELEVENLABS_API_KEY=
# OLLAMA_HOST=http://127.0.0.1:11434
"""


def congelada() -> bool:
    """Running from inside an executable (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def no_repositorio() -> bool:
    """Running from a repository checkout (development), not installed."""
    return (
        not congelada()
        and (REPOSITORIO / "pyproject.toml").is_file()
        and (REPOSITORIO / "src" / "nora").is_dir()
    )


def pasta_do_usuario(ambiente: dict[str, str] | None = None) -> Path:
    """Where the personal config, the .env, the data and the models live."""
    ambiente = os.environ if ambiente is None else ambiente
    if ambiente.get("NORA_HOME"):
        return Path(ambiente["NORA_HOME"]).expanduser()
    if no_repositorio():
        return REPOSITORIO
    if sys.platform == "win32" and ambiente.get("APPDATA"):
        return Path(ambiente["APPDATA"]) / "Nora"
    return Path.home() / ".nora"


def preparar_pasta_do_usuario(pasta: Path) -> None:
    """The first time (installed), creates the folder with a commented personal config and .env.
    Never overwrites what already exists; in the repository, does nothing."""
    if pasta == REPOSITORIO:
        return
    (pasta / "config").mkdir(parents=True, exist_ok=True)
    for arquivo, texto in (
        (pasta / "config" / "local.toml", LOCAL_INICIAL),
        (pasta / ".env", ENV_INICIAL),
    ):
        if not arquivo.exists():
            arquivo.write_text(texto, encoding="utf-8")


def build_da_hud(ambiente: dict[str, str] | None = None) -> Path:
    """The HUD build folder (index.html and assets): NORA_HUD_DIST, the copy inside the
    executable or the repository's (`hud/dist`)."""
    ambiente = os.environ if ambiente is None else ambiente
    if ambiente.get("NORA_HUD_DIST"):
        return Path(ambiente["NORA_HUD_DIST"])
    if congelada():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "hud" / "dist"
    return REPOSITORIO / "hud" / "dist"
