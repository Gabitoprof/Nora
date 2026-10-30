"""Linha de comando da Ella: `ella` (olá), `ella --verificar` (diagnóstico) e
`ella conversar` (conversa digitada)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from ella import __version__
from ella.config import Config, ConfigError, carregar
from ella.servico import responde


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
        f"  ouvido      {config.ouvido.motor} em {config.ouvido.url} ({config.ouvido.idioma})",
        f"  voz         {config.voz.motor} {config.voz.voz or '(a definir)'} em {config.voz.url}",
        f"  modelo      {config.modelo_local.provedor} {modelo}"
        f" (modo pensando {'ligado' if config.modelo_local.pensar else 'desligado'})",
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
    for nome, url, dica in [
        ("whisper-server", config.ouvido.url, "veja docs/VOZ.md"),
        ("Piper", config.voz.url, "veja docs/VOZ.md"),
    ]:
        estado = "ok" if responde(url) else f"não respondeu em {url} ({dica})"
        linhas.append(f"  {nome:<24}{estado}")
    return linhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ella", description="Assistente de IA pessoal por voz.")
    parser.add_argument("--versao", action="version", version=f"ella {__version__}")
    parser.add_argument(
        "--verificar", action="store_true", help="mostra a config carregada e checa o ambiente"
    )
    comandos = parser.add_subparsers(dest="comando")
    conversar_cmd = comandos.add_parser("conversar", help="conversa digitada com o modelo local")
    conversar_cmd.add_argument(
        "--medir", action="store_true", help="mostra o tempo de cada resposta"
    )
    falar_cmd = comandos.add_parser("falar", help="conversa por voz (aperte Enter para falar)")
    falar_cmd.add_argument("--medir", action="store_true", help="mostra o tempo de cada etapa")
    args = parser.parse_args(argv)

    try:
        config = carregar()
    except ConfigError as erro:
        print(f"Erro na config: {erro}", file=sys.stderr)
        return 1

    if args.comando == "conversar":
        from ella.conversa import conversar

        return conversar(config, medir=args.medir)

    if args.comando == "falar":
        from ella.conversa_voz import conversar_por_voz

        return conversar_por_voz(config, medir=args.medir)

    print(saudacao(config))
    if args.verificar:
        print()
        print("\n".join(verificar(config)))
    return 0
