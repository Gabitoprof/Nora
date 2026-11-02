"""Servidor de voz local com o Kokoro-82M (pesos Apache-2.0), no mesmo formato do Piper:
POST /synthesize com JSON {"text", "voice"?, "speed"?} devolve um WAV.

Roda como processo separado (`nora servidor-kokoro`) e só é importado aqui: o kokoro-onnx usa o
phonemizer e o espeak-ng, que são GPL-3.0, e por isso ficam fora do núcleo da Nora.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from nora.audio import para_wav

PASTA_PADRAO = "models/kokoro"
MODELOS = ("kokoro-v1.0.onnx", "kokoro-v1.0.int8.onnx")
VOZES = "voices-v1.0.bin"


def ler_receita(receita: str) -> list[tuple[str, float]]:
    """'pf_dora:0.7 + af_heart:0.3' -> [('pf_dora', 0.7), ('af_heart', 0.3)], com os pesos
    somando 1. Uma voz sozinha ('pf_dora') vale peso 1."""
    partes = []
    for parte in receita.split("+"):
        parte = parte.strip()
        if not parte:
            continue
        nome, _, peso = parte.partition(":")
        try:
            valor = float(peso) if peso.strip() else 1.0
        except ValueError as erro:
            raise ValueError(f"Peso inválido em '{parte}' (use nome:0.5).") from erro
        if valor <= 0:
            raise ValueError(f"O peso de '{nome.strip()}' precisa ser maior que zero.")
        partes.append((nome.strip(), valor))
    if not partes:
        raise ValueError("Receita de voz vazia.")
    total = sum(peso for _, peso in partes)
    return [(nome, peso / total) for nome, peso in partes]


def achar_modelo(pasta: Path) -> Path:
    for nome in MODELOS:
        if (pasta / nome).is_file():
            return pasta / nome
    raise FileNotFoundError(
        f"Nenhum modelo do Kokoro em {pasta} ({' ou '.join(MODELOS)}). "
        "Rode scripts\\instalar_voz_windows.ps1."
    )


class Sintetizador:
    """Carrega o Kokoro uma vez e gera WAV de 16 bits."""

    def __init__(self, pasta: Path, voz: str, velocidade: float, idioma: str = "pt-br") -> None:
        try:
            from kokoro_onnx import Kokoro
        except ImportError as erro:
            raise RuntimeError('Falta o Kokoro. Instale com: pip install -e ".[kokoro]"') from erro
        self.kokoro = Kokoro(str(achar_modelo(pasta)), str(pasta / VOZES))
        self.voz = voz
        self.velocidade = velocidade
        self.idioma = idioma
        self._trava = threading.Lock()
        self._misturas: dict = {}
        self.estilo(voz)  # confere a receita já ao abrir

    def vozes(self) -> list[str]:
        return sorted(self.kokoro.get_voices())

    def estilo(self, receita: str):
        """O "DNA" da voz: uma voz do Kokoro ou a mistura de várias, pela receita."""
        if receita not in self._misturas:
            disponiveis = set(self.kokoro.get_voices())
            partes = ler_receita(receita)
            desconhecidas = [nome for nome, _ in partes if nome not in disponiveis]
            if desconhecidas:
                raise ValueError(
                    f"Voz desconhecida: {', '.join(desconhecidas)}. "
                    "Veja as vozes com 'nora voz listar'."
                )
            self._misturas[receita] = sum(
                peso * self.kokoro.get_voice_style(nome) for nome, peso in partes
            )
        return self._misturas[receita]

    def sintetizar(
        self, texto: str, voz: str | None = None, velocidade: float | None = None
    ) -> bytes:
        import numpy

        with self._trava:
            amostras, taxa = self.kokoro.create(
                texto,
                voice=self.estilo(voz or self.voz),
                speed=velocidade or self.velocidade,
                lang=self.idioma,
            )
        pcm = (numpy.clip(amostras, -1.0, 1.0) * 32767).astype("<i2").tobytes()
        return para_wav(pcm, taxa=taxa)


def criar_servidor(sintetizador, host: str, porta: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def _responder(self, status: int, tipo: str, corpo: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):
            self._responder(200, "text/plain; charset=utf-8", b"Kokoro pronto")

        def do_POST(self):
            if urlsplit(self.path).path != "/synthesize":
                self._responder(404, "text/plain", b"use POST /synthesize")
                return
            try:
                dados = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                texto = str(dados.get("text", "")).strip()
                if not texto:
                    raise ValueError("campo 'text' vazio")
                wav = sintetizador.sintetizar(texto, dados.get("voice"), dados.get("speed"))
            except (ValueError, KeyError, TypeError) as erro:
                self._responder(400, "text/plain; charset=utf-8", str(erro).encode())
                return
            except Exception as erro:  # o servidor continua de pé para a próxima frase
                self._responder(500, "text/plain; charset=utf-8", str(erro).encode())
                return
            self._responder(200, "audio/wav", wav)

        def log_message(self, formato, *args):
            pass

    return ThreadingHTTPServer((host, porta), Handler)


def servir(url: str, pasta: Path, voz: str, velocidade: float) -> int:
    partes = urlsplit(url)
    host, porta = partes.hostname or "127.0.0.1", partes.port or 5001
    print(f"Carregando o Kokoro de {pasta}...")
    sintetizador = Sintetizador(pasta, voz, velocidade)
    sintetizador.sintetizar("Pronto.")  # aquece, para a primeira frase não demorar
    servidor = criar_servidor(sintetizador, host, porta)
    print(f"Kokoro pronto em http://{host}:{porta} (voz {voz}). Ctrl+C encerra.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0
