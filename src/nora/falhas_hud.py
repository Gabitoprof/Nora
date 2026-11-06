"""Falhas da HUD (visualização), contadas sem parar a fala.

A HUD nunca pode interromper o áudio: os erros dela são engolidos no caminho acústico. Mas não em
silêncio: cada (lugar, tipo de erro) vira uma linha de log na primeira vez e, depois, só conta.
Nunca registra a mensagem do erro, que pode ter texto da conversa, nem áudio.

Seguro no callback de áudio: sem trava (um contador aproximado basta) e no máximo uma linha de log
por tipo de erro em toda a sessão.
"""

from __future__ import annotations

import logging

log = logging.getLogger("nora.hud")
_contagem: dict[tuple[str, str], int] = {}


def registrar(onde: str, erro: BaseException) -> None:
    """Conta a falha; a primeira de cada tipo, em cada lugar, vira uma linha de log."""
    try:
        chave = (onde, type(erro).__name__)
        vezes = _contagem.get(chave, 0) + 1
        _contagem[chave] = vezes
        if vezes == 1:
            log.warning(
                "HUD: falha em %s (%s); a fala continua. As próximas iguais só são contadas.",
                *chave,
            )
    except Exception:
        pass  # nem o registro pode parar o áudio


def contagem() -> dict[str, int]:
    """{"lugar: TipoDoErro": vezes}, para o diagnóstico e os testes."""
    return {f"{onde}: {tipo}": vezes for (onde, tipo), vezes in dict(_contagem).items()}


def zerar() -> None:
    _contagem.clear()
