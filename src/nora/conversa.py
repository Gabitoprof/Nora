"""Conversa digitada com a Nora (parte 1 da v0.1.0; a voz entra por cima disto)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime
from typing import TextIO

from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import Config
from nora.curadoria import extrair_fatos
from nora.historico import Historico
from nora.memoria import Fato, Memoria, abrir_memoria
from nora.persona import prompt_de_sistema

COMANDOS_SAIR = {"sair", "tchau", "/sair", "exit", "quit"}
AUTOMATICA = object()


class Conversa:
    """Guarda as mensagens da sessão e pede respostas ao cérebro."""

    def __init__(
        self,
        config: Config,
        cerebro: CerebroLocal,
        historico: Historico,
        memoria: Memoria | None = None,
    ) -> None:
        self.config = config
        self.cerebro = cerebro
        self.historico = historico
        self.memoria = memoria
        self.lembrancas: list[Fato] = []  # fatos usados na última resposta
        self.avisos: list[str] = []
        self._curadorias: list[threading.Thread] = []
        self.limpar()

    def limpar(self) -> None:
        self.mensagens = [{"role": "system", "content": prompt_de_sistema(self.config)}]

    def _avisar(self, aviso: str) -> None:
        if aviso not in self.avisos:
            self.avisos.append(aviso)

    def _lembrar(self, texto: str) -> list[dict[str, str]]:
        """Fatos da memória parecidos com a pergunta, como uma nota para o modelo."""
        self.lembrancas = []
        if self.memoria is None:
            return []
        memoria = self.config.memoria
        try:
            self.lembrancas = self.memoria.buscar(
                texto, memoria.fatos_por_pergunta, memoria.similaridade_minima
            )
        except Exception as erro:  # sem memória a conversa continua
            self._avisar(
                f"Memória indisponível ({erro}). Rode: ollama pull {memoria.modelo_embeddings}"
            )
            return []
        if not self.lembrancas:
            return []
        quem = self.config.nome_usuario or "a pessoa"
        linhas = "\n".join(
            f"- {fato.texto} (anotado em {fato.atualizado[:10]})" for fato in self.lembrancas
        )
        nota = (
            f"O que você lembra de conversas anteriores com {quem} (use só se ajudar a "
            f"responder; não liste isso sem ser pedido):\n{linhas}"
        )
        return [{"role": "system", "content": nota}]

    def _curar(self, pergunta: str, resposta: str) -> None:
        try:
            hoje = datetime.now().strftime("%d/%m/%Y")
            for fato in extrair_fatos(self.config, pergunta, resposta, hoje):
                self.memoria.lembrar(fato, origem=self.historico.sessao)
        except Exception as erro:
            self._avisar(f"Não consegui atualizar a memória ({erro}).")

    def avisos_pendentes(self) -> list[str]:
        """Avisos da memória ainda não mostrados (e os esquece)."""
        avisos, self.avisos = self.avisos, []
        return avisos

    def encerrar(self) -> list[str]:
        """Espera a memória terminar de anotar a conversa; devolve os avisos que sobraram."""
        if any(linha.is_alive() for linha in self._curadorias):
            self.esperar_memoria()
        return self.avisos_pendentes()

    def esperar_memoria(self, timeout: float = 120.0) -> None:
        """Espera as curadorias em andamento (ao sair, para não perder fatos)."""
        for linha in self._curadorias:
            linha.join(timeout)
        self._curadorias = [linha for linha in self._curadorias if linha.is_alive()]

    def perguntar(self, texto: str):
        """Devolve a resposta aos pedaços e guarda pergunta e resposta no histórico."""
        self.mensagens.append({"role": "user", "content": texto})
        self.historico.registrar("usuario", texto)
        envio = self.mensagens[:-1] + self._lembrar(texto) + self.mensagens[-1:]
        partes: list[str] = []
        try:
            for pedaco in self.cerebro.responder(envio):
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
            lembrancas=[fato.id for fato in self.lembrancas],
        )
        if self.memoria is not None and self.config.memoria.curadoria and resposta:
            linha = threading.Thread(target=self._curar, args=(texto, resposta), daemon=True)
            linha.start()
            self._curadorias.append(linha)


def nova_conversa(config: Config, cerebro: CerebroLocal | None = None, memoria=AUTOMATICA):
    """Conversa com o cérebro local, o histórico e (se ligada na config) a memória."""
    if memoria is AUTOMATICA:
        memoria = abrir_memoria(config)
    return Conversa(config, cerebro or CerebroLocal(config), Historico(config.pasta_dados), memoria)


def conversar(
    config: Config,
    entrada: Callable[[str], str] = input,
    saida: TextIO | None = None,
    medir: bool = False,
    cerebro: CerebroLocal | None = None,
) -> int:
    import sys

    saida = saida or sys.stdout
    conversa = nova_conversa(config, cerebro)
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
        for aviso in conversa.avisos_pendentes():
            escrever(f"[memória] {aviso}")
        if medir:
            m = conversa.cerebro.medidas
            escrever(
                f"  [primeira palavra em {m.primeiro_pedaco:.2f} s, total {m.total:.2f} s, "
                f"{m.tokens_por_segundo:.1f} tokens/s, lembrou {len(conversa.lembrancas)} fatos]"
            )
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
