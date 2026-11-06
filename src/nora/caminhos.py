"""Onde a Nora guarda e procura cada coisa, rodando do repositório ou instalada (.exe, wheel).

- **No repositório** (checkout com `pyproject.toml`): tudo fica onde sempre ficou, na raiz do
  repositório (`config/local.toml`, `.env`, `data/`, `models/`, `hud/dist`).
- **Instalada:** o programa fica numa pasta só de leitura (ex.: `C:\\Program Files\\Nora`). A config
  pessoal, o `.env`, a memória e os modelos vão para a pasta do usuário: `%APPDATA%\\Nora` no
  Windows, `~/.nora` fora dele. A config padrão (`nora.toml`) e o build da HUD vêm no pacote.
- `NORA_HOME` (variável do sistema, não do `.env`) troca a pasta do usuário nos dois casos.
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
    """Rodando de dentro de um executável (PyInstaller)."""
    return bool(getattr(sys, "frozen", False))


def no_repositorio() -> bool:
    """Rodando de um checkout do repositório (desenvolvimento), não instalada."""
    return (
        not congelada()
        and (REPOSITORIO / "pyproject.toml").is_file()
        and (REPOSITORIO / "src" / "nora").is_dir()
    )


def pasta_do_usuario(ambiente: dict[str, str] | None = None) -> Path:
    """Onde ficam a config pessoal, o .env, os dados e os modelos."""
    ambiente = os.environ if ambiente is None else ambiente
    if ambiente.get("NORA_HOME"):
        return Path(ambiente["NORA_HOME"]).expanduser()
    if no_repositorio():
        return REPOSITORIO
    if sys.platform == "win32" and ambiente.get("APPDATA"):
        return Path(ambiente["APPDATA"]) / "Nora"
    return Path.home() / ".nora"


def preparar_pasta_do_usuario(pasta: Path) -> None:
    """Na primeira vez (instalada), cria a pasta com uma config pessoal e um .env comentados.
    Nunca sobrescreve o que já existe; no repositório, não faz nada."""
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
    """A pasta do build da HUD (index.html e assets): NORA_HUD_DIST, a cópia dentro do
    executável ou a do repositório (`hud/dist`)."""
    ambiente = os.environ if ambiente is None else ambiente
    if ambiente.get("NORA_HUD_DIST"):
        return Path(ambiente["NORA_HUD_DIST"])
    if congelada():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "hud" / "dist"
    return REPOSITORIO / "hud" / "dist"
