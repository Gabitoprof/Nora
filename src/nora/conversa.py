"""Conversa digitada com a Nora (parte 1 da v0.1.0; a voz entra por cima disto)."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TextIO

from nora.agenda import intervalo_da_pergunta, quando
from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import Config
from nora.curadoria import curar
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

    def _agenda(self, texto: str, hoje: date) -> list[str]:
        """Linhas da agenda para a nota: os próximos dias, o período citado na pergunta e,
        se ela fala de aniversário, os aniversários anotados."""
        dias = self.config.memoria.agenda_dias
        vistos: set[tuple[date, int]] = set()

        def linhas(eventos) -> list[str]:
            novas = []
            for dia, evento in eventos:
                if (dia, evento.id) not in vistos:
                    vistos.add((dia, evento.id))
                    novas.append(f"- {quando(dia, hoje)}: {evento.texto}")
            return novas

        partes = []
        if dias > 0:
            proximos = linhas(self.memoria.agenda(hoje, hoje + timedelta(days=dias - 1)))
            if proximos:
                partes += [f"Agenda dos próximos {dias} dias (hoje incluído):", *proximos]
        periodo = intervalo_da_pergunta(texto, hoje)
        if periodo:
            inicio, fim = periodo
            achados = self.memoria.agenda(inicio, fim)
            novas = linhas(achados)
            nome = f"{inicio:%d/%m/%Y}" + (f" a {fim:%d/%m/%Y}" if fim != inicio else "")
            if novas:
                partes += [f"Na agenda para {nome}:", *novas]
            elif not achados:
                partes.append(f"Não há nada anotado na agenda para {nome}.")
        if "aniversari" in texto.lower().replace("á", "a"):
            aniversarios = [
                (evento.data, evento) for evento in self.memoria.eventos_contendo("anivers")
            ]
            novas = linhas(aniversarios)
            if novas:
                partes += ["Aniversários anotados (a data original):", *novas]
        return partes

    def _preferencias(self) -> list[dict[str, str]]:
        """O que a pessoa pediu sobre o jeito de falar, em toda resposta."""
        try:
            preferencias = self.memoria.preferencias()
        except Exception:
            return []
        if not preferencias:
            return []
        quem = self.config.nome_usuario or "a pessoa"
        linhas = [f"Como {quem} pediu que você fale (siga sempre):"]
        linhas += [f"- {texto}" for _, texto in preferencias[-20:]]
        return [{"role": "system", "content": "\n".join(linhas)}]

    def _lembrar(self, texto: str) -> list[dict[str, str]]:
        """Preferências, fatos e trechos de conversas antigas parecidos com a pergunta, como
        notas para o modelo (que não ficam guardadas na conversa)."""
        self.lembrancas, self.trechos = [], []
        if self.memoria is None:
            return []
        return self._preferencias() + self._lembrancas(texto)

    def _lembrancas(self, texto: str) -> list[dict[str, str]]:
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
        try:
            agenda = self._agenda(texto, date.today())
        except Exception as erro:
            self._avisar(f"Agenda indisponível ({erro}).")
            agenda = []
        if not self.lembrancas and not self.trechos and not agenda:
            return []
        quem = self.config.nome_usuario or "a pessoa"
        partes = [
            f"O que você lembra de conversas anteriores com {quem} (use só se ajudar a "
            "responder; não liste isso sem ser pedido; não acrescente detalhes que não "
            "estejam aqui):"
        ]
        partes += [
            f"- {f'[{f.area}] ' if f.area else ''}{f.texto} (anotado em {_data(f.atualizado)})"
            for f in self.lembrancas
        ]
        partes += agenda
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
            areas = [area for area, _ in self.memoria.areas()]
            hoje = agora.strftime("%d/%m/%Y")
            curadoria = curar(self.config, pergunta, resposta, hoje, areas)
            for palavra, fala in curadoria.pronuncias:
                self.memoria.ensinar_pronuncia(palavra, fala)
                self._avisar(f"aprendi a pronúncia: {palavra} → {fala}")
            for preferencia in curadoria.preferencias:
                _, nova = self.memoria.preferir(preferencia)
                if nova:
                    self._avisar(f"vou lembrar de: {preferencia}")
            for fato in curadoria.fatos:
                fato_id, novo = self.memoria.lembrar(
                    fato.texto, origem=self.historico.sessao, area=fato.area
                )
                area = self.memoria.normalizar_area(fato.area)
                if fato.data:
                    self.memoria.marcar(fato.data, fato.texto, fato.anual, area, fato_id)
                onde = f" em {area}" if area else ""
                na_agenda = f" (agenda: {fato.data:%d/%m/%Y})" if fato.data else ""
                self._avisar(f"{'anotei' if novo else 'atualizei'}{onde}: {fato.texto}{na_agenda}")
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
