"""Servidor falso que imita a API /api/chat do Ollama em streaming."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class OllamaFalso:
    def __init__(self, pedacos: list[str], erro: str | None = None, status: int = 200) -> None:
        self.pedacos = pedacos
        self.erro = erro
        self.status = status
        self.pedidos: list[dict] = []
        dono = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                tamanho = int(self.headers["Content-Length"])
                dono.pedidos.append(json.loads(self.rfile.read(tamanho)))
                self.send_response(dono.status)
                self.send_header("Content-Type", "application/x-ndjson")
                self.end_headers()
                if dono.status != 200:
                    self.wfile.write(b'{"error":"modelo nao encontrado"}')
                    return
                if dono.erro:
                    self.wfile.write(json.dumps({"error": dono.erro}).encode() + b"\n")
                    return
                for pedaco in dono.pedacos:
                    linha = {"message": {"role": "assistant", "content": pedaco}, "done": False}
                    self.wfile.write(json.dumps(linha).encode() + b"\n")
                    self.wfile.flush()
                fim = {
                    "message": {"content": ""},
                    "done": True,
                    "eval_count": 10,
                    "eval_duration": 200_000_000,
                }
                self.wfile.write(json.dumps(fim).encode() + b"\n")

            def log_message(self, *args):
                pass

        self.servidor = HTTPServer(("127.0.0.1", 0), Handler)
        self.host = f"http://127.0.0.1:{self.servidor.server_port}"

    def __enter__(self):
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *args):
        self.servidor.shutdown()
        self.servidor.server_close()
