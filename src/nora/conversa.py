"""Conversa digitada com a Nora (parte 1 da v0.1.0; a voz entra por cima disto)."""

from __future__ import annotations

import re
import threading
import unicodedata
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import TextIO

from nora.agenda import contas_de_data, intervalo_da_pergunta, quando
from nora.cerebro import CerebroIndisponivel, CerebroLocal
from nora.config import Config
from nora.confirmacao import confirmacao
from nora.curadoria import curar
from nora.emocao import FiltroDeTela, sem_emocoes, tom_predominante
from nora.historico import Historico, apagar_do_historico
from nora.melhorias import Melhorias, abrir_melhorias, ler_entrada
from nora.melhorias import iniciar as iniciar_melhorias
from nora.memoria import MAX_TENTATIVAS, Fato, Memoria, Pendente, Troca, abrir_memoria
from nora.notas import IndiceDeNotas, Trecho, abrir_notas
from nora.observador import Observador, abrir_observador
from nora.persona import prompt_de_sistema
from nora.roteador import Roteador, insatisfeito


def _data(quando: str) -> str:
    """'2026-10-30T10:00:00' -> '30/10/2026'."""
    return f"{quando[8:10]}/{quando[5:7]}/{quando[:4]}" if len(quando) >= 10 else quando


def _resumir(texto: str, limite: int = 300) -> str:
    texto = " ".join(texto.split())
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


COMANDOS_SAIR = {"sair", "tchau", "/sair", "exit", "quit"}

# "Apaga de vez X": apaga da memória e do histórico, mas só depois de a pessoa confirmar.
_APAGAR = r"\b(apaga|apague|apagar|exclui|exclua|excluir|deleta|delete|deletar|remove|remova)\b"
_DE_VEZ = r"\b(de vez|para sempre|pra sempre|definitivamente|completamente)\b"
_TUDO_SOBRE = r"\btudo (sobre|de|do|da|dos|das)\b"
_SEM_ASSUNTO = {
    "",
    "isso",
    "isto",
    "isso ai",
    "isso tudo",
    "tudo",
    "essa informacao",
    "esse assunto",
}


def _sem_acento(texto: str) -> str:
    sem = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem if not unicodedata.combining(c))


def pedido_de_apagar(texto: str) -> str | None:
    """O assunto de um "apaga de vez ...", "" se não disse qual, ou None se não é esse pedido.
    "Esquece isso" (sem "de vez") é só esquecer: quem cuida é a curadoria."""
    if not re.search(_APAGAR, texto, re.I):
        return None
    if not (re.search(_DE_VEZ, texto, re.I) or re.search(_TUDO_SOBRE, texto, re.I)):
        return None
    assunto = texto
    for padrao in (_APAGAR, _DE_VEZ, _TUDO_SOBRE, r"\bda (sua )?mem[oó]ria\b", r"\bnora\b"):
        assunto = re.sub(padrao, " ", assunto, flags=re.I)
    assunto = re.sub(r"\bpor favor\b", " ", assunto, flags=re.I)
    assunto = " ".join(re.sub(r"[,.!?;:]", " ", assunto).split())
    return "" if _sem_acento(assunto) in _SEM_ASSUNTO else assunto


_NUMEROS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}


def pedido_de_melhoria(texto: str) -> tuple[str, int] | None:
    """("listar", 0) ou ("aprovar" | "recusar" | "adiar", nº). Só com a palavra "melhoria" e,
    para decidir, um número claro: nada de adivinhar qual proposta."""
    limpo = " ".join(re.sub(r"[^\w\s]", " ", _sem_acento(texto)).split())
    if not re.search(r"\bmelhorias?\b", limpo):
        return None
    acao = re.search(r"\b(aprov|recus|adi)(a|e|ar|o)\b", limpo)
    if acao:
        nome = {"aprov": "aprovar", "recus": "recusar", "adi": "adiar"}[acao.group(1)]
        numero = re.search(r"\bmelhorias? (?:numero |n |no )?(\d+|\w+)\b", limpo)
        if not numero:
            return nome, 0
        valor = numero.group(1)
        return nome, int(valor) if valor.isdigit() else _NUMEROS.get(valor, 0)
    if re.search(
        r"\b(quais|que|tem|lista|listar|fala|diz|le|relatorio|sugeriu|sugestoes)\b", limpo
    ):
        return "listar", 0
    return None


def pede_retomada(texto: str) -> bool:
    """ "Termina a resposta que ficou pela metade", "continua aquela resposta"..."""
    limpo = _sem_acento(texto)
    return bool(
        re.search(
            r"\b(termin|continu|retom|complet|refa|repet)\w*\b.{0,40}\b(resposta|pergunta)", limpo
        )
        and re.search(
            r"metade|interromp|anterior|aquela|pendente|ficou|parou|caiu|cortou|incomplet", limpo
        )
    )


_MOTIVOS = {"interrompida": "stream_interrompido", "sem resposta": "sem_resposta"}


def _contagem(fatos: int, trechos: int) -> str:
    partes = []
    if fatos:
        partes.append(f"{fatos} fato{'s' if fatos > 1 else ''}")
    if trechos:
        partes.append(f"{trechos} trecho{'s' if trechos > 1 else ''} de conversa")
    return " e ".join(partes)


AUTOMATICA = object()


class Conversa:
    """Guarda as mensagens da sessão e pede respostas ao cérebro."""

    def __init__(
        self,
        config: Config,
        cerebro: CerebroLocal,
        historico: Historico,
        memoria: Memoria | None = None,
        notas: IndiceDeNotas | None = None,
        observador: Observador | None = None,
        melhorias: Melhorias | None = None,
    ) -> None:
        self.config = config
        self.cerebro = cerebro
        self.historico = historico
        self.memoria = memoria
        self.notas = notas
        self.observador = observador
        self.melhorias = melhorias
        self.ocupada = False  # respondendo agora: a auto-melhoria espera
        self.falando = False  # a voz ainda está tocando a resposta: o Second Brain espera
        self.segundo_cerebro = None  # o sincronizador das notas, se ligado ([segundo_cerebro])
        self._melhoria_pendente: tuple[str, int] | None = None  # (ação, nº) esperando o "sim"
        self.ultima_interacao = ""  # para a voz anotar os tempos dela na mesma interação
        self._anterior: tuple[str, str] = ("", "")  # (interação, quem respondeu), p/ reclamações
        self.trechos_de_notas: list[Trecho] = []  # trechos das notas usados na última resposta
        self.lembrancas: list[Fato] = []  # fatos usados na última resposta
        self.trechos: list[Troca] = []  # trechos de conversas antigas usados na última resposta
        self.avisos: list[str] = []
        self._curadorias: list[threading.Thread] = []
        self._apagar_pendente: tuple[str, set[str]] | None = None  # esperando o "sim"
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
        self.lembrancas, self.trechos, self.trechos_de_notas = [], [], []
        notas = self._notas(texto) + self._contas_de_data(texto)
        if self.memoria is None:
            return notas
        return self._preferencias() + self._lembrancas(texto) + notas

    def _contas_de_data(self, texto: str) -> list[dict[str, str]]:
        """As contas de data da pergunta, feitas pelo código: o modelo erra "daqui a 23 dias"."""
        anteriores = [m["content"] for m in self.mensagens[:-1] if m["role"] == "user"]
        try:
            linhas = contas_de_data(texto, date.today(), anteriores)
        except Exception:
            return []
        if not linhas:
            return []
        cabecalho = (
            "Contas de data já feitas pelo sistema (estão certas: use estes resultados, não "
            "refaça a conta):"
        )
        return [{"role": "system", "content": "\n".join([cabecalho, *linhas])}]

    def _notas(self, texto: str) -> list[dict[str, str]]:
        """Os trechos das notas do Obsidian parecidos com a pergunta."""
        if self.notas is None:
            return []
        config = self.config.notas
        try:
            self.trechos_de_notas = self.notas.buscar(
                texto, config.trechos_por_pergunta, config.similaridade_minima
            )
        except Exception as erro:  # sem as notas a conversa continua
            self._avisar(f"Notas indisponíveis ({erro}).")
            return []
        if not self.trechos_de_notas:
            return []
        quem = self.config.nome_usuario or "a pessoa"
        partes = [
            f"Trechos das notas que {quem} escreveu no Obsidian, parecidos com a pergunta (use "
            "só se ajudar; quando usar, diga de qual nota veio; não invente o que não estiver "
            "aqui):"
        ]
        partes += [f'- Nota "{t.titulo}": {_resumir(t.texto, 700)}' for t in self.trechos_de_notas]
        return [{"role": "system", "content": "\n".join(partes)}]

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

    def _memorizar(self, pergunta: str, resposta: str, anterior: str = "", tom: str = "") -> None:
        """Guarda a troca inteira e anota os fatos novos (em segundo plano). Ao terminar, avisa
        o Second Brain (sem esperar): as notas do Obsidian são escritas depois, por ele."""
        try:
            agora = datetime.now()
            self.memoria.guardar_troca(
                pergunta, resposta, agora.isoformat(timespec="seconds"), self.historico.sessao
            )
            if not self.config.memoria.curadoria:
                return
            areas = [area for area, _ in self.memoria.areas()]
            hoje = agora.strftime("%d/%m/%Y")
            curadoria = curar(self.config, pergunta, resposta, hoje, areas, anterior=anterior)
            for palavra, fala in curadoria.pronuncias:
                self.memoria.ensinar_pronuncia(palavra, fala)
                self._avisar(f"aprendi a pronúncia: {palavra} → {fala}")
            for preferencia in curadoria.preferencias:
                _, nova = self.memoria.preferir(preferencia)
                if nova:
                    self._avisar(f"vou lembrar de: {preferencia}")
            for texto in curadoria.esquecer:  # antes dos fatos novos: numa correção, sai o errado
                apagados = self.memoria.esquecer_parecido(texto)
                for apagado in apagados:
                    self._avisar(f"esqueci: {apagado.texto}")
                if not apagados:
                    self._avisar(f"não vou mais usar: {texto}")
                alvo = apagados[0].texto if apagados else texto
                self._avisar(
                    "a conversa continua guardada no histórico; para apagar de lá também: "
                    f'nora memoria apagar "{alvo}"'
                )
            for fato in curadoria.fatos:
                fato_id, novo = self.memoria.lembrar(
                    fato.texto, origem=self.historico.sessao, area=fato.area, emocao=tom
                )
                area = self.memoria.normalizar_area(fato.area)
                if fato.data:
                    self.memoria.marcar(fato.data, fato.texto, fato.anual, area, fato_id)
                onde = f" em {area}" if area else ""
                na_agenda = f" (agenda: {fato.data:%d/%m/%Y})" if fato.data else ""
                self._avisar(f"{'anotei' if novo else 'atualizei'}{onde}: {fato.texto}{na_agenda}")
        except Exception as erro:
            self._avisar(f"Não consegui atualizar a memória ({erro}).")
        finally:
            self.avisar_segundo_cerebro()

    def avisar_segundo_cerebro(self) -> None:
        """A memória mudou: o Second Brain sincroniza quando a Nora estiver livre. Só levanta um
        sinal; nunca escreve notas nem espera nada aqui."""
        if self.segundo_cerebro is not None:
            self.segundo_cerebro.avisar()

    def atualizar_notas(self) -> None:
        try:
            resumo = self.notas.atualizar()
        except Exception as erro:
            self._avisar(f"Não consegui ler as notas do Obsidian ({erro}).")
            return
        if resumo.lidas or resumo.removidas:
            self._avisar(
                f"Notas: li {resumo.lidas} nota(s) nova(s) ou alterada(s)"
                f"{f' e esqueci {resumo.removidas} apagada(s)' if resumo.removidas else ''}; "
                f"{resumo.notas} notas no índice."
            )

    def avisos_do_cerebro(self) -> list[str]:
        """Avisos do roteador (quem respondeu na falta de quem) ainda não mostrados."""
        pegar = getattr(self.cerebro, "avisos_pendentes", None)
        return pegar() if pegar else []

    @property
    def origem(self) -> str:
        """Quem respondeu por último: o cérebro local ou um modelo do Claude."""
        return getattr(self.cerebro, "origem", "") or self.config.modelo_local.modelo

    def avisos_pendentes(self) -> list[str]:
        """Avisos da memória ainda não mostrados (e os esquece)."""
        avisos, self.avisos = self.avisos, []
        return avisos

    def encerrar(self) -> list[str]:
        """Espera a memória terminar de anotar a conversa; devolve os avisos que sobraram."""
        if any(linha.is_alive() for linha in self._curadorias):
            self.esperar_memoria()
        if self.segundo_cerebro is not None:  # última sincronização, já fora da conversa
            self.segundo_cerebro.encerrar()
            self.segundo_cerebro = None
        return self.avisos_pendentes()

    def esperar_memoria(self, timeout: float = 120.0) -> None:
        """Espera as curadorias em andamento (ao sair, para não perder fatos)."""
        for linha in self._curadorias:
            linha.join(timeout)
        self._curadorias = [linha for linha in self._curadorias if linha.is_alive()]

    def _responder_comando(self, texto: str, resposta: str) -> str:
        """Guarda na conversa e no histórico uma resposta que não passou pelo cérebro."""
        self.mensagens += [
            {"role": "user", "content": texto},
            {"role": "assistant", "content": resposta},
        ]
        self.historico.registrar("usuario", texto)
        self.historico.registrar("assistente", resposta, modelo="comando de memória")
        return resposta

    def _apagar_pela_conversa(self, texto: str) -> str | None:
        """ "Apaga de vez X": mostra o que sairia e espera o "sim". A resposta, ou None se a fala
        não tem nada a ver com isso."""
        pendente, self._apagar_pendente = self._apagar_pendente, None
        if pendente:
            resposta = confirmacao(texto)
            if resposta == "sim":
                return self._apagar_confirmado(texto, *pendente)
            if resposta == "nao":
                return self._responder_comando(texto, "Tudo bem, não apaguei nada.")
            self._avisar("o pedido de apagar de vez foi cancelado (você mudou de assunto).")
        assunto = pedido_de_apagar(texto)
        if assunto is None:
            return None
        if self.memoria is None:
            return self._responder_comando(
                texto, "A memória está desligada, então não tenho nada guardado para apagar."
            )
        if not assunto:
            return self._responder_comando(
                texto,
                'Apagar de vez o quê? Diga o assunto, por exemplo: "apaga de vez a prova '
                'de cálculo".',
            )
        previa = self.memoria.apagar_de_vez(assunto, confirmar=False)
        if not previa.fatos and not previa.trocas:
            return self._responder_comando(texto, f"Não achei nada sobre {assunto} na memória.")
        for fato in previa.fatos:
            self._avisar(f"apagaria o fato: {fato.texto}")
        for troca in previa.trocas:
            self._avisar(
                f"apagaria a conversa de {_data(troca.quando)}: {_resumir(troca.pergunta, 80)}"
            )
        resposta = (
            f"Isso apagaria {_contagem(len(previa.fatos), len(previa.trocas))} sobre {assunto}, "
            "também do histórico das conversas, e não tem volta. Confirma? Diga "
            '"sim, pode apagar".'
        )
        self._apagar_pendente = (assunto, {texto, resposta})
        return self._responder_comando(texto, resposta)

    def _apagar_confirmado(self, texto: str, assunto: str, falas_do_pedido: set[str]) -> str:
        feito = self.memoria.apagar_de_vez(assunto, confirmar=True)
        # o próprio pedido também cita o assunto: sai do histórico junto
        apagar_do_historico(self.config.pasta_dados, feito.textos | falas_do_pedido)
        quanto = _contagem(len(feito.fatos), len(feito.trocas)) or "o que restava"
        self.avisar_segundo_cerebro()  # a nota sai do vault na próxima rodada
        return self._responder_comando(texto, f"Pronto, apaguei de vez {quanto}.")

    def perguntar(self, texto: str):
        """Devolve a resposta aos pedaços e guarda pergunta e resposta no histórico."""
        comando = self._apagar_pela_conversa(texto)
        if comando is not None:
            yield comando
            return
        comando = self._melhorias_pela_conversa(texto)
        if comando is not None:
            yield comando
            return
        comando = self._mapa_pela_conversa(texto)
        if comando is not None:
            yield comando
            return
        self.ocupada = True  # respondendo ou retomando: a auto-melhoria espera
        try:
            if pede_retomada(texto):
                yield from self._retomar(texto)
            else:
                yield from self._responder(texto)
        finally:
            self.ocupada = False

    def _mapa_pela_conversa(self, texto: str) -> str | None:
        """ "Mostre seu segundo cérebro", "abra o mapa da memória": abre o mapa já pronto (não
        recalcula nada) no navegador. A resposta, ou None se a fala não é esse pedido."""
        if not pede_o_mapa(texto):
            return None
        from nora.melhorias import abrir_arquivo
        from nora.segundo_cerebro import caminho_do_mapa

        if not self.config.segundo_cerebro.ativo:
            resposta = (
                "O segundo cérebro está desligado. Para ligar, ponha ativo = true em "
                "[segundo_cerebro] no config/local.toml (veja docs/SEGUNDO_CEREBRO.md)."
            )
        elif not caminho_do_mapa(self.config).exists():
            self.avisar_segundo_cerebro()
            resposta = (
                "O mapa ainda não ficou pronto: eu monto quando estiver livre. "
                "Pede de novo daqui a pouco."
            )
        elif abrir_arquivo(caminho_do_mapa(self.config), na_frente=True):
            resposta = "Abrindo o mapa da minha memória."
        else:
            resposta = f"Não consegui abrir o mapa. Ele está em {caminho_do_mapa(self.config)}."
        return self._responder_comando(texto, resposta)

    def _melhorias_pela_conversa(self, texto: str) -> str | None:
        """ "Quais melhorias você sugeriu?" e "aprova/recusa/adia a melhoria 3" (com "sim")."""
        if self.melhorias is None:
            return None
        pendente, self._melhoria_pendente = self._melhoria_pendente, None
        if pendente:
            resposta = confirmacao(texto)
            if resposta == "sim":
                acao, numero = pendente
                feita = self.melhorias.decidir(numero, acao, "usuário (pela conversa)")
                frase = {"aprovar": "aprovada", "recusar": "recusada", "adiar": "adiada"}[acao]
                fim = (
                    " Gerei a tarefa para desenvolver; nada muda no código sem você."
                    if acao == "aprovar"
                    else ""
                )
                return self._responder_comando(
                    texto,
                    f"Pronto, a melhoria {numero} foi {frase}.{fim}"
                    if feita
                    else f"A melhoria {numero} não está mais esperando decisão.",
                )
            if resposta == "nao":
                return self._responder_comando(texto, "Tudo bem, não mudei nada.")
        pedido = pedido_de_melhoria(texto)
        if pedido is None:
            return None
        acao, numero = pedido
        if acao == "listar":
            abertas = self.melhorias.propostas(("proposta",))
            if not abertas:
                return self._responder_comando(
                    texto, "Não tenho sugestões de melhoria esperando decisão."
                )
            itens = "; ".join(f"número {p.id}, {p.titulo}" for p in abertas[:5])
            return self._responder_comando(
                texto,
                f"Tenho {len(abertas)} sugestão(ões): {itens}. Para decidir, diga por exemplo "
                f'"aprova a melhoria {abertas[0].id}". O relatório completo: nora melhorias '
                "relatorio.",
            )
        proposta = self.melhorias.proposta(numero) if numero else None
        if proposta is None or proposta.status != "proposta":
            return self._responder_comando(
                texto,
                f'Não achei a melhoria {numero} esperando decisão. Diga "quais melhorias você '
                'sugeriu?" para ouvir os números.',
            )
        self._melhoria_pendente = (acao, numero)
        verbo = {"aprovar": "Aprovar", "recusar": "Recusar", "adiar": "Adiar por uma semana"}[acao]
        return self._responder_comando(
            texto, f'{verbo} a melhoria {numero}, "{proposta.titulo}"? Diga "sim" para confirmar.'
        )

    def _retomar(self, texto: str):
        """Responde de novo, inteira, a última pergunta que ficou pela metade."""
        try:
            pendentes = self.memoria.pendentes() if self.memoria is not None else []
        except Exception:
            pendentes = []
        if not pendentes:
            yield self._responder_comando(
                texto, "Não tenho nenhuma resposta pela metade para terminar."
            )
            return
        pendente = pendentes[0]
        tentativas = self.memoria.tentar_pendencia(pendente.id)
        # uma resposta nova e identificada, não um complemento do pedaço que já saiu
        yield f'Retomando a pergunta "{_resumir(pendente.pergunta, 80)}": '
        yield from self._responder(pendente.pergunta, retomada=(pendente, tentativas))

    def _pendencia(self, interacao, pergunta, parcial, motivo, retomada) -> None:
        """Guarda a resposta que não terminou, para retomar depois (nunca como fato)."""
        if self.memoria is None:
            return
        try:
            if retomada and retomada[1] >= MAX_TENTATIVAS:
                self._avisar(
                    f"tentei {retomada[1]} vezes e a resposta não saiu inteira; desisti dessa "
                    "pendência (pergunte de novo quando quiser)."
                )
                return
            sessao = retomada[0].sessao if retomada else self.historico.sessao
            self.memoria.marcar_pendente(
                interacao, sessao, pergunta, sem_emocoes(parcial), motivo, self.origem
            )
            self._avisar(
                'a resposta ficou pela metade; para terminar: "termina a resposta que ficou '
                'pela metade".'
            )
        except Exception as erro:
            self._avisar(f"Não consegui guardar a resposta pela metade ({erro}).")

    def _oferecer_retomada_do_jogo(self) -> None:
        """Saiu do modo jogo: se alguma pergunta ficou sem resposta lá, oferece retomar (só
        oferece; nada roda sozinho)."""
        if self.memoria is None:
            return
        try:
            sem_resposta = [p for p in self.memoria.pendentes() if p.motivo == "sem_resposta"]
        except Exception:
            return
        if sem_resposta:
            self._avisar(
                f"{len(sem_resposta)} pergunta(s) ficaram sem resposta no modo jogo. Para "
                'responder a última agora: "termina a resposta que ficou pela metade".'
            )

    def _observar(self, interacao: str, texto: str, situacao: str) -> None:
        """Anota para a auto-melhoria como foi a resposta: cada cérebro tentado, comandos e
        reclamações (só categorias e tempos; o texto da conversa não vai para lá)."""
        self.ultima_interacao = interacao
        anterior, quem_antes = self._anterior
        self._anterior = (interacao, self.origem)
        if self.observador is None:
            return
        registrar = self.observador.registrar
        jogo = bool(getattr(self.cerebro, "jogo", False))
        tentativas = getattr(self.cerebro, "tentativas", None)
        if tentativas is None:  # um cérebro só (sem roteador)
            medidas = self.cerebro.medidas
            tentativas = [
                {
                    "motor": self.origem,
                    "resultado": "resposta" if situacao == "completa" else situacao,
                    "duracao_ms": int(medidas.primeiro_pedaco * 1000),
                }
            ]
        for numero, tentativa in enumerate(tentativas, start=1):
            registrar(
                "llm",
                tentativa["resultado"],
                tentativa["motor"],
                interacao,
                tentativa["duracao_ms"],
                situacao,
                numero,
                jogo,
            )
        if situacao in ("sem resposta", "sem_resposta", "cancelada"):
            tipo = situacao.replace(" ", "_")
            registrar("llm", tipo, self.origem, interacao, status=situacao, modo_jogo=jogo)
        if situacao == "comando":
            registrar("roteador", "comando", interacao=interacao, modo_jogo=jogo)
        if anterior and insatisfeito(texto):  # "tá errado", "não entendi": sobre a anterior
            registrar(
                "llm",
                "feedback_negativo",
                quem_antes,
                interacao,
                correlacao=anterior,
                gravidade="aviso",
                modo_jogo=jogo,
            )
            if quem_antes.startswith("local"):  # o local respondeu algo que precisava de mais
                registrar(
                    "roteador",
                    "rota_suspeita",
                    quem_antes,
                    interacao,
                    correlacao=anterior,
                    gravidade="aviso",
                    modo_jogo=jogo,
                )

    def _responder(self, texto: str, retomada: tuple[Pendente, int] | None = None):
        # a resposta anterior (com as etiquetas de emoção) mostra a que tom a pessoa reage agora
        anterior = next(
            (m["content"] for m in reversed(self.mensagens) if m["role"] == "assistant"), ""
        )
        interacao = retomada[0].interacao if retomada else uuid.uuid4().hex
        jogo_antes = bool(getattr(self.cerebro, "jogo", False))
        self.mensagens.append({"role": "user", "content": texto})
        self.historico.registrar(
            "usuario", texto, **({"retomada": retomada[0].id} if retomada else {})
        )
        if self.memoria is not None and not retomada:
            try:  # se o programa cair no meio, ela vira pendência na próxima vez
                self.memoria.abrir_resposta(interacao, self.historico.sessao, texto)
            except Exception:
                pass
        envio = self.mensagens[:-1] + self._lembrar(texto) + self.mensagens[-1:]
        partes: list[str] = []
        try:
            for pedaco in self.cerebro.responder(envio):
                partes.append(pedaco)
                yield pedaco
        except CerebroIndisponivel:
            self.mensagens.pop()
            motivo = "erro_provedor" if partes else "sem_resposta"
            self._pendencia(interacao, texto, "".join(partes), motivo, retomada)
            self._observar(interacao, texto, "sem_resposta")
            raise
        except (GeneratorExit, KeyboardInterrupt):
            # Ctrl+C: chega aqui como KeyboardInterrupt se ela estava esperando o cérebro, ou
            # como GeneratorExit se estava falando (quem lê o gerador o fecha). Depois disto o
            # gerador acabou, então a pendência é gravada uma vez só.
            self._observar(interacao, texto, "cancelada")
            parcial = sem_emocoes("".join(partes).strip())
            self.historico.registrar(
                "assistente", parcial, modelo=self.origem, situacao="cancelada"
            )
            self._pendencia(interacao, texto, parcial, "cancelada", retomada)
            raise
        # A resposta crua tem as etiquetas de emoção ({alegre}...), que só a voz usa: a conversa
        # guarda a crua (o modelo segue o próprio jeito), o histórico e a memória, a limpa.
        crua = "".join(partes).strip()
        resposta = sem_emocoes(crua)
        self.mensagens.append({"role": "assistant", "content": crua})
        medidas = self.cerebro.medidas
        # interrompida (parou no meio) ou sem resposta: fica marcada no histórico e não vai para
        # a memória, para uma resposta pela metade não virar fato
        situacao = getattr(self.cerebro, "situacao", "completa")
        self.historico.registrar(
            "assistente",
            resposta,
            modelo=self.origem,
            primeiro_pedaco_s=round(medidas.primeiro_pedaco, 3),
            total_s=round(medidas.total, 3),
            lembrancas=[fato.id for fato in self.lembrancas],
            **({} if situacao == "completa" else {"situacao": situacao}),
        )
        self._observar(interacao, texto, situacao)
        if jogo_antes and not getattr(self.cerebro, "jogo", False):
            self._oferecer_retomada_do_jogo()
        if self.memoria is not None:
            try:
                if situacao in _MOTIVOS:
                    self._pendencia(interacao, texto, resposta, _MOTIVOS[situacao], retomada)
                elif retomada:
                    self.memoria.resolver_pendencia(retomada[0].id, interacao)
                else:
                    self.memoria.concluir_resposta(interacao)
            except Exception as erro:
                self._avisar(f"Não consegui atualizar as respostas pendentes ({erro}).")
        if self.memoria is not None and resposta and situacao == "completa":
            linha = threading.Thread(
                target=self._memorizar,
                args=(texto, resposta, anterior, tom_predominante(crua)),
                daemon=True,
            )
            linha.start()
            self._curadorias.append(linha)


_PEDE_MAPA = re.compile(
    r"\b(mostr\w*|abr[ea]\w*|abrir|visualiz\w*|ver|veja|exib\w*)\b.{0,30}"
    r"\b(segundo cerebro|second brain|mapa da (sua )?memoria|suas conexoes|"
    r"sua rede neural|rede neural da memoria)\b"
)


def pede_o_mapa(texto: str) -> bool:
    """Se a fala pede para ver o Second Brain (e não pergunta o que ele é)."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    limpo = " ".join("".join(c for c in sem_acento if not unicodedata.combining(c)).split())
    return bool(_PEDE_MAPA.search(limpo))


def nova_conversa(
    config: Config,
    cerebro: CerebroLocal | None = None,
    memoria=AUTOMATICA,
    notas=AUTOMATICA,
    observador=AUTOMATICA,
):
    """Conversa com o cérebro local, o histórico e (se ligadas na config) a memória e as notas.
    As notas novas ou alteradas são lidas em segundo plano, sem atrasar o começo."""
    if memoria is AUTOMATICA:
        memoria = abrir_memoria(config)
    if notas is AUTOMATICA:
        notas = abrir_notas(config)
    if observador is AUTOMATICA:
        observador = abrir_observador(config)
    melhorias = abrir_melhorias(config, observador) if observador is not None else None
    conversa = Conversa(
        config,
        cerebro or Roteador(config),
        Historico(config.pasta_dados),
        memoria,
        notas,
        observador,
        melhorias,
    )
    if memoria is not None:
        try:  # respostas que caíram com o programa da última vez viram pendências
            memoria.recuperar_abertas(exceto_sessao=conversa.historico.sessao)
            quantas = len(memoria.pendentes())
            if quantas:
                conversa._avisar(
                    f"{quantas} resposta(s) ficaram pela metade. Para terminar a última, diga "
                    '"termina a resposta que ficou pela metade"; para ver todas: nora pendencias.'
                )
        except Exception:
            pass
    if notas is not None and config.notas.atualizar_ao_abrir:
        threading.Thread(target=conversa.atualizar_notas, daemon=True).start()
    if config.segundo_cerebro.ativo:
        from nora.segundo_cerebro import iniciar as iniciar_segundo_cerebro

        iniciar_segundo_cerebro(conversa)
    return conversa


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
    for aviso in conversa.avisos_pendentes():  # ao abrir: respostas pela metade, por exemplo
        escrever(f"[memória] {aviso}")
    agendador = iniciar_melhorias(conversa, escrever)
    while True:
        try:
            texto = ler_entrada(
                entrada, "\nVocê: ", agendador, lambda p: escrever(p, fim="")
            ).strip()
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
        from nora.troca_voz import pedido_de_voz

        if pedido_de_voz(texto):  # sem isso, o cérebro diria que trocou sem trocar nada
            escrever(
                f"{nome}: Aqui eu só escrevo, sem voz. Para trocar a voz, converse comigo por "
                "voz (nora ouvir ou nora conversar --voz) e peça lá."
            )
            continue

        escrever(f"{nome}: ", fim="")
        tela = FiltroDeTela()  # as etiquetas de emoção ({alegre}...) não aparecem
        try:
            for pedaco in conversa.perguntar(texto):
                escrever(tela.alimentar(pedaco), fim="")
            escrever(tela.finalizar(), fim="")
        except CerebroIndisponivel as erro:
            escrever(f"\n[erro] {erro}")
            continue
        except KeyboardInterrupt:
            escrever("\n(interrompido)")
            continue
        escrever()
        for aviso in conversa.avisos_do_cerebro():
            escrever(f"[cérebro] {aviso}")
        for aviso in conversa.avisos_pendentes():
            escrever(f"[memória] {aviso}")
        if medir:
            m = conversa.cerebro.medidas
            escrever(
                f"  [{conversa.origem}: primeira palavra em {m.primeiro_pedaco:.2f} s, "
                f"total {m.total:.2f} s, "
                f"{m.tokens_por_segundo:.1f} tokens/s, "
                f"lembrou {len(conversa.lembrancas)} fatos, {len(conversa.trechos)} trechos "
                f"e {len(conversa.trechos_de_notas)} notas]"
            )
    if conversa.memoria is not None:
        escrever("(guardando o que aprendi nesta conversa...)")
    for aviso in conversa.encerrar():
        escrever(f"[memória] {aviso}")
    if agendador is not None:
        agendador.parar()
    escrever(f"Até mais! (conversa salva em {conversa.historico.arquivo})")
    return 0
