"""Ouvido: transcreve fala em texto pelo whisper-server (whisper.cpp)."""

from __future__ import annotations

import json
import re
import time
import urllib.request
import uuid
from dataclasses import dataclass

from ella.config import Config
from ella.servico import enviar

# O Whisper descreve sons em vez de fala entre colchetes ou parênteses, ex.: [MÚSICA DE FUNDO],
# (risos), [BLANK_AUDIO]. Isso não é fala da pessoa e não deve virar pergunta.
_SO_DESCRICAO = re.compile(r"^(\s*[\[(][^\])]*[\])]\s*)+$")
_DESCRICAO = re.compile(r"\s*[\[(][^\])]*[\])]\s*")


def limpar_transcricao(texto: str) -> str:
    """Tira as descrições de som do Whisper; devolve "" se não sobrou fala."""
    texto = " ".join(texto.split())
    if not texto or _SO_DESCRICAO.match(texto):
        return ""
    return " ".join(_DESCRICAO.sub(" ", texto).split())


@dataclass
class OuvidoWhisper:
    config: Config
    timeout: float = 60.0
    ultima_duracao: float = 0.0

    def transcrever(self, wav: bytes) -> str:
        """Envia um WAV ao whisper-server e devolve o texto reconhecido."""
        fronteira = uuid.uuid4().hex
        campos = {
            "response_format": "json",
            "temperature": "0.0",
            "language": self.config.ouvido.idioma,
        }
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
