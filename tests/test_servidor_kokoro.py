import json
import os
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from nora.audio import duracao_wav, para_wav
from nora.servidor_kokoro import Sintetizador, achar_modelo, criar_servidor


class SintetizadorFalso:
    def __init__(self):
        self.pedidos = []

    def sintetizar(self, texto, voz=None, velocidade=None):
        if texto == "quebra":
            raise RuntimeError("falha interna")
        self.pedidos.append((texto, voz, velocidade))
        return para_wav(b"\x00\x00" * 24_000, taxa=24_000)


@pytest.fixture
def servidor():
    sintetizador = SintetizadorFalso()
    http = criar_servidor(sintetizador, "127.0.0.1", 0)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{http.server_port}", sintetizador
    http.shutdown()
    http.server_close()


def post(url, corpo):
    pedido = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST")
    with urllib.request.urlopen(pedido, timeout=5) as resposta:
        return resposta.status, resposta.read()


def test_servidor_sintetiza_e_repassa_voz(servidor):
    url, sintetizador = servidor
    status, wav = post(f"{url}/synthesize", {"text": "Oi!", "voice": "pf_dora", "speed": 1.2})
    assert status == 200
    assert duracao_wav(wav) == pytest.approx(1.0)
    assert sintetizador.pedidos == [("Oi!", "pf_dora", 1.2)]
    with urllib.request.urlopen(url, timeout=5) as resposta:
        assert resposta.read() == b"Kokoro pronto"


@pytest.mark.parametrize(
    ("caminho", "corpo", "status"),
    [
        ("/synthesize", {"text": "  "}, 400),
        ("/outro", {"text": "oi"}, 404),
        ("/synthesize", {"text": "quebra"}, 500),
    ],
)
def test_servidor_recusa_pedidos_ruins(servidor, caminho, corpo, status):
    url, _ = servidor
    with pytest.raises(urllib.error.HTTPError) as erro:
        post(f"{url}{caminho}", corpo)
    assert erro.value.code == status


def test_achar_modelo(tmp_path):
    with pytest.raises(FileNotFoundError, match="Nenhum modelo do Kokoro"):
        achar_modelo(tmp_path)
    (tmp_path / "kokoro-v1.0.int8.onnx").write_bytes(b"")
    assert achar_modelo(tmp_path).name == "kokoro-v1.0.int8.onnx"
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"")
    assert achar_modelo(tmp_path).name == "kokoro-v1.0.onnx"


@pytest.mark.skipif(
    not os.environ.get("ELLA_KOKORO_PASTA"), reason="defina ELLA_KOKORO_PASTA para testar o modelo"
)
def test_kokoro_de_verdade_fala_portugues():
    sintetizador = Sintetizador(Path(os.environ["ELLA_KOKORO_PASTA"]), "pf_dora", 1.0)
    wav = sintetizador.sintetizar("Olá, eu sou a Nora.")
    assert duracao_wav(wav) > 0.5
