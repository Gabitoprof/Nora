import io
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

from nora.audio import como_wav_16bits, duracao_wav, ler_wav, para_wav
from nora.config import carregar
from nora.servico import ServicoIndisponivel
from nora.voz import VozComfyUI, criar_voz

FLUXO = {
    "3": {"class_type": "TextoParaFala", "inputs": {"text": "{{texto}}", "seed": 42}},
    "7": {"class_type": "SaveAudio", "inputs": {"audio": ["3", 0], "filename_prefix": "nora"}},
}


class ComfyFalso:
    """Imita a API do ComfyUI: /prompt enfileira, /history fica pronto na 2ª consulta, /view
    devolve o arquivo de áudio."""

    def __init__(self, audio: bytes, saidas=None, erro=False):
        self.recebidos = []
        self.consultas = 0
        dono = self

        class Handler(BaseHTTPRequestHandler):
            def _json(self, dados, status=200):
                corpo = json.dumps(dados).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_POST(self):
                dono.recebidos.append(
                    json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                )
                self._json({"prompt_id": "abc", "number": 1})

            def do_GET(self):
                partes = urlsplit(self.path)
                if partes.path == "/history/abc":
                    dono.consultas += 1
                    if dono.consultas < 2:
                        return self._json({})
                    status = {"status_str": "error" if erro else "success", "completed": True}
                    padrao = {
                        "7": {
                            "audio": [
                                {"filename": "nora_00001_.flac", "subfolder": "", "type": "output"}
                            ]
                        }
                    }
                    return self._json(
                        {"abc": {"status": status, "outputs": padrao if saidas is None else saidas}}
                    )
                if partes.path == "/view":
                    dono.vista = parse_qs(partes.query)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(audio)
                    return None
                return self._json({}, 404)

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


def flac_de_um_segundo():
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    saida = io.BytesIO()
    sf.write(saida, np.full((24_000, 2), 0.25, dtype="float32"), 24_000, format="FLAC")
    return saida.getvalue()


def voz_de_teste(tmp_path, url, fluxo=FLUXO, **extra):
    arquivo = tmp_path / "voz_comfyui.json"
    arquivo.write_text(json.dumps(fluxo), encoding="utf-8")
    return VozComfyUI(url, arquivo, intervalo=0.01, **extra)


def test_comfyui_gera_a_fala_pelo_fluxo(tmp_path):
    with ComfyFalso(flac_de_um_segundo()) as comfy:
        voz = voz_de_teste(tmp_path, comfy.url, pronuncias={"Nora": "Nóra"})
        wav = voz.sintetizar("Oi, eu sou a Nora.")
    enviado = comfy.recebidos[0]["prompt"]
    assert enviado["3"]["inputs"]["text"] == "Oi, eu sou a Nóra."
    assert enviado["3"]["inputs"]["seed"] == 42  # o resto do fluxo não muda
    assert comfy.recebidos[0]["client_id"].startswith("nora-")
    assert comfy.vista["filename"] == ["nora_00001_.flac"]
    amostras, taxa, canais = ler_wav(wav)
    assert (taxa, canais) == (24_000, 1)  # o FLAC estéreo virou WAV mono de 16 bits
    assert duracao_wav(wav) == pytest.approx(1.0)


def test_fluxo_sem_marcador_ou_sem_arquivo(tmp_path):
    sem_marcador = {"3": {"inputs": {"text": "frase fixa"}}}
    with pytest.raises(ServicoIndisponivel, match="não tem {{texto}}"):
        voz_de_teste(tmp_path, "http://127.0.0.1:9", sem_marcador).sintetizar("oi")
    with pytest.raises(ServicoIndisponivel, match="Export \\(API\\)"):
        VozComfyUI("http://127.0.0.1:9", tmp_path / "nao_existe.json").sintetizar("oi")


def test_fluxo_com_erro_ou_sem_audio(tmp_path):
    with ComfyFalso(b"", erro=True) as comfy:
        with pytest.raises(ServicoIndisponivel, match="deu erro"):
            voz_de_teste(tmp_path, comfy.url).sintetizar("oi")
    with ComfyFalso(b"", saidas={"7": {"images": []}}) as comfy:
        with pytest.raises(ServicoIndisponivel, match="Save Audio"):
            voz_de_teste(tmp_path, comfy.url).sintetizar("oi")


def test_comfyui_na_config(criar_raiz, tmp_path):
    local = (
        '[voz]\nmotor = "comfyui"\nreserva = ""\n'
        '[voz.comfyui]\nfluxo = "config/minha_voz.json"\nespera_s = 30.0\n'
    )
    raiz = criar_raiz(local=local)
    voz = criar_voz(carregar(raiz, ambiente={}))
    assert isinstance(voz, VozComfyUI)
    assert voz.fluxo == raiz / "config" / "minha_voz.json"
    assert voz.espera_s == 30.0


def test_wav_de_16_bits_passa_direto():
    wav = para_wav(b"\x01\x00" * 100, taxa=22_050)
    assert como_wav_16bits(wav) == wav
