import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from ella.cli import modelos_ollama, verificar
from ella.config import carregar


class OllamaFalso(BaseHTTPRequestHandler):
    def do_GET(self):
        corpo = json.dumps({"models": [{"name": "qwen3.5:9b"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass


def test_verificar_encontra_o_modelo_no_ollama(criar_raiz):
    servidor = HTTPServer(("127.0.0.1", 0), OllamaFalso)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    host = f"http://127.0.0.1:{servidor.server_port}"
    try:
        assert modelos_ollama(host) == ["qwen3.5:9b"]
        linhas = verificar(carregar(criar_raiz(), ambiente={"OLLAMA_HOST": host}))
        assert any("qwen3.5:9b instalado" in linha for linha in linhas)
    finally:
        servidor.shutdown()


def test_verificar_sem_ollama(criar_raiz):
    linhas = verificar(carregar(criar_raiz(), ambiente={"OLLAMA_HOST": "http://127.0.0.1:9"}))
    assert any("não respondeu" in linha for linha in linhas)
