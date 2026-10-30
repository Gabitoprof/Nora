"""Servidor de voz local com o Kokoro-82M (pesos Apache-2.0), no mesmo formato do Piper:
POST /synthesize com JSON {"text", "voice"?, "speed"?} devolve um WAV.

Roda como processo separado (`ella servidor-kokoro`) e só é importado aqui: o kokoro-onnx usa o
phonemizer e o espeak-ng, que são GPL-3.0, e por isso ficam fora do núcleo da Ella.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ella.audio import para_wav

PASTA_PADRAO = "models/kokoro"
MODELOS = ("kokoro-v1.0.onnx", "kokoro-v1.0.int8.onnx")
VOZES = "voices-v1.0.bin"


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

    def sintetizar(
        self, texto: str, voz: str | None = None, velocidade: float | None = None
    ) -> bytes:
        import numpy

        with self._trava:
            amostras, taxa = self.kokoro.create(
                texto,
                voice=voz or self.voz,
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
