"""Nora: assistente de IA pessoal por voz."""

__version__ = "0.1.0.dev0"


def versao_legivel(versao: str = __version__) -> str:
    """ "0.1.0.dev0" -> "0.1.0 (em desenvolvimento)"; versões lançadas ficam como estão."""
    base, _, extra = versao.partition(".dev")
    return f"{base} (em desenvolvimento)" if extra or versao.endswith(".dev") else versao
