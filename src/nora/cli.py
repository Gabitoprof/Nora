"""Linha de comando da Nora: `nora` (olá), `nora --verificar` (diagnóstico) e
`nora conversar` (conversa digitada)."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

from nora import __version__, versao_legivel
from nora.config import Config, ConfigError, carregar
from nora.servico import responde


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
    texto = f"elevenlabs {voz.elevenlabs.voz_id or '(sem voz_id)'} ({voz.elevenlabs.modelo})"
    return texto + (f", reserva {voz.reserva}" if voz.reserva else "")


def _instalado(modelo: str, instalados: list[str]) -> bool:
    """O Ollama lista "bge-m3:latest" para quem pediu "bge-m3"."""
    return modelo in instalados or f"{modelo}:latest" in instalados


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
    elif _instalado(modelo, instalados):
        linhas.append(f"  Ollama                  ok, {modelo} instalado")
    else:
        linhas.append(f"  Ollama                  ok, mas falta o modelo: ollama pull {modelo}")
    if config.memoria.ativa:
        embeddings = config.memoria.modelo_embeddings
        if instalados is None:
            estado = "depende do Ollama"
        elif _instalado(embeddings, instalados):
            estado = f"ok, {embeddings} instalado, em {config.pasta_dados / 'memoria.db'}"
        else:
            estado = f"falta o modelo: ollama pull {embeddings}"
        linhas.append(f"  {'Memória':<24}{estado}")
    servicos = [("whisper-server", config.ouvido.url)]
    for motor, papel in [(config.voz.motor, ""), (config.voz.reserva, " (reserva)")]:
        if motor == "kokoro":
            servicos.append((f"Kokoro{papel}", config.voz.kokoro.url))
        elif motor == "piper":
            servicos.append((f"Piper{papel}", config.voz.piper.url))
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

    from nora import audio

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


def comando_memoria(config: Config, args) -> int:
    from nora.memoria import Memoria, abrir_memoria
    from nora.servico import ServicoIndisponivel

    memoria: Memoria | None = abrir_memoria(config)
    if memoria is None:
        print("A memória está desligada ([memoria] ativa = false).", file=sys.stderr)
        return 1
    try:
        if args.acao == "listar":
            fatos = memoria.listar()
            print(f"{len(fatos)} fatos em {memoria.caminho}:")
            for fato in fatos:
                print(f"  {fato.id:>4}  {fato.texto}  ({fato.atualizado[:10]})")
        elif args.acao == "buscar":
            for fato in memoria.buscar(" ".join(args.texto), k=10):
                print(f"  {fato.id:>4}  {fato.similaridade:.2f}  {fato.texto}")
        elif args.acao == "lembrar":
            fato_id, novo = memoria.lembrar(" ".join(args.texto), origem="manual")
            print(f"{'Guardado' if novo else 'Atualizado'} (nº {fato_id}).")
        elif args.acao == "esquecer":
            if not memoria.esquecer(args.id):
                print(f"Não existe fato nº {args.id}.", file=sys.stderr)
                return 1
            print(f"Esquecido (nº {args.id}).")
        elif args.acao == "importar":
            from nora.importar import importar_historico

            return importar_historico(config, memoria)
    except ServicoIndisponivel as erro:
        modelo = config.memoria.modelo_embeddings
        print(
            f"[erro] {erro}\nA memória usa o Ollama: rode 'ollama pull {modelo}'.", file=sys.stderr
        )
        return 1
    finally:
        memoria.fechar()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nora", description="Assistente de IA pessoal por voz.")
    parser.add_argument("--versao", action="version", version=f"nora {__version__}")
    parser.add_argument(
        "--verificar", action="store_true", help="mostra a config carregada e checa o ambiente"
    )
    comandos = parser.add_subparsers(dest="comando")
    conversar_cmd = comandos.add_parser("conversar", help="conversa digitada com o modelo local")
    conversar_cmd.add_argument(
        "--medir", action="store_true", help="mostra o tempo de cada resposta"
    )
    conversar_cmd.add_argument(
        "--voz", action="store_true", help="a resposta também sai falada (sem usar microfone)"
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
    memoria_cmd = comandos.add_parser("memoria", help="ver e editar o que a Nora lembra de você")
    acoes = memoria_cmd.add_subparsers(dest="acao", required=True)
    acoes.add_parser("listar", help="todos os fatos guardados")
    buscar_cmd = acoes.add_parser("buscar", help="fatos parecidos com um texto")
    buscar_cmd.add_argument("texto", nargs="+")
    lembrar_cmd = acoes.add_parser("lembrar", help="guardar um fato à mão")
    lembrar_cmd.add_argument("texto", nargs="+")
    esquecer_cmd = acoes.add_parser("esquecer", help="apagar um fato pelo número")
    esquecer_cmd.add_argument("id", type=int)
    acoes.add_parser("importar", help="tirar fatos das conversas antigas (data/historico)")
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
        if args.voz:
            from nora.conversa_voz import conversar_por_voz

            return conversar_por_voz(config, medir=args.medir, so_teclado=True)
        from nora.conversa import conversar

        return conversar(config, medir=args.medir)

    if args.comando == "memoria":
        return comando_memoria(config, args)

    if args.comando == "servidor-kokoro":
        from pathlib import Path

        from nora.config import RAIZ
        from nora.servidor_kokoro import PASTA_PADRAO, servir

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
        from nora.maos_livres import conversar_maos_livres

        return conversar_maos_livres(
            config,
            medir=args.medir,
            mostrar_ignoradas=args.mostrar_ignoradas,
            gravar_falas=args.gravar_falas,
        )

    if args.comando == "falar":
        from nora.conversa_voz import conversar_por_voz

        return conversar_por_voz(config, medir=args.medir)

    print(saudacao(config))
    if args.verificar:
        print()
        print("\n".join(verificar(config)))
    return 0
