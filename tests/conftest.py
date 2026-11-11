from pathlib import Path

import pytest

from nora.config import RAIZ


@pytest.fixture
def criar_raiz(tmp_path: Path):
    """Temporary folder with the repository's default config, without the .env and local.toml of
    whoever runs the tests."""

    def criar(local: str | None = None, env: str | None = None) -> Path:
        (tmp_path / "config").mkdir(exist_ok=True)
        (tmp_path / "config/nora.toml").write_text(
            (RAIZ / "config/nora.toml").read_text(encoding="utf-8"), encoding="utf-8"
        )
        # Memory stays off in the tests, unless the test turns it on: it would make extra requests
        # to the fake Ollama in the background.
        local = local or ""
        if "[memoria]" not in local:
            local += "\n[memoria]\nativa = false\n"
        (tmp_path / "config/local.toml").write_text(local, encoding="utf-8")
        if env is not None:
            (tmp_path / ".env").write_text(env, encoding="utf-8")
        return tmp_path

    return criar
