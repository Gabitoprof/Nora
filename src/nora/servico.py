"""HTTP requests to the local services (Ollama, whisper-server, Piper)."""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request


class ServicoIndisponivel(Exception):
    """A local service did not answer or refused the request."""


def enviar(nome: str, pedido: urllib.request.Request, timeout: float) -> bytes:
    try:
        with urllib.request.urlopen(pedido, timeout=timeout) as resposta:
            return resposta.read()
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "replace").strip()[:300]
        raise ServicoIndisponivel(f"{nome} recusou o pedido ({erro.code}): {detalhe}") from erro
    except (urllib.error.URLError, OSError) as erro:
        partes = urllib.parse.urlsplit(pedido.full_url)
        endereco = f"{partes.scheme}://{partes.netloc}"
        motivo = getattr(erro, "reason", erro)
        local = partes.hostname in {"127.0.0.1", "localhost", "::1"}
        dica = "Ele está aberto?" if local else "Confira a internet."
        raise ServicoIndisponivel(
            f"Não consegui falar com {nome} em {endereco} ({motivo}). {dica}"
        ) from erro


def responde(url: str, timeout: float = 2.0) -> bool:
    """True if some HTTP server is listening at `url` (any status will do)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False
