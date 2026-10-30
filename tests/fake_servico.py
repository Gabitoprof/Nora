"""Servidor HTTP falso e genérico para testar os clientes dos serviços locais."""

from __future__ import annotations

import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer

Resposta = tuple[int, str, bytes]


class ServicoFalso:
    def __init__(self, responder: Callable[[str, dict, bytes], Resposta]) -> None:
        self.pedidos: list[tuple[str, dict, bytes]] = []
        dono = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                corpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                cabecalhos = dict(self.headers)
                dono.pedidos.append((self.path, cabecalhos, corpo))
                status, tipo, dados = responder(self.path, cabecalhos, corpo)
                self.send_response(status)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_GET(self):
                self.send_response(404)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.servidor = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.servidor.server_port}"

    def __enter__(self):
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *args):
        self.servidor.shutdown()
        self.servidor.server_close()
