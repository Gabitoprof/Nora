"""Cérebro local: conversa com o modelo do Ollama em streaming."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from dataclasses import dataclass, field

from nora.config import Config


class CerebroIndisponivel(Exception):
    """O cérebro (Ollama ou nuvem) não respondeu ou recusou o pedido. `categoria` diz o tipo da
    falha para o diagnóstico (erro_provedor, timeout, resposta_vazia); vazia = descobrir."""

    def __init__(self, mensagem: str = "", categoria: str = "") -> None:
        super().__init__(mensagem)
        self.categoria = categoria


def categoria_do_erro(erro: Exception) -> str:
    """erro_provedor, timeout ou resposta_vazia, para o observador agrupar as falhas."""
    if getattr(erro, "categoria", ""):
        return erro.categoria
    causa = erro.__cause__
    texto = str(erro).lower()
    if (
        isinstance(causa, TimeoutError)
        or "timeout" in type(causa).__name__.lower()
        or "timed out" in texto
        or "tempo esgotado" in texto
    ):
        return "timeout"
    return "erro_provedor"


@dataclass
class Medidas:
    """Tempos da última resposta, em segundos."""

    primeiro_pedaco: float = 0.0
    total: float = 0.0
    tokens: int = 0
    tokens_por_segundo: float = 0.0


@dataclass
class CerebroLocal:
    config: Config
    timeout: float = 120.0
    medidas: Medidas = field(default_factory=Medidas)

    def _pedido(self, corpo: dict) -> urllib.request.Request:
        return urllib.request.Request(
            f"{self.config.ollama_host.rstrip('/')}/api/chat",
            data=json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    def aquecer(self) -> float:
        """Carrega o modelo na memória sem gerar nada; devolve quanto tempo levou."""
        modelo = self.config.modelo_local
        inicio = time.perf_counter()
        pedido = self._pedido(
            {
                "model": modelo.modelo,
                "messages": [],
                "stream": False,
                "keep_alive": modelo.keep_alive,
            }
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                resposta.read()
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", "replace").strip()
            raise CerebroIndisponivel(
                f"O Ollama recusou o pedido ({erro.code}): {detalhe}"
            ) from erro
        except (urllib.error.URLError, OSError) as erro:
            raise CerebroIndisponivel(
                f"Não consegui falar com o Ollama em {self.config.ollama_host}. Ele está aberto?"
            ) from erro
        return time.perf_counter() - inicio

    def descarregar(self) -> None:
        """Tira o modelo da memória da placa de vídeo agora (modo jogo)."""
        pedido = urllib.request.Request(
            f"{self.config.ollama_host.rstrip('/')}/api/generate",
            data=json.dumps({"model": self.config.modelo_local.modelo, "keep_alive": 0}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=self.timeout) as resposta:
                resposta.read()
        except (urllib.error.URLError, OSError) as erro:
            raise CerebroIndisponivel(
                f"Não consegui falar com o Ollama em {self.config.ollama_host}."
            ) from erro

    def responder(self, mensagens: list[dict[str, str]]) -> Iterator[str]:
        """Envia a conversa ao Ollama e devolve a resposta aos pedaços, conforme é gerada."""
        modelo = self.config.modelo_local
        pedido = self._pedido(
            {
                "model": modelo.modelo,
                "messages": mensagens,
                "stream": True,
                "think": modelo.pensar,
                "keep_alive": modelo.keep_alive,
                "options": {"temperature": modelo.temperatura},
            }
        )
        inicio = time.perf_counter()
        self.medidas = Medidas()
        try:
            resposta = urllib.request.urlopen(pedido, timeout=self.timeout)
        except urllib.error.HTTPError as erro:
            detalhe = erro.read().decode("utf-8", "replace").strip()
            raise CerebroIndisponivel(
                f"O Ollama recusou o pedido ({erro.code}): {detalhe}"
            ) from erro
        except (urllib.error.URLError, OSError) as erro:
            raise CerebroIndisponivel(
                f"Não consegui falar com o Ollama em {self.config.ollama_host}. Ele está aberto?"
            ) from erro

        with resposta:
            for linha in resposta:
                if not linha.strip():
                    continue
                dados = json.loads(linha)
                if "error" in dados:
                    raise CerebroIndisponivel(f"Erro do Ollama: {dados['error']}")
                pedaco = dados.get("message", {}).get("content", "")
                if pedaco:
                    if not self.medidas.primeiro_pedaco:
                        self.medidas.primeiro_pedaco = time.perf_counter() - inicio
                    yield pedaco
                if dados.get("done"):
                    self.medidas.tokens = dados.get("eval_count", 0)
                    duracao = dados.get("eval_duration", 0) / 1e9
                    if duracao:
                        self.medidas.tokens_por_segundo = self.medidas.tokens / duracao
                    break
        self.medidas.total = time.perf_counter() - inicio
