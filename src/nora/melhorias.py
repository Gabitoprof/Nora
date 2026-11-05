"""Auto-melhoria supervisionada (MVP): uma vez por dia, a Nora junta o que o observador anotou,
agrupa por causa provável, transforma o que se repetiu em propostas e salva um relatório em
<dados>/auto_melhoria/relatorios/AAAA-MM-DD.md. Ela só propõe: cada proposta espera a decisão da
pessoa (aprovar, recusar ou adiar). Aprovar gera uma tarefa para desenvolver; nada muda no
código, nada é instalado nem publicado sozinho.

Nesta versão o diagnóstico é por regras (sem modelo e sem internet): é leve, não usa a placa de
vídeo e não manda nada para fora do PC. A pesquisa na web (etapa P3) ainda não existe.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import re
import sqlite3
import statistics
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from nora import __version__
from nora.observador import Observador, caminho_do_banco

ESQUEMA = """
CREATE TABLE IF NOT EXISTS propostas (
    id INTEGER PRIMARY KEY,
    chave TEXT NOT NULL UNIQUE,
    criada TEXT NOT NULL,
    atualizada TEXT NOT NULL,
    categoria TEXT NOT NULL,
    titulo TEXT NOT NULL,
    dados TEXT NOT NULL,
    status TEXT NOT NULL,
    contagem_na_decisao INTEGER NOT NULL DEFAULT 0,
    versao_na_decisao TEXT NOT NULL DEFAULT '',
    adiada_ate TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS decisoes (
    id INTEGER PRIMARY KEY,
    proposta_id INTEGER NOT NULL,
    quando TEXT NOT NULL,
    acao TEXT NOT NULL,
    quem TEXT NOT NULL,
    motivo TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS fechamentos (
    data TEXT PRIMARY KEY,
    inicio TEXT NOT NULL,
    fim TEXT NOT NULL,
    criado TEXT NOT NULL,
    caminho TEXT NOT NULL,
    propostas INTEGER NOT NULL DEFAULT 0,
    mostrado INTEGER NOT NULL DEFAULT 0,
    falha_aviso TEXT NOT NULL DEFAULT ''
);
"""
# Linha de pendência dos relatórios antigos: "- nº 3: <pergunta> (cancelada, 0 tentativa(s))".
_PERGUNTA_NO_RELATORIO = re.compile(
    r"^- nº (\d+): .* \(([a-z_]+), (\d+) tentativa\(s\)\)$", re.MULTILINE
)
# Estados de uma proposta. "publicada" só com autorização explícita.
ABERTAS = ("proposta",)
DECIDIDAS = ("aprovada", "recusada", "adiada")
DESENVOLVIMENTO = ("preparacao", "em_teste", "pronta_para_revisao", "publicada")
ESTADOS = (*ABERTAS, *DECIDIDAS, *DESENVOLVIMENTO)
SEGUINTE = {
    "aprovada": "preparacao",
    "preparacao": "em_teste",
    "em_teste": "pronta_para_revisao",
    "pronta_para_revisao": "publicada",
}


@dataclass(frozen=True)
class Regra:
    """Como descrever um tipo de problema (o texto da proposta)."""

    titulo: str  # com {motor} e {n}
    causa: str
    solucao: str
    beneficio: str
    impacto: str
    risco: str
    testes: str
    arquivos: str


REGRAS = {
    ("llm", "erro_provedor"): Regra(
        "{motor} falhou {n} vezes",
        "Chave recusada, sem créditos, rede instável ou modelo indisponível para a chave.",
        "Rodar `nora --verificar`; se o modelo sumiu, trocar em [modelos.*]; se for rede, a "
        "ordem de reserva já cobre, mas vale ver se outra nuvem deveria ser a primeira.",
        "Menos respostas pela reserva e menos espera.",
        "Custo pode mudar se a ordem das nuvens mudar.",
        "Baixo (configuração).",
        "Teste do roteador com cliente falso simulando o erro e a reserva.",
        "src/nora/roteador.py, src/nora/cerebro_openai.py, src/nora/cerebro_nuvem.py",
    ),
    ("llm", "timeout"): Regra(
        "{motor} demorou demais {n} vezes",
        "Esforço de raciocínio alto, modelo sobrecarregado ou rede lenta.",
        "Baixar o esforço (esforco_pesado) ou usar um modelo mais rápido nas perguntas comuns; "
        "rever o tempo-limite do cliente.",
        "Respostas que começam mais cedo.",
        "Esforço menor pode dar respostas um pouco piores; custo tende a cair.",
        "Baixo.",
        "Teste com cliente falso que demora e confere a reserva.",
        "src/nora/cerebro_openai.py, src/nora/cerebro_nuvem.py, config/nora.toml",
    ),
    ("llm", "resposta_vazia"): Regra(
        "{motor} recusou ou não respondeu {n} vezes",
        "Recusa do modelo ou resposta vazia para o tipo de pergunta feita.",
        "Conferir se as perguntas recusadas deviam ir para outra nuvem primeiro "
        "([roteador] complexas) e se a persona está provocando recusas.",
        "Menos idas à reserva.",
        "Nenhum relevante.",
        "Baixo.",
        "Teste com o cliente falso de recusa.",
        "src/nora/roteador.py, src/nora/persona.py",
    ),
    ("llm", "stream_interrompido"): Regra(
        "Respostas do {motor} caíram no meio {n} vezes",
        "Conexão caindo durante a resposta, limite de uso ou o Ollama ficando sem memória.",
        "Ver os avisos [cérebro] desses momentos; se for o local, conferir VRAM e keep_alive; "
        "se for nuvem, conferir limites de uso.",
        "Menos respostas pela metade (pendências).",
        "Pode pedir menos contexto ou modelo menor.",
        "Médio: mexe no caminho principal de resposta.",
        "Teste de falha no meio do fluxo, sem emendar respostas.",
        "src/nora/roteador.py, src/nora/cerebro.py",
    ),
    ("llm", "sem_resposta"): Regra(
        "Pedidos sem nenhuma resposta ({n} vezes)",
        "Nenhum cérebro disponível na hora (ex.: modo jogo sem internet).",
        "Conferir a internet e as chaves (nora --verificar) e a ordem das nuvens. No modo jogo "
        "o cérebro local fica de fora de propósito: a pergunta vira pendência e, ao sair do "
        "modo jogo (com confirmação), a Nora oferece retomá-la.",
        "Menos perguntas sem resposta, sem ocupar a placa de vídeo durante o jogo.",
        "Nenhum para a GPU: o modo jogo continua sem o cérebro local; a pendência só é "
        "retomada quando você pedir.",
        "Médio.",
        "Teste do modo jogo sem nuvem.",
        "src/nora/roteador.py",
    ),
    ("llm", "latencia_alta"): Regra(
        "{motor} lento para começar a responder ({n} vezes)",
        "Modelo grande para a placa, contexto longo, esforço alto ou modelo sendo carregado.",
        "Conferir keep_alive e VRAM; reduzir contexto ou esforço; considerar um modelo menor "
        "para conversa.",
        "Conversa mais fluida (meta do projeto: menos de 1 s).",
        "Modelo menor pode responder pior.",
        "Médio.",
        "Medir com `nora conversar --medir` antes e depois.",
        "src/nora/cerebro.py, config/nora.toml",
    ),
    ("llm", "feedback_negativo"): Regra(
        "Reclamações de respostas do {motor} ({n} vezes)",
        "Respostas erradas, fora do assunto ou longas demais para o que foi pedido.",
        "Rever a persona e as preferências; se for o local, mandar mais perguntas para a nuvem "
        "(triagem) ou usar um modelo melhor.",
        "Respostas mais certas de primeira.",
        "Mais nuvem = mais custo.",
        "Baixo a médio.",
        "Conjunto de perguntas reais com a resposta esperada (teste de regressão).",
        "src/nora/persona.py, src/nora/roteador.py",
    ),
    ("roteador", "rota_suspeita"): Regra(
        "A triagem deixou para o local perguntas que precisavam de mais ({n} vezes)",
        "As palavras-chave da triagem não pegaram esse tipo de pergunta.",
        "Ampliar os sinais de peso da triagem ou adotar o classificador com nível de confiança "
        "(proposta já no roadmap).",
        "Menos segunda chance; respostas certas mais cedo.",
        "Mais perguntas na nuvem (custo).",
        "Médio.",
        "Testes da triagem com as perguntas reclamadas (sem dados pessoais).",
        "src/nora/roteador.py",
    ),
    ("stt", "latencia_alta"): Regra(
        "Transcrição lenta no {motor} ({n} vezes)",
        "Modelo do Whisper grande demais, poucas threads ou sem aceleração Vulkan.",
        "Conferir as threads e o Vulkan no iniciar_voz_windows.ps1; testar um modelo menor.",
        "Ela começa a pensar mais cedo.",
        "Modelo menor erra mais palavras.",
        "Baixo.",
        "Medir a transcrição com `nora falar --medir`.",
        "scripts/iniciar_voz_windows.ps1, src/nora/ouvido.py",
    ),
    ("tts", "latencia_alta"): Regra(
        "A voz {motor} demora para começar ({n} vezes)",
        "Motor de voz lento (nuvem ou servidor local sem GPU) ou frases muito longas.",
        "Testar o modelo Flash do ElevenLabs ou uma voz local; conferir o tamanho do lote.",
        "Fala começa mais cedo.",
        "Outra voz muda o timbre.",
        "Baixo.",
        "Medir com `nora falar --medir`.",
        "src/nora/voz.py, src/nora/conversa_voz.py",
    ),
    ("tts", "erro_provedor"): Regra(
        "A voz {motor} falhou {n} vezes",
        "Servidor da voz fechado, chave/créditos do ElevenLabs ou rede.",
        "Conferir a janela do servidor da voz ou a conta do ElevenLabs; manter uma reserva local.",
        "Menos falas na voz reserva ou sem voz.",
        "Nenhum relevante.",
        "Baixo.",
        "Teste da voz com reserva (cliente falso).",
        "src/nora/voz.py",
    ),
}
GENERICA = Regra(
    "{tipo} em {etapa} ({motor}) {n} vezes",
    "Ainda sem regra específica para este tipo de evento.",
    "Olhar os eventos desse tipo e decidir se merecem uma regra própria.",
    "A definir.",
    "A definir.",
    "A definir.",
    "A definir.",
    "src/nora/melhorias.py",
)


@dataclass(frozen=True)
class Proposta:
    id: int
    chave: str
    criada: str
    atualizada: str
    categoria: str
    titulo: str
    dados: dict
    status: str
    adiada_ate: str = ""


@dataclass
class Fechamento:
    data: str
    inicio: str
    fim: str
    caminho: Path | None
    novas: list[Proposta] = field(default_factory=list)
    esperando: list[Proposta] = field(default_factory=list)
    acompanhamento: list[Proposta] = field(default_factory=list)
    eventos: int = 0
    pendentes: int = 0

    @property
    def resumo(self) -> str:
        if not self.novas and not self.esperando:
            return "sem novas melhorias relevantes"
        partes = []
        if self.novas:
            partes.append(f"{len(self.novas)} proposta(s) nova(s)")
        if self.esperando:
            partes.append(f"{len(self.esperando)} esperando sua decisão")
        return ", ".join(partes)


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hora(texto: str) -> time:
    horas, minutos = texto.split(":")
    return time(int(horas), int(minutos))


# --- diagnóstico (por regras, sem modelo) -----------------------------------------------------


def diagnosticar(eventos: list[dict], cfg) -> list[dict]:
    """Agrupa os eventos por causa provável e devolve os grupos que se repetiram o bastante.
    Uma ocorrência só não vira proposta (cfg.min_ocorrencias)."""
    limites = {
        ("llm", "resposta"): cfg.latencia_resposta_ms,
        ("stt", "transcricao"): cfg.latencia_ouvido_ms,
        ("tts", "voz"): cfg.latencia_voz_ms,
    }
    grupos: dict[tuple[str, str, str], list[dict]] = {}
    totais: dict[tuple[str, str], int] = {}
    for evento in eventos:
        etapa, tipo, motor = evento["etapa"], evento["tipo"], evento["motor"]
        if (etapa, tipo) in limites:  # medida de tempo: só conta quando passou do limite
            totais[(etapa, motor)] = totais.get((etapa, motor), 0) + 1
            if evento["duracao_ms"] <= limites[(etapa, tipo)]:
                continue
            tipo = "latencia_alta"
        elif tipo in ("resposta", "escalou", "comando", "transcricao", "voz", "cancelada"):
            continue  # normal ou escolha da pessoa: não é problema
        grupos.setdefault((etapa, tipo, motor), []).append(evento)
    achados = []
    for (etapa, tipo, motor), lista in grupos.items():
        if len(lista) < cfg.min_ocorrencias:
            continue
        regra = REGRAS.get((etapa, tipo), GENERICA)
        tempos = [e["duracao_ms"] for e in lista if e["duracao_ms"]]
        dias = sorted({e["quando"][:10] for e in lista})
        n = len(lista)
        total = totais.get((etapa, motor))
        graves = sum(e["gravidade"] == "erro" for e in lista)
        prioridade = "alta" if graves >= 5 or n >= 10 else "média" if graves or n >= 5 else "baixa"
        confianca = (
            "alta"
            if n >= 3 * cfg.min_ocorrencias and len(dias) > 1
            else "média"
            if n >= 2 * cfg.min_ocorrencias
            else "baixa"
        )
        evidencia = {
            "tipo": tipo,
            "etapa": etapa,
            "motor": motor or "(sem motor)",
            "ocorrencias": n,
            "dias": dias,
            "primeira": lista[0]["quando"],
            "ultima": lista[-1]["quando"],
            "exemplos": [e["interacao"] for e in lista if e["interacao"]][:3],
            "no_modo_jogo": sum(bool(e["modo_jogo"]) for e in lista),
        }
        if total:
            evidencia["de_um_total_de"] = total
        if tempos:
            evidencia["mediana_ms"] = int(statistics.median(tempos))
            evidencia["maior_ms"] = max(tempos)
        achados.append(
            {
                "chave": f"{etapa}|{tipo}|{motor}",
                "categoria": tipo,
                "titulo": regra.titulo.format(motor=motor or etapa, n=n, tipo=tipo, etapa=etapa),
                "dados": {
                    "evidencia": evidencia,
                    "causa_provavel": regra.causa,
                    "solucao": regra.solucao,
                    "beneficios_estimados": regra.beneficio,
                    "impacto": regra.impacto,
                    "risco": regra.risco,
                    "testes_exigidos": regra.testes,
                    "arquivos": regra.arquivos,
                    "prioridade": prioridade,
                    "confianca": confianca,
                    "fontes": [],
                    "versao": __version__,
                },
            }
        )
    ordem = {"alta": 0, "média": 1, "baixa": 2}
    return sorted(
        achados,
        key=lambda a: (ordem[a["dados"]["prioridade"]], -a["dados"]["evidencia"]["ocorrencias"]),
    )


# --- banco, fechamento do dia e relatório -----------------------------------------------------


class Melhorias:
    def __init__(self, config, observador: Observador | None = None) -> None:
        self.config = config
        self.cfg = config.auto_melhoria
        self.pasta = config.pasta_dados / "auto_melhoria"
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.observador = observador or Observador(caminho_do_banco(config.pasta_dados))
        self._trava = threading.RLock()
        self._db = sqlite3.connect(
            caminho_do_banco(config.pasta_dados), check_same_thread=False, timeout=10
        )
        with self._db:
            self._db.executescript(ESQUEMA)
            colunas = {c[1] for c in self._db.execute("PRAGMA table_info(fechamentos)")}
            if "falha_aviso" not in colunas:  # bancos de antes do registro de falhas
                self._db.execute(
                    "ALTER TABLE fechamentos ADD COLUMN falha_aviso TEXT NOT NULL DEFAULT ''"
                )
        self._limpar_perguntas_dos_relatorios()

    def _limpar_perguntas_dos_relatorios(self) -> None:
        """Relatórios feitos antes desta correção traziam o começo das perguntas pendentes:
        tira o texto e deixa só número, motivo e tentativas."""
        for relatorio in (self.pasta / "relatorios").glob("*.md"):
            try:
                texto = relatorio.read_text(encoding="utf-8")
                limpo = _PERGUNTA_NO_RELATORIO.sub(r"- nº \1 (\2, \3 tentativa(s))", texto)
                if limpo != texto:
                    relatorio.write_text(limpo, encoding="utf-8")
            except OSError:
                pass

    # propostas ------------------------------------------------------------------------------

    def _proposta(self, linha) -> Proposta:
        pid, chave, criada, atualizada, categoria, titulo, dados, status, adiada = linha
        return Proposta(
            pid, chave, criada, atualizada, categoria, titulo, json.loads(dados), status, adiada
        )

    _SELECT = (
        "SELECT id, chave, criada, atualizada, categoria, titulo, dados, status, adiada_ate "
        "FROM propostas"
    )

    def proposta(self, proposta_id: int) -> Proposta | None:
        with self._trava:
            linha = self._db.execute(f"{self._SELECT} WHERE id = ?", (proposta_id,)).fetchone()
        return self._proposta(linha) if linha else None

    def propostas(self, status: tuple[str, ...] = ()) -> list[Proposta]:
        consulta, valores = self._SELECT, ()
        if status:
            consulta += f" WHERE status IN ({','.join('?' * len(status))})"
            valores = status
        with self._trava:
            linhas = self._db.execute(consulta + " ORDER BY id", valores).fetchall()
        return [self._proposta(linha) for linha in linhas]

    def _atualizar(self, achado: dict, dia: date) -> tuple[str, Proposta]:
        """Grava o achado. Devolve ('nova' | 'esperando' | 'acompanhamento' | 'oculta', proposta).
        Recusada só volta com evidência nova (o dobro de ocorrências) ou outra versão; adiada
        volta na data marcada."""
        agora = _agora()
        dados = json.dumps(achado["dados"], ensure_ascii=False)
        with self._trava, self._db:
            linha = self._db.execute(
                "SELECT id, status, contagem_na_decisao, versao_na_decisao, adiada_ate "
                "FROM propostas WHERE chave = ?",
                (achado["chave"],),
            ).fetchone()
            if linha is None:
                cursor = self._db.execute(
                    "INSERT INTO propostas(chave, criada, atualizada, categoria, titulo, dados, "
                    "status) VALUES (?, ?, ?, ?, ?, ?, 'proposta')",
                    (achado["chave"], agora, agora, achado["categoria"], achado["titulo"], dados),
                )
                return "nova", self.proposta(cursor.lastrowid)
            pid, status, contagem, versao, adiada_ate = linha
            n = achado["dados"]["evidencia"]["ocorrencias"]
            novo_status, grupo = status, "acompanhamento"
            if status == "proposta":
                grupo = "esperando"
            elif status == "recusada":
                voltou = n >= 2 * max(contagem, 1) or versao != __version__
                novo_status, grupo = ("proposta", "nova") if voltou else (status, "oculta")
            elif status == "adiada":
                venceu = not adiada_ate or adiada_ate <= dia.isoformat()
                novo_status, grupo = ("proposta", "nova") if venceu else (status, "oculta")
            self._db.execute(
                "UPDATE propostas SET atualizada = ?, titulo = ?, dados = ?, status = ? "
                "WHERE id = ?",
                (agora, achado["titulo"], dados, novo_status, pid),
            )
        return grupo, self.proposta(pid)

    def decidir(self, proposta_id: int, acao: str, quem: str, motivo: str = "", dias: int = 7):
        """aprovar, recusar ou adiar. Aprovar gera a tarefa de desenvolvimento (um arquivo), mas
        não muda o código. Devolve a proposta atualizada (ou None se não existe ou já foi)."""
        status = {"aprovar": "aprovada", "recusar": "recusada", "adiar": "adiada"}[acao]
        proposta = self.proposta(proposta_id)
        if proposta is None or proposta.status not in ABERTAS:
            return None
        adiada_ate = (date.today() + timedelta(days=dias)).isoformat() if acao == "adiar" else ""
        with self._trava, self._db:
            self._db.execute(
                "UPDATE propostas SET status = ?, atualizada = ?, contagem_na_decisao = ?, "
                "versao_na_decisao = ?, adiada_ate = ? WHERE id = ?",
                (
                    status,
                    _agora(),
                    proposta.dados["evidencia"]["ocorrencias"],
                    __version__,
                    adiada_ate,
                    proposta_id,
                ),
            )
            self._db.execute(
                "INSERT INTO decisoes(proposta_id, quando, acao, quem, motivo) "
                "VALUES (?, ?, ?, ?, ?)",
                (proposta_id, _agora(), acao, quem, motivo),
            )
        if acao == "aprovar":
            self._escrever_tarefa(self.proposta(proposta_id))
        return self.proposta(proposta_id)

    def avancar(self, proposta_id: int, estado: str, quem: str, autorizo_publicar=False):
        """Move uma proposta aprovada pelo desenvolvimento. Publicar pede autorização à parte."""
        proposta = self.proposta(proposta_id)
        if proposta is None or SEGUINTE.get(proposta.status) != estado:
            return None
        if estado == "publicada" and not autorizo_publicar:
            return None
        with self._trava, self._db:
            self._db.execute(
                "UPDATE propostas SET status = ?, atualizada = ? WHERE id = ?",
                (estado, _agora(), proposta_id),
            )
            self._db.execute(
                "INSERT INTO decisoes(proposta_id, quando, acao, quem) VALUES (?, ?, ?, ?)",
                (proposta_id, _agora(), estado, quem),
            )
        return self.proposta(proposta_id)

    def decisoes(self, proposta_id: int) -> list[tuple[str, str, str, str]]:
        with self._trava:
            return self._db.execute(
                "SELECT quando, acao, quem, motivo FROM decisoes WHERE proposta_id = ? ORDER BY id",
                (proposta_id,),
            ).fetchall()

    def _escrever_tarefa(self, proposta: Proposta) -> Path:
        """A especificação para desenvolver a melhoria (para o Codex ou outra pessoa)."""
        pasta = self.pasta / "tarefas"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"melhoria-{proposta.id}.md"
        d = proposta.dados
        caminho.write_text(
            f"# Tarefa: melhoria nº {proposta.id} — {proposta.titulo}\n\n"
            f"Aprovada para **desenvolver** em {_agora()[:10]}. Publicar exige nova autorização "
            f"(`nora melhorias estado {proposta.id} publicada --autorizo-publicar`).\n\n"
            f"## Problema\n\n{_evidencia_em_texto(d['evidencia'])}\n\n"
            f"**Causa provável:** {d['causa_provavel']}\n\n"
            f"## O que fazer\n\n{d['solucao']}\n\n"
            f"**Arquivos prováveis:** {d['arquivos']}\n\n"
            f"## Testes exigidos\n\n{d['testes_exigidos']}\n\n"
            "## Regras\n\n"
            "- Branch isolada; testes automatizados antes de qualquer merge.\n"
            "- Seguir o `CLAUDE.md` (pt-BR, Conventional Commits, licenças, nada pessoal no Git, "
            "nada só-CUDA).\n"
            "- Não usar dados pessoais de `data/` nos testes.\n"
            f"- Risco: {d['risco']} Impacto: {d['impacto']}\n",
            encoding="utf-8",
        )
        return caminho

    # fechamento do dia ------------------------------------------------------------------------

    def ultimo_fechamento(self) -> tuple[str, str] | None:
        with self._trava:
            return self._db.execute(
                "SELECT data, fim FROM fechamentos ORDER BY data DESC LIMIT 1"
            ).fetchone()

    def dia_a_fechar(self, agora: datetime | None = None) -> date | None:
        """O dia cujo relatório está faltando, ou None. Depois da hora marcada é hoje; antes, é
        ontem (o PC estava desligado na hora). Um relatório por dia, sem repetir."""
        agora = agora or datetime.now()
        alvo = agora.date()
        if agora.time() < _hora(self.cfg.hora_relatorio):
            alvo -= timedelta(days=1)
        ultimo = self.ultimo_fechamento()
        if ultimo is None:
            if not self.observador.eventos():  # primeiro uso: só marca o começo
                with self._trava, self._db:
                    self._db.execute(
                        "INSERT INTO fechamentos(data, inicio, fim, criado, caminho, mostrado) "
                        "VALUES (?, '', ?, ?, '', 1)",
                        (alvo.isoformat(), agora.isoformat(timespec="seconds"), _agora()),
                    )
                return None
            return alvo
        return alvo if ultimo[0] < alvo.isoformat() else None

    def fechar(self, dia: date, agora: datetime | None = None, pendentes=()) -> Fechamento:
        """Analisa os eventos desde o fechamento anterior, grava as propostas e o relatório."""
        agora = agora or datetime.now()
        fim = agora.isoformat(timespec="seconds")
        with self._trava:
            anterior = self._db.execute(
                "SELECT fim FROM fechamentos WHERE data < ? ORDER BY data DESC LIMIT 1",
                (dia.isoformat(),),
            ).fetchone()
        inicio = anterior[0] if anterior else ""
        eventos = self.observador.eventos(inicio, fim)
        fechamento = Fechamento(dia.isoformat(), inicio, fim, None, eventos=len(eventos))
        for achado in diagnosticar(eventos, self.cfg):
            grupo, proposta = self._atualizar(achado, dia)
            if grupo == "nova":
                fechamento.novas.append(proposta)
            elif grupo == "esperando":
                fechamento.esperando.append(proposta)
            elif grupo == "acompanhamento":
                fechamento.acompanhamento.append(proposta)
        fechamento.pendentes = len(pendentes)
        pasta = self.pasta / "relatorios"
        pasta.mkdir(parents=True, exist_ok=True)
        caminho = pasta / f"{dia.isoformat()}.md"
        caminho.write_text(_relatorio(fechamento, list(pendentes)), encoding="utf-8")
        fechamento.caminho = caminho
        with self._trava, self._db:
            self._db.execute(
                "INSERT OR REPLACE INTO fechamentos(data, inicio, fim, criado, caminho, "
                "propostas, mostrado) VALUES (?, ?, ?, ?, ?, ?, 0)",
                (
                    dia.isoformat(),
                    inicio,
                    fim,
                    _agora(),
                    str(caminho),
                    len(fechamento.novas) + len(fechamento.esperando),
                ),
            )
        self.observador.limpar_antigos(self.cfg.dias_de_eventos, agora)
        return fechamento

    def nao_mostrados(self) -> list[tuple[str, str, int]]:
        """Relatórios ainda não apresentados: (data, caminho, propostas). Só viram "mostrados"
        com marcar_mostrado, depois de aparecerem de fato."""
        with self._trava:
            return self._db.execute(
                "SELECT data, caminho, propostas FROM fechamentos "
                "WHERE mostrado = 0 AND caminho != '' ORDER BY data"
            ).fetchall()

    def marcar_mostrado(self, data: str) -> None:
        with self._trava, self._db:
            self._db.execute("UPDATE fechamentos SET mostrado = 1 WHERE data = ?", (data,))

    def registrar_falha_do_aviso(self, data: str, motivo: str) -> None:
        """Guarda por que o relatório não apareceu (ele tenta de novo na próxima sessão)."""
        with self._trava, self._db:
            self._db.execute(
                "UPDATE fechamentos SET falha_aviso = ? WHERE data = ?",
                (f"{_agora()}: {motivo}", data),
            )

    def falha_do_aviso(self, data: str) -> str:
        with self._trava:
            linha = self._db.execute(
                "SELECT falha_aviso FROM fechamentos WHERE data = ?", (data,)
            ).fetchone()
        return linha[0] if linha else ""

    def relatorio(self, dia: str = "") -> Path | None:
        with self._trava:
            if dia:
                linha = self._db.execute(
                    "SELECT caminho FROM fechamentos WHERE data = ? AND caminho != ''", (dia,)
                ).fetchone()
            else:
                linha = self._db.execute(
                    "SELECT caminho FROM fechamentos WHERE caminho != '' ORDER BY data DESC"
                ).fetchone()
        return Path(linha[0]) if linha else None

    def fechar_banco(self) -> None:
        with self._trava:
            self._db.close()


def _evidencia_em_texto(e: dict) -> str:
    texto = f"{e['ocorrencias']} ocorrência(s) de `{e['tipo']}` em `{e['etapa']}` ({e['motor']})"
    if e.get("de_um_total_de"):
        texto += f", de {e['de_um_total_de']} medidas"
    texto += f", entre {e['primeira'].replace('T', ' ')} e {e['ultima'].replace('T', ' ')}"
    if e.get("mediana_ms"):
        texto += f"; mediana {e['mediana_ms']} ms, maior {e['maior_ms']} ms"
    if e.get("no_modo_jogo"):
        texto += f"; {e['no_modo_jogo']} no modo jogo"
    return texto + "."


def _bloco(p: Proposta) -> str:
    d = p.dados
    return (
        f"### Nº {p.id} — {p.titulo}\n\n"
        f"- **Categoria:** {p.categoria} · **Prioridade:** {d['prioridade']} · "
        f"**Confiança:** {d['confianca']}\n"
        f"- **Evidência:** {_evidencia_em_texto(d['evidencia'])}\n"
        f"- **Causa provável:** {d['causa_provavel']}\n"
        f"- **Solução sugerida:** {d['solucao']}\n"
        f"- **Benefícios estimados:** {d['beneficios_estimados']}\n"
        f"- **Impacto (tempo, custo, GPU):** {d['impacto']}\n"
        f"- **Risco:** {d['risco']}\n"
        f"- **Testes exigidos:** {d['testes_exigidos']}\n"
        f"- **Arquivos:** {d['arquivos']}\n"
        f"- **Fontes:** nenhuma (pesquisa na web ainda não existe; diagnóstico por regras).\n"
        f"- **Decidir:** `nora melhorias aprovar {p.id}` · `recusar {p.id}` · `adiar {p.id}`\n"
    )


def _relatorio(f: Fechamento, pendentes: list) -> str:
    janela = f"desde {f.inicio.replace('T', ' ')}" if f.inicio else "desde o começo"
    linhas = [
        f"# Melhorias da Nora — {f.data[8:10]}/{f.data[5:7]}/{f.data[:4]}",
        "",
        f"Janela analisada: {janela} até {f.fim.replace('T', ' ')} ({f.eventos} eventos). "
        "Diagnóstico por regras, sem internet. Nada foi mudado no código: cada proposta espera "
        "a sua decisão.",
        "",
    ]
    if not f.novas and not f.esperando and not pendentes:
        linhas += ["**Sem novas melhorias relevantes.**", ""]
    if f.novas:
        linhas += ["## Propostas novas", ""] + [_bloco(p) for p in f.novas]
    if f.esperando:
        linhas += ["## Ainda esperando sua decisão", ""] + [_bloco(p) for p in f.esperando]
    if f.acompanhamento:
        linhas += ["## Em acompanhamento (já decididas)", ""]
        linhas += [f"- Nº {p.id} — {p.titulo} ({p.status})" for p in f.acompanhamento] + [""]
    if pendentes:
        # Só número, motivo e data: o texto da pergunta é pessoal e não vai para o relatório
        # (ele aparece só com um pedido explícito: nora pendencias).
        linhas += ["## Respostas que ficaram pela metade", ""]
        linhas += [
            f"- nº {p.id} ({p.motivo}, {p.tentativas} tentativa(s)), de {p.criada[:10]}"
            for p in pendentes
        ]
        linhas += [
            "",
            'Para ver as perguntas: nora pendencias. Para terminar a última: "termina a resposta '
            'que ficou pela metade".',
            "",
        ]
    return "\n".join(linhas)


# --- aviso: notificação do Windows e abrir o relatório ----------------------------------------


def notificar(titulo: str, texto: str, caminho: Path) -> bool:
    """Notificação do Windows que abre o relatório ao clicar. Fora do Windows, ou se falhar,
    devolve False (o aviso também aparece na próxima conversa)."""
    if sys.platform != "win32":
        return False
    xml = (
        f'<toast activationType="protocol" launch="{escape(caminho.resolve().as_uri())}">'
        f'<visual><binding template="ToastGeneric"><text>{escape(titulo)}</text>'
        f"<text>{escape(texto)}</text></binding></visual></toast>"
    ).replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';"
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
        "ContentType = WindowsRuntime] | Out-Null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, "
        "ContentType = WindowsRuntime] | Out-Null;"
        "$x = New-Object Windows.Data.Xml.Dom.XmlDocument;"
        f"$x.LoadXml('{xml}');"
        "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe';"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($app)"
        ".Show((New-Object Windows.UI.Notifications.ToastNotification $x))"
    )
    try:
        resultado = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            stdin=subprocess.DEVNULL,  # o PowerShell não pode disputar o teclado da sessão
            timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return resultado.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# ShellExecute: mostra minimizada e sem ativar. O programa do .md não toma o foco do terminal,
# onde a pessoa está no meio de um "[Enter para falar]" (senão o Enter iria para o editor).
SW_SHOWMINNOACTIVE = 7


def abrir_arquivo(caminho: Path) -> bool:
    """Abre o relatório no programa padrão sem roubar o teclado da sessão: no Windows, a janela
    abre minimizada e sem foco; fora dele, o programa não herda o terminal (stdin) da Nora."""
    try:
        if sys.platform == "win32":
            os.startfile(caminho, "open", show_cmd=SW_SHOWMINNOACTIVE)  # noqa: S606
        else:
            subprocess.Popen(
                ["xdg-open", str(caminho)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        return True
    except (OSError, AttributeError, TypeError):
        return False


# --- agendador mínimo (enquanto a Nora está aberta) -------------------------------------------


class Agendador(threading.Thread):
    """Confere a cada minuto se o relatório do dia está faltando e, quando a Nora não está
    ocupada (respondendo ou no modo jogo), fecha o dia. A primeira conferência é logo ao abrir:
    cobre o dia em que o PC estava desligado na hora."""

    def __init__(
        self,
        melhorias: Melhorias,
        ocupado: Callable[[], bool],
        ao_fechar: Callable[[Fechamento], None],
        pendentes: Callable[[], list] = list,
        intervalo: float = 60.0,
        relogio: Callable[[], datetime] = datetime.now,
    ) -> None:
        super().__init__(daemon=True, name="nora-auto-melhoria")
        self.melhorias, self.ocupado, self.ao_fechar = melhorias, ocupado, ao_fechar
        self.pendentes, self.intervalo, self.relogio = pendentes, intervalo, relogio
        self._parar = threading.Event()
        self.apresentar_pendentes: Callable[[], bool] = lambda: False

    def conferir(self) -> Fechamento | None:
        if self.ocupado():
            return None
        agora = self.relogio()
        dia = self.melhorias.dia_a_fechar(agora)
        if dia is None:
            return None
        try:
            pendentes = self.pendentes()
        except Exception as erro:
            logging.getLogger(__name__).error("Falha ao listar pendências: %s", type(erro).__name__)
            pendentes = []
        fechamento = self.melhorias.fechar(dia, agora, pendentes)
        self.ao_fechar(fechamento)
        return fechamento

    def run(self) -> None:
        while not self._parar.is_set():
            try:
                self.conferir()
            except Exception as erro:
                # Não registrar a mensagem/traceback: provedores podem incluir texto pessoal.
                logging.getLogger(__name__).error("Falha no agendador: %s", type(erro).__name__)
            self._parar.wait(self.intervalo)

    def parar(self) -> None:
        self._parar.set()


def apresentar(
    melhorias: Melhorias,
    data: str,
    caminho: Path,
    quantas: int,
    modo: str,
    escrever: Callable[[str], None],
) -> bool:
    """Mostra um relatório novo sem a pessoa pedir: abre o .md (modo "abrir") ou escreve o
    texto inteiro na conversa (modo "terminal", ou se abrir falhar). Só então marca como
    mostrado. Devolve se apareceu."""
    dia = f"{data[8:10]}/{data[5:7]}"
    if not caminho.is_file():
        melhorias.registrar_falha_do_aviso(data, f"arquivo não encontrado: {caminho}")
        escrever(
            f"[melhorias] O relatório de {dia} sumiu ({caminho}). "
            "Restaure o arquivo de uma cópia de segurança e reinicie a sessão para exibi-lo. "
            "Sem uma cópia, não é possível recuperar o conteúdo original automaticamente."
        )
        return False
    resumo = f"{quantas} proposta(s) para decidir" if quantas else "sem novas melhorias relevantes"
    if modo == "abrir":
        if abrir_arquivo(caminho):
            melhorias.marcar_mostrado(data)
            escrever(f"[melhorias] Abri o relatório de {dia} ({resumo}): {caminho}")
            return True
        melhorias.registrar_falha_do_aviso(
            data, "não consegui abrir o .md; tentando mostrar na conversa"
        )
    try:
        texto = caminho.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as erro:
        motivo = f"falha ao ler o .md: {type(erro).__name__}"
        melhorias.registrar_falha_do_aviso(data, motivo)
        escrever(
            f"[melhorias] Não consegui ler o relatório de {dia} ({motivo}). "
            "Corrija as permissões ou restaure uma cópia UTF-8 do arquivo e reinicie a sessão. "
            "O relatório continua pendente."
        )
        return False
    escrever(f"[melhorias] Relatório de {dia} ({resumo}):")
    escrever(texto)
    melhorias.marcar_mostrado(data)
    return True


def abrir_melhorias(config, observador: Observador | None = None) -> Melhorias | None:
    if not config.auto_melhoria.ativa:
        return None
    try:
        return Melhorias(config, observador)
    except Exception:
        return None


def iniciar(conversa, escrever: Callable[[str], None]) -> Agendador | None:
    """Liga a auto-melhoria numa sessão (nora conversar, falar, ouvir): mostra os relatórios
    ainda não vistos e começa o agendador do dia."""
    melhorias = getattr(conversa, "melhorias", None)
    if melhorias is None:
        return None
    cfg = conversa.config.auto_melhoria

    def ao_fechar(fechamento: Fechamento) -> None:
        """O dia fechou com a Nora desocupada: notifica sem escrever na interface."""
        if fechamento.caminho is None:
            return
        texto = f"Relatório de melhorias pronto: {fechamento.resumo}."
        if cfg.notificar and sys.platform == "win32":
            if not notificar(
                "Nora: melhorias do dia", texto + " Clique para abrir.", fechamento.caminho
            ):
                melhorias.registrar_falha_do_aviso(fechamento.data, "a notificação falhou")
        # A apresentação pertence ao loop da interface; esta thread só fecha e notifica.

    def ocupado() -> bool:
        return bool(getattr(conversa, "ocupada", False) or getattr(conversa.cerebro, "jogo", False))

    def pendentes() -> list:
        return conversa.memoria.pendentes() if conversa.memoria is not None else []

    agendador = Agendador(melhorias, ocupado, ao_fechar, pendentes)
    tentados: set[str] = set()

    def apresentar_pendentes() -> bool:
        """Apresenta os relatórios novos; devolve se escreveu algo na tela."""
        if ocupado():
            return False
        escreveu = False
        for data, caminho, quantas in melhorias.nao_mostrados():
            if data in tentados:
                continue  # uma tentativa por sessão; falhas continuam pendentes no banco
            tentados.add(data)
            apresentar(melhorias, data, Path(caminho), quantas, cfg.apresentar, escrever)
            escreveu = True
        return escreveu

    agendador.apresentar_pendentes = apresentar_pendentes
    apresentar_pendentes()
    agendador.start()
    return agendador


def ler_entrada(
    entrada: Callable[[str], str],
    prompt: str,
    agendador: Agendador | None,
    reimprimir: Callable[[str], None] | None = None,
) -> str:
    """Mantém a interface atendendo relatórios enquanto o teclado espera uma linha.

    Só o loop chamador escreve relatórios; a thread de entrada apenas lê o teclado.
    Não antecipa a próxima leitura (a gravação por Enter usa a mesma entrada). Esta função só
    volta com a linha que a sua própria thread leu: um erro ao apresentar um relatório não pode
    deixar essa thread para trás, senão ela engoliria o Enter seguinte (o de parar de gravar).
    Se um relatório aparecer durante a espera, `reimprimir` mostra o prompt de novo.
    """
    if agendador is None:
        return entrada(prompt)
    resultado: queue.Queue = queue.Queue()

    def ler() -> None:
        try:
            resultado.put((True, entrada(prompt)))
        except BaseException as erro:
            resultado.put((False, erro))

    threading.Thread(target=ler, daemon=True, name="nora-entrada").start()
    while True:
        try:
            mostrou = agendador.apresentar_pendentes()
        except Exception as erro:  # a auto-melhoria nunca tira o teclado da conversa
            logging.getLogger(__name__).error(
                "Falha ao apresentar relatório: %s", type(erro).__name__
            )
            mostrou = False
        if mostrou and reimprimir is not None:
            reimprimir(prompt)
        try:
            sucesso, valor = resultado.get(timeout=0.1)
        except queue.Empty:
            continue
        if sucesso:
            return valor
        raise valor
