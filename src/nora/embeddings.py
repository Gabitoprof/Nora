"""Embeddings: transforma textos em vetores de significado pelo Ollama (/api/embed)."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from nora.config import Config
from nora.servico import enviar


@dataclass
class EmbeddingsOllama:
    config: Config
    timeout: float = 60.0

    def vetores(self, textos: list[str]) -> list[list[float]]:
        if not textos:
            return []
        pedido = urllib.request.Request(
            f"{self.config.ollama_host.rstrip('/')}/api/embed",
            data=json.dumps(
                {
                    "model": self.config.memoria.modelo_embeddings,
                    "input": textos,
                    "keep_alive": self.config.modelo_local.keep_alive,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return json.loads(enviar("o Ollama", pedido, self.timeout))["embeddings"]

    def vetor(self, texto: str) -> list[float]:
        return self.vetores([texto])[0]
