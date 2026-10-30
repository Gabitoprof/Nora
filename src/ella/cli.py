"""Linha de comando da Ella: `ella` (olá) e `ella --verificar` (diagnóstico)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from ella import __version__
from ella.config import Config, ConfigError, carregar


def saudacao(config: Config) -> str:
    quem = f", {config.nome_usuario}" if config.nome_usuario else ""
    return f"Olá{quem}! Eu sou a {config.assistente.nome}, versão {__version__}."


def modelos_ollama(host: str, timeout: float = 2.0) -> list[str] | None:
    """Lista os modelos instalados no Ollama, ou None se ele não responder."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as resposta:
            dados = json.load(resposta)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return [modelo.get("name", "") for modelo in dados.get("models", [])]


def verificar(config: Config) -> list[str]:
    persona = config.persona
    chave = "definida" if config.tem_chave_anthropic else "não definida (só precisa na v0.3.0)"
    modelo = config.modelo_local.modelo
    linhas = [
        "Config:",
        *(f"  arquivo     {arquivo}" for arquivo in config.arquivos),
        f"  assistente  {config.assistente.nome} ({config.assistente.idioma})",
        f"  usuário     {config.nome_usuario or '(não definido: config/local.toml)'}",
        f"  persona     humor {persona.humor:.1f}, formalidade {persona.formalidade:.1f}",
        f"  voz         {config.voz.motor} {config.voz.voz or '(a definir)'}",
        f"  modelo      {config.modelo_local.provedor} {config.modelo_local.modelo}",
        f"  nuvem       {config.modelo_nuvem.rapido} / {config.modelo_nuvem.pesado}",
        f"  dados       {config.pasta_dados}",
        "",
        "Ambiente:",
        f"  chave da API Anthropic  {chave}",
    ]
    instalados = modelos_ollama(config.ollama_host)
    if instalados is None:
        linhas.append(f"  Ollama                  não respondeu em {config.ollama_host}")
    elif modelo in instalados:
        linhas.append(f"  Ollama                  ok, {modelo} instalado")
    else:
        linhas.append(f"  Ollama                  ok, mas falta o modelo: ollama pull {modelo}")
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ella", description="Assistente de IA pessoal por voz.")
    parser.add_argument("--versao", action="version", version=f"ella {__version__}")
    parser.add_argument(
        "--verificar", action="store_true", help="mostra a config carregada e checa o ambiente"
    )
    args = parser.parse_args(argv)

    try:
        config = carregar()
    except ConfigError as erro:
        print(f"Erro na config: {erro}", file=sys.stderr)
        return 1

    print(saudacao(config))
    if args.verificar:
        print()
        print("\n".join(verificar(config)))
    return 0
