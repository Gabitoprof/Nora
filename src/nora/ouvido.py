"""Ear: transcribes speech into text through whisper-server (whisper.cpp)."""

from __future__ import annotations

import json
import re
import time
import urllib.request
import uuid
from dataclasses import dataclass

from nora.config import Config
from nora.servico import enviar

# Whisper describes sounds instead of speech in brackets or parentheses, e.g. [MÚSICA DE FUNDO],
# (risos), [BLANK_AUDIO]. That is not the person's speech and must not become a question.
_SO_DESCRICAO = re.compile(r"^(\s*[\[(][^\])]*[\])]\s*)+$")
_DESCRICAO = re.compile(r"\s*[\[(][^\])]*[\])]\s*")


def limpar_transcricao(texto: str) -> str:
    """Removes Whisper's sound descriptions; returns "" if no speech is left."""
    texto = " ".join(texto.split())
    if not texto or _SO_DESCRICAO.match(texto):
        return ""
    return " ".join(_DESCRICAO.sub(" ", texto).split())


@dataclass
class OuvidoWhisper:
    config: Config
    timeout: float = 60.0
    ultima_duracao: float = 0.0

    def transcrever(self, wav: bytes, dica: str = "") -> str:
        """Sends a WAV to whisper-server and returns the recognized text.

        `dica` is a context text for Whisper (e.g. the assistant's name), which helps it spell
        names the right way."""
        fronteira = uuid.uuid4().hex
        campos = {
            "response_format": "json",
            "temperature": "0.0",
            "language": self.config.ouvido.idioma,
        }
        if dica:
            campos["prompt"] = dica
        cabecalho = '--{}\r\nContent-Disposition: form-data; name="{}"\r\n\r\n{}\r\n'
        partes = [
            cabecalho.format(fronteira, nome, valor).encode() for nome, valor in campos.items()
        ]
        partes.append(
            f'--{fronteira}\r\nContent-Disposition: form-data; name="file"; filename="fala.wav"\r\n'
            "Content-Type: audio/wav\r\n\r\n".encode()
            + wav
            + f"\r\n--{fronteira}--\r\n".encode()
        )
        pedido = urllib.request.Request(
            f"{self.config.ouvido.url.rstrip('/')}/inference",
            data=b"".join(partes),
            headers={"Content-Type": f"multipart/form-data; boundary={fronteira}"},
        )
        inicio = time.perf_counter()
        resposta = enviar("o whisper-server", pedido, self.timeout)
        self.ultima_duracao = time.perf_counter() - inicio
        return limpar_transcricao(json.loads(resposta).get("text", ""))
