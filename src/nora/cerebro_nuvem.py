"""Cloud brain: Claude (Anthropic API), streaming, for the hard questions.

Takes the same messages as the local brain (persona, memory notes, conversation) and returns the
answer in chunks, the same way: the voice and the screen do not know who answered.
Uses the official `anthropic` SDK ([nuvem] extra) and the ANTHROPIC_API_KEY key from .env.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field

from nora.cerebro import CerebroIndisponivel, Medidas
from nora.config import Config

# Models with server-side refusal handling (`fallbacks: "default"`): if the model refuses for
# safety reasons, the API retries the request on a designated model, within the same call.
_COM_FALLBACK = ("claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")
_BETA_FALLBACK = "server-side-fallback-2026-07-01"
RECUSA = "Desculpe, nisso eu não posso ajudar."


def separar_sistema(mensagens: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    """The API takes the system prompt separately: joins the system messages (persona and notes)
    and leaves only the conversation, starting with a user turn and with no two equal roles
    in a row."""
    sistema = "\n\n".join(m["content"] for m in mensagens if m["role"] == "system")
    conversa: list[dict[str, str]] = []
    for mensagem in mensagens:
        if mensagem["role"] not in ("user", "assistant") or not mensagem["content"].strip():
            continue
        if not conversa and mensagem["role"] != "user":
            continue
        if conversa and conversa[-1]["role"] == mensagem["role"]:
            conversa[-1] = {
                "role": mensagem["role"],
                "content": conversa[-1]["content"] + "\n\n" + mensagem["content"],
            }
        else:
            conversa.append({"role": mensagem["role"], "content": mensagem["content"]})
    return sistema, conversa


def nome_do_modelo(modelo: str) -> str:
    """'claude-sonnet-5-5' -> 'Claude Sonnet 5.5', for notices and --medir."""
    partes = modelo.removeprefix("claude-").split("-")
    nome = " ".join(p.capitalize() for p in partes if not p.isdigit())
    versao = ".".join(p for p in partes if p.isdigit())
    return f"Claude {nome} {versao}".strip()


@dataclass
class CerebroNuvem:
    config: Config
    modelo: str
    esforco: str = "medium"
    max_tokens: int = 8000
    cliente: object = None
    medidas: Medidas = field(default_factory=Medidas)

    @property
    def nome(self) -> str:
        return nome_do_modelo(self.modelo)

    def _cliente(self):
        if self.cliente is not None:
            return self.cliente
        if not self.config.chave_anthropic:
            raise CerebroIndisponivel("Falta ANTHROPIC_API_KEY no .env para usar o Claude.")
        try:
            import anthropic
        except ImportError as erro:
            raise CerebroIndisponivel(
                'O Claude precisa do pacote anthropic: pip install -e ".[nuvem]"'
            ) from erro
        self.cliente = anthropic.Anthropic(
            api_key=self.config.chave_anthropic, timeout=60.0, max_retries=2
        )
        return self.cliente

    def aquecer(self) -> float:
        return 0.0  # nothing to load: the model lives in the cloud

    def _abrir(self, cliente, sistema: str, conversa: list[dict[str, str]]):
        pedido = {
            "model": self.modelo,
            "max_tokens": self.max_tokens,
            "system": sistema,
            "messages": conversa,
            "output_config": {"effort": self.esforco},
        }
        if self.modelo.startswith(_COM_FALLBACK):
            return cliente.beta.messages.stream(
                **pedido, betas=[_BETA_FALLBACK], fallbacks="default"
            )
        return cliente.messages.stream(**pedido)

    def responder(self, mensagens: list[dict[str, str]]) -> Iterator[str]:
        """Sends the conversation to Claude and returns the answer in chunks."""
        cliente = self._cliente()
        sistema, conversa = separar_sistema(mensagens)
        if not conversa:
            return
        inicio = time.perf_counter()
        self.medidas = Medidas()
        escreveu = False
        try:
            with self._abrir(cliente, sistema, conversa) as fluxo:
                for pedaco in fluxo.text_stream:
                    if pedaco:
                        if not self.medidas.primeiro_pedaco:
                            self.medidas.primeiro_pedaco = time.perf_counter() - inicio
                        escreveu = True
                        yield pedaco
                final = fluxo.get_final_message()
        except Exception as erro:
            raise CerebroIndisponivel(_explicar(erro)) from erro
        if getattr(final, "stop_reason", None) == "refusal" and not escreveu:
            yield RECUSA
        uso = getattr(final, "usage", None)
        self.medidas.tokens = getattr(uso, "output_tokens", 0) or 0
        self.medidas.total = time.perf_counter() - inicio
        if self.medidas.total:
            self.medidas.tokens_por_segundo = self.medidas.tokens / self.medidas.total


def problema_do_pacote() -> str:
    """ "" if the Claude SDK loads; otherwise, what is missing or the load error."""
    try:
        import anthropic  # noqa: F401
    except ModuleNotFoundError as erro:
        if erro.name == "anthropic":
            return 'falta o pacote do Claude: python -m pip install -e ".[nuvem]"'
        return f"o pacote do Claude não carregou (falta {erro.name}): {erro}"
    except ImportError as erro:
        return f"o pacote do Claude não carregou: {erro}"
    return ""


def testar_conexao(config: Config) -> str:
    """Checks the key and the heavy model with the models API (generates no text, spends no
    credits). Returns "" if it worked, or the reason for the failure."""
    if not config.chave_anthropic:
        return "falta ANTHROPIC_API_KEY no .env"
    if problema := problema_do_pacote():
        return problema
    import anthropic

    try:
        cliente = anthropic.Anthropic(api_key=config.chave_anthropic, timeout=10.0, max_retries=0)
        cliente.models.retrieve(config.modelo_nuvem.pesado)
    except Exception as erro:
        return _explicar(erro)
    return ""


def _explicar(erro: Exception) -> str:
    """A clear sentence for each type of API failure (the rest of the text stays in the history)."""
    try:
        import anthropic
    except ImportError:
        return f"Falha no Claude: {erro}"
    if isinstance(erro, anthropic.AuthenticationError):
        return "A chave do Claude (ANTHROPIC_API_KEY no .env) foi recusada. Confira se está certa."
    if isinstance(erro, anthropic.PermissionDeniedError):
        return "A chave do Claude não tem permissão para esse modelo."
    if isinstance(erro, anthropic.NotFoundError):
        return "O Claude não achou o modelo pedido: confira [modelos.nuvem] na config."
    if isinstance(erro, anthropic.RateLimitError):
        return "O Claude pediu para esperar (limite de uso). Tente de novo daqui a pouco."
    if isinstance(erro, anthropic.APIStatusError) and erro.status_code in (500, 502, 503, 529):
        return "O Claude está sobrecarregado agora. Tente de novo em instantes."
    if isinstance(erro, anthropic.APIStatusError):
        return f"O Claude recusou o pedido ({erro.status_code}): {erro.message}"
    if isinstance(erro, anthropic.APIConnectionError):
        return "Não consegui falar com o Claude: sem internet?"
    return f"Falha no Claude: {erro}"
