"""Voz: transforma texto em fala pelo servidor HTTP do Piper."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

from ella.config import Config
from ella.servico import enviar


@dataclass
class VozPiper:
    config: Config
    timeout: float = 60.0
    ultima_duracao: float = 0.0

    def sintetizar(self, texto: str) -> bytes:
        """Devolve o WAV falado do texto."""
        pedido = urllib.request.Request(
            f"{self.config.voz.url.rstrip('/')}/synthesize",
            data=json.dumps({"text": texto}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        inicio = time.perf_counter()
        wav = enviar("o Piper", pedido, self.timeout)
        self.ultima_duracao = time.perf_counter() - inicio
        return wav
