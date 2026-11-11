"""OpenAI (ChatGPT) cloud brain, streaming, through the Responses API.

Same shape as the local brain and Claude: takes the messages (persona, memory notes,
conversation) and returns the answer in chunks. Uses the official `openai` SDK ([nuvem] extra)
and the OPENAI_API_KEY key from .env. With no answer (error, refusal or nothing written), it
signals CerebroIndisponivel, and the router asks Claude.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from nora.cerebro import CerebroIndisponivel, Medidas
from nora.cerebro_nuvem import separar_sistema
from nora.config import Config


def problema_do_pacote() -> str:
    """ "" if the OpenAI SDK loads; otherwise, what is missing or the load error."""
    try:
        import openai  # noqa: F401
    except ModuleNotFoundError as erro:
        if erro.name == "openai":
            return 'falta o pacote da OpenAI: python -m pip install -e ".[nuvem]"'
        return f"o pacote da OpenAI não carregou (falta {erro.name}): {erro}"
    except ImportError as erro:
        return f"o pacote da OpenAI não carregou: {erro}"
    return ""


@dataclass
class CerebroOpenAI:
    config: Config
    modelo: str
    esforco: str = "medium"
    max_tokens: int = 8000
    cliente: object = None
    medidas: Medidas = field(default_factory=Medidas)
    # whether something was already said in this answer (then the brain cannot be switched)
    escreveu: bool = False

    @property
    def nome(self) -> str:
        return f"ChatGPT ({self.modelo})"

    def _cliente(self):
        if self.cliente is not None:
            return self.cliente
        if not self.config.chave_openai:
            raise CerebroIndisponivel("Falta OPENAI_API_KEY no .env para usar o ChatGPT.")
        if problema := problema_do_pacote():
            raise CerebroIndisponivel(problema)
        import openai

        self.cliente = openai.OpenAI(api_key=self.config.chave_openai, timeout=60.0, max_retries=2)
        return self.cliente

    def aquecer(self) -> float:
        return 0.0

    def responder(self, mensagens: list[dict[str, str]]) -> Iterator[str]:
        cliente = self._cliente()
        instrucoes, conversa = separar_sistema(mensagens)
        self.escreveu = False
        if not conversa:
            return
        inicio = time.perf_counter()
        self.medidas = Medidas()
        recusou = False
        try:
            fluxo = cliente.responses.create(
                model=self.modelo,
                instructions=instrucoes,
                input=conversa,
                reasoning={"effort": self.esforco},
                max_output_tokens=self.max_tokens,
                stream=True,
            )
            for evento in fluxo:
                tipo = getattr(evento, "type", "")
                if tipo == "response.output_text.delta" and evento.delta:
                    if not self.medidas.primeiro_pedaco:
                        self.medidas.primeiro_pedaco = time.perf_counter() - inicio
                    self.escreveu = True
                    yield evento.delta
                elif tipo == "response.refusal.delta":
                    recusou = True
                elif tipo in ("response.failed", "error"):
                    raise CerebroIndisponivel(_mensagem_do_evento(evento))
                elif tipo == "response.completed":
                    uso = getattr(getattr(evento, "response", None), "usage", None)
                    self.medidas.tokens = getattr(uso, "output_tokens", 0) or 0
        except CerebroIndisponivel:
            raise
        except Exception as erro:
            raise CerebroIndisponivel(_explicar(erro)) from erro
        self.medidas.total = time.perf_counter() - inicio
        if self.medidas.total:
            self.medidas.tokens_por_segundo = self.medidas.tokens / self.medidas.total
        if not self.escreveu:
            motivo = "recusou a pergunta" if recusou else "não devolveu resposta"
            raise CerebroIndisponivel(f"O ChatGPT {motivo}.", categoria="resposta_vazia")


def _mensagem_do_evento(evento) -> str:
    erro = getattr(evento, "error", None) or getattr(
        getattr(evento, "response", None), "error", None
    )
    detalhe = getattr(erro, "message", None) or getattr(evento, "message", None) or ""
    return f"O ChatGPT falhou: {detalhe}".strip()


def _explicar(erro: Exception) -> str:
    try:
        import openai
    except ImportError:
        return f"Falha no ChatGPT: {erro}"
    if isinstance(erro, openai.AuthenticationError):
        return "A chave do ChatGPT (OPENAI_API_KEY no .env) foi recusada. Confira se está certa."
    if isinstance(erro, openai.PermissionDeniedError):
        return "A chave do ChatGPT não tem permissão para esse modelo."
    if isinstance(erro, openai.NotFoundError):
        return "A OpenAI não achou o modelo pedido: confira [modelos.openai] na config."
    if isinstance(erro, openai.RateLimitError):
        return "O ChatGPT pediu para esperar (limite de uso ou sem créditos)."
    if isinstance(erro, openai.APIStatusError):
        return f"O ChatGPT recusou o pedido ({erro.status_code}): {erro.message}"
    if isinstance(erro, openai.APIConnectionError):
        return "Não consegui falar com o ChatGPT: sem internet?"
    return f"Falha no ChatGPT: {erro}"


def testar_conexao(config: Config) -> str:
    """Checks the key and the heavy model without generating text. "" if it worked."""
    if not config.chave_openai:
        return "falta OPENAI_API_KEY no .env"
    if problema := problema_do_pacote():
        return problema
    import openai

    try:
        cliente = openai.OpenAI(api_key=config.chave_openai, timeout=10.0, max_retries=0)
        cliente.models.retrieve(config.modelo_openai.pesado)
    except Exception as erro:
        return _explicar(erro)
    return ""
