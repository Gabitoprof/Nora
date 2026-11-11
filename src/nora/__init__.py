"""Nora: personal voice AI assistant."""

__version__ = "0.3.0"


def versao_legivel(versao: str = __version__) -> str:
    """ "0.1.0.dev0" -> "0.1.0 (em desenvolvimento)"; released versions stay as they are."""
    base, _, extra = versao.partition(".dev")
    return f"{base} (em desenvolvimento)" if extra or versao.endswith(".dev") else versao
