"""Conversa digitada com a Nora (parte 1 da v0.1.0; a voz entra por cima disto)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TextIO

from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import Config
from nora.historico import Historico
from nora.persona import prompt_de_sistema

COMANDOS_SAIR = {"sair", "tchau", "/sair", "exit", "quit"}


class Conversa:
    """Guarda as mensagens da sessão e pede respostas ao cérebro."""

    def __init__(self, config: Config, cerebro: CerebroLocal, historico: Historico) -> None:
        self.config = config
        self.cerebro = cerebro
        self.historico = historico
        self.limpar()

    def limpar(self) -> None:
        self.mensagens = [{"role": "system", "content": prompt_de_sistema(self.config)}]

    def perguntar(self, texto: str):
        """Devolve a resposta aos pedaços e guarda pergunta e resposta no histórico."""
        self.mensagens.append({"role": "user", "content": texto})
        self.historico.registrar("usuario", texto)
        partes: list[str] = []
        try:
            for pedaco in self.cerebro.responder(self.mensagens):
                partes.append(pedaco)
                yield pedaco
        except CerebroIndisponivel:
            self.mensagens.pop()
            raise
        resposta = "".join(partes).strip()
        self.mensagens.append({"role": "assistant", "content": resposta})
        medidas = self.cerebro.medidas
        self.historico.registrar(
            "assistente",
            resposta,
            modelo=self.config.modelo_local.modelo,
            primeiro_pedaco_s=round(medidas.primeiro_pedaco, 3),
            total_s=round(medidas.total, 3),
        )


def conversar(
    config: Config,
    entrada: Callable[[str], str] = input,
    saida: TextIO | None = None,
    medir: bool = False,
    cerebro: CerebroLocal | None = None,
) -> int:
    import sys

    saida = saida or sys.stdout
    conversa = Conversa(config, cerebro or CerebroLocal(config), Historico(config.pasta_dados))
    nome = config.assistente.nome

    def escrever(texto: str = "", fim: str = "\n") -> None:
        saida.write(texto + fim)
        saida.flush()

    escrever(f"Carregando {config.modelo_local.modelo} na memória...", fim="")
    try:
        escrever(f" pronto em {conversa.cerebro.aquecer():.1f} s.")
    except CerebroIndisponivel as erro:
        escrever(f"\n[erro] {erro}")
    escrever(f"Conversa com {nome}. Digite 'sair' para encerrar e '/limpar' para começar do zero.")
    while True:
        try:
            texto = entrada("\nVocê: ").strip()
        except (EOFError, KeyboardInterrupt):
            escrever()
            break
        if not texto:
            continue
        if texto.lower() in COMANDOS_SAIR:
            break
        if texto == "/limpar":
            conversa.limpar()
            escrever("(conversa reiniciada)")
            continue

        escrever(f"{nome}: ", fim="")
        try:
            for pedaco in conversa.perguntar(texto):
                escrever(pedaco, fim="")
        except CerebroIndisponivel as erro:
            escrever(f"\n[erro] {erro}")
            continue
        except KeyboardInterrupt:
            escrever("\n(interrompido)")
            continue
        escrever()
        if medir:
            m = conversa.cerebro.medidas
            escrever(
                f"  [primeira palavra em {m.primeiro_pedaco:.2f} s, total {m.total:.2f} s, "
                f"{m.tokens_por_segundo:.1f} tokens/s]"
            )
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
