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
from nora.memoria import Fato, Memoria, Troca, abrir_memoria
from nora.persona import prompt_de_sistema


def _data(quando: str) -> str:
    """'2026-10-30T10:00:00' -> '30/10/2026'."""
    return f"{quando[8:10]}/{quando[5:7]}/{quando[:4]}" if len(quando) >= 10 else quando


def _resumir(texto: str, limite: int = 300) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


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
        self.trechos: list[Troca] = []  # trechos de conversas antigas usados na última resposta
        self.avisos: list[str] = []
        self._curadorias: list[threading.Thread] = []
        self.limpar()

    def limpar(self) -> None:
        self.mensagens = [{"role": "system", "content": prompt_de_sistema(self.config)}]

    def _avisar(self, aviso: str) -> None:
        if aviso not in self.avisos:
            self.avisos.append(aviso)

    def _lembrar(self, texto: str) -> list[dict[str, str]]:
        """Fatos e trechos de conversas antigas parecidos com a pergunta, como uma nota para o
        modelo (que não fica guardada na conversa)."""
        self.lembrancas, self.trechos = [], []
        if self.memoria is None:
            return []
        memoria = self.config.memoria
        try:
            self.lembrancas = self.memoria.buscar(
                texto, memoria.fatos_por_pergunta, memoria.similaridade_minima
            )
            if memoria.trocas_por_pergunta:
                self.trechos = self.memoria.buscar_trocas(
                    texto,
                    memoria.trocas_por_pergunta,
                    memoria.similaridade_minima,
                    exceto_sessao=self.historico.sessao,
                )
        except Exception as erro:  # sem memória a conversa continua
            modelo = memoria.modelo_embeddings
            self._avisar(f"Memória indisponível ({erro}). Rode: ollama pull {modelo}")
            return []
        if not self.lembrancas and not self.trechos:
            return []
        quem = self.config.nome_usuario or "a pessoa"
        partes = [
            f"O que você lembra de conversas anteriores com {quem} (use só se ajudar a "
            "responder; não liste isso sem ser pedido):"
        ]
        partes += [f"- {f.texto} (anotado em {_data(f.atualizado)})" for f in self.lembrancas]
        if self.trechos:
            partes.append("Trechos dessas conversas:")
            partes += [
                f'- Em {_data(t.quando)}, {quem} disse: "{_resumir(t.pergunta)}" e você '
                f'respondeu: "{_resumir(t.resposta)}"'
                for t in self.trechos
            ]
        return [{"role": "system", "content": "\n".join(partes)}]

    def _memorizar(self, pergunta: str, resposta: str) -> None:
        """Guarda a troca inteira e anota os fatos novos (em segundo plano)."""
        try:
            agora = datetime.now()
            self.memoria.guardar_troca(
                pergunta, resposta, agora.isoformat(timespec="seconds"), self.historico.sessao
            )
            if not self.config.memoria.curadoria:
                return
            for fato in extrair_fatos(self.config, pergunta, resposta, agora.strftime("%d/%m/%Y")):
                _, novo = self.memoria.lembrar(fato, origem=self.historico.sessao)
                self._avisar(f"{'anotei' if novo else 'atualizei'}: {fato}")
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
        if self.memoria is not None and resposta:
            linha = threading.Thread(target=self._memorizar, args=(texto, resposta), daemon=True)
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
                f"{m.tokens_por_segundo:.1f} tokens/s, "
                f"lembrou {len(conversa.lembrancas)} fatos e {len(conversa.trechos)} trechos]"
            )
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
