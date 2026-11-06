"""Pastas da Nora no repositório e instalada (.exe, wheel)."""

import sys
from pathlib import Path

from nora import caminhos


def test_no_repositorio_tudo_fica_na_raiz():
    assert caminhos.no_repositorio()
    assert caminhos.pasta_do_usuario({}) == caminhos.REPOSITORIO
    assert caminhos.CONFIG_PADRAO == caminhos.REPOSITORIO / "src" / "nora" / "nora.toml"
    assert caminhos.CONFIG_PADRAO.is_file()
    assert caminhos.build_da_hud({}) == caminhos.REPOSITORIO / "hud" / "dist"


def test_instalada_usa_appdata_no_windows(monkeypatch, tmp_path):
    monkeypatch.setattr(caminhos, "no_repositorio", lambda: False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert caminhos.pasta_do_usuario({"APPDATA": str(tmp_path)}) == tmp_path / "Nora"
    monkeypatch.setattr(sys, "platform", "linux")
    assert caminhos.pasta_do_usuario({}) == Path.home() / ".nora"


def test_nora_home_vale_nos_dois_casos(monkeypatch, tmp_path):
    assert caminhos.pasta_do_usuario({"NORA_HOME": str(tmp_path)}) == tmp_path
    monkeypatch.setattr(caminhos, "no_repositorio", lambda: False)
    assert caminhos.pasta_do_usuario({"NORA_HOME": str(tmp_path)}) == tmp_path


def test_executavel_acha_a_hud_dentro_dele(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert caminhos.congelada() and not caminhos.no_repositorio()
    assert caminhos.build_da_hud({}) == tmp_path / "hud" / "dist"
    assert caminhos.build_da_hud({"NORA_HUD_DIST": "/x"}) == Path("/x")


def test_primeira_vez_cria_config_e_env_sem_sobrescrever(tmp_path):
    pasta = tmp_path / "Nora"
    caminhos.preparar_pasta_do_usuario(pasta)
    local, env = pasta / "config" / "local.toml", pasta / ".env"
    assert local.read_text("utf-8").startswith("# Sua config pessoal")
    assert "ELEVENLABS_API_KEY=" in env.read_text("utf-8")
    local.write_text('[usuario]\nnome = "Lia"\n', encoding="utf-8")
    caminhos.preparar_pasta_do_usuario(pasta)
    assert local.read_text("utf-8") == '[usuario]\nnome = "Lia"\n'


def test_no_repositorio_a_preparacao_nao_cria_nada(monkeypatch):
    criados = []
    monkeypatch.setattr(Path, "write_text", lambda self, *a, **k: criados.append(self))
    caminhos.preparar_pasta_do_usuario(caminhos.REPOSITORIO)
    assert criados == []


def test_config_instalada_le_o_padrao_do_pacote_e_a_pessoal_da_pasta(tmp_path):
    from nora.config import carregar

    pasta = tmp_path / "Nora"
    caminhos.preparar_pasta_do_usuario(pasta)
    (pasta / "config" / "local.toml").write_text('[usuario]\nnome = "Lia"\n', encoding="utf-8")
    (pasta / ".env").write_text("ELEVENLABS_API_KEY=abc\n", encoding="utf-8")
    config = carregar(pasta, ambiente={})
    assert config.arquivos[0] == caminhos.CONFIG_PADRAO
    assert config.nome_usuario == "Lia" and config.chave_elevenlabs == "abc"
    assert config.pasta_dados == pasta / "data"
