"""Linha de comando da Ella: `ella` (olá), `ella --verificar` (diagnóstico) e
`ella conversar` (conversa digitada)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from ella import __version__, versao_legivel
from ella.config import Config, ConfigError, carregar
from ella.servico import responde


def saudacao(config: Config) -> str:
    quem = f", {config.nome_usuario}" if config.nome_usuario else ""
    return f"Olá{quem}! Eu sou a {config.assistente.nome}, versão {versao_legivel()}."


def modelos_ollama(host: str, timeout: float = 2.0) -> list[str] | None:
    """Lista os modelos instalados no Ollama, ou None se ele não responder."""
    try:
        with urllib.request.urlopen(f"{host.rstrip('/')}/api/tags", timeout=timeout) as resposta:
            dados = json.load(resposta)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return [modelo.get("name", "") for modelo in dados.get("models", [])]


def descrever_voz(config: Config) -> str:
    voz = config.voz
    if voz.motor == "kokoro":
        return f"kokoro {voz.kokoro.voz} (velocidade {voz.kokoro.velocidade}) em {voz.kokoro.url}"
    if voz.motor == "piper":
        return f"piper {voz.piper.voz} em {voz.piper.url}"
    return f"elevenlabs {voz.elevenlabs.voz_id or '(sem voz_id)'} ({voz.elevenlabs.modelo})"


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
        f"  voz         {descrever_voz(config)}",
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
    servicos = [("whisper-server", config.ouvido.url)]
    if config.voz.motor == "kokoro":
        servicos.append(("Kokoro", config.voz.kokoro.url))
    elif config.voz.motor == "piper":
        servicos.append(("Piper", config.voz.piper.url))
    for nome, url in servicos:
        estado = "ok" if responde(url) else f"não respondeu em {url} (veja docs/VOZ.md)"
        linhas.append(f"  {nome:<24}{estado}")
    if config.voz.motor == "elevenlabs":
        faltando = [
            nome
            for nome, valor in [
                ("ELEVENLABS_API_KEY no .env", config.chave_elevenlabs),
                ("voz_id em [voz.elevenlabs]", config.voz.elevenlabs.voz_id),
            ]
            if not valor
        ]
        estado = "configurado" if not faltando else "falta " + " e ".join(faltando)
        linhas.append(f"  {'ElevenLabs':<24}{estado}")
    return linhas


def testar_audio(config: Config, segundos: float, entrada=input) -> int:
    """Lista os dispositivos de áudio e grava alguns segundos para tocar de volta."""
    import threading

    from ella import audio

    try:
        print("Dispositivos de áudio:")
        print("\n".join(audio.listar_dispositivos()))
        print(
            f"\nEm uso: microfone '{config.audio.microfone or 'padrão'}', "
            f"alto-falante '{config.audio.alto_falante or 'padrão'}' (config [audio])."
        )
        entrada(f"\nAperte Enter e fale por {segundos:.0f} segundos...")
        parar = threading.Timer(segundos, lambda: None)
        parar.start()
        wav = audio.gravar_ate_enter(
            lambda _: parar.join(), audio.dispositivo(config.audio.microfone)
        )
        print(f"Gravei {audio.duracao_wav(wav):.1f} s. Tocando de volta...")
        audio.tocar_wav(wav, audio.dispositivo(config.audio.alto_falante))
    except RuntimeError as erro:
        print(f"[erro] {erro}", file=sys.stderr)
        return 1
    print("Se você ouviu a sua voz, o áudio está funcionando.")
    return 0


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
    audio_cmd = comandos.add_parser("audio", help="lista microfones e alto-falantes e faz um teste")
    audio_cmd.add_argument(
        "--segundos", type=float, default=3.0, help="duração da gravação de teste"
    )
    ouvir_cmd = comandos.add_parser(
        "ouvir", help="conversa mãos livres: comece a frase com o nome dela"
    )
    ouvir_cmd.add_argument("--medir", action="store_true", help="mostra o tempo de cada etapa")
    ouvir_cmd.add_argument(
        "--mostrar-ignoradas",
        action="store_true",
        help="mostra as falas ouvidas que não começaram com o nome dela",
    )
    ouvir_cmd.add_argument(
        "--gravar-falas",
        action="store_true",
        help="salva cada fala ouvida em data/falas (para diagnóstico)",
    )
    kokoro_cmd = comandos.add_parser(
        "servidor-kokoro", help="inicia o servidor de voz local Kokoro (fica rodando)"
    )
    kokoro_cmd.add_argument(
        "--pasta", default=None, help="pasta com o modelo e as vozes (padrão: models/kokoro)"
    )
    args = parser.parse_args(argv)

    try:
        config = carregar()
    except ConfigError as erro:
        print(f"Erro na config: {erro}", file=sys.stderr)
        return 1

    if args.comando == "conversar":
        from ella.conversa import conversar

        return conversar(config, medir=args.medir)

    if args.comando == "servidor-kokoro":
        from pathlib import Path

        from ella.config import RAIZ
        from ella.servidor_kokoro import PASTA_PADRAO, servir

        kokoro = config.voz.kokoro
        pasta = Path(args.pasta) if args.pasta else RAIZ / PASTA_PADRAO
        try:
            return servir(kokoro.url, pasta, kokoro.voz, kokoro.velocidade)
        except (RuntimeError, FileNotFoundError) as erro:
            print(f"[erro] {erro}", file=sys.stderr)
            return 1

    if args.comando == "audio":
        return testar_audio(config, args.segundos)

    if args.comando == "ouvir":
        from ella.maos_livres import conversar_maos_livres

        return conversar_maos_livres(
            config,
            medir=args.medir,
            mostrar_ignoradas=args.mostrar_ignoradas,
            gravar_falas=args.gravar_falas,
        )

    if args.comando == "falar":
        from ella.conversa_voz import conversar_por_voz

        return conversar_por_voz(config, medir=args.medir)

    print(saudacao(config))
    if args.verificar:
        print()
        print("\n".join(verificar(config)))
    return 0
