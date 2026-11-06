"""Second Brain (v0.3.1): as memórias consolidadas da Nora viram notas no Obsidian, com links
entre áreas, nomes, meses da agenda e preferências, e um grafo para o mapa da memória.

A memória (SQLite) continua sendo a fonte da verdade; as notas são uma vista dela.

Fora do caminho da fala, sempre:
- a conversa só chama `avisar()` (levanta um sinal) depois que a curadoria, que já roda em
  segundo plano, grava a memória;
- uma linha própria (`Trabalhador`) espera a Nora ficar livre (sem responder nem falar), lê a
  memória numa conexão só de leitura, compara com o que já foi exportado e escreve só o que
  mudou. Se a Nora voltar a falar no meio, para e continua depois;
- não há fila de eventos que possa encher: o estado exportado (estado.db) é o ponto de
  retomada. Se o PC desligar no meio, a próxima rodada refaz o que faltou, sem duplicar.

Notas que a Nora não criou, ou que você editou, nunca são sobrescritas nem apagadas: viram
conflito em `nora cerebro status`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
import tempfile
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from nora.agenda import NOMES_DOS_MESES
from nora.paleta import cor as cor_da_emocao

VERSAO_DO_CONTRATO = 1
CONTRATO = Path(__file__).with_name("segundo_cerebro_contrato.json")

# As cores das emoções vêm de hud/paleta.json, o mesmo arquivo que a HUD lê (nora.paleta): um
# sistema de cores só, sem cópia. Os nomes são os tons de emocao.py e a neutra.
NOMES_DOS_TONS = (
    "alegre",
    "empolgada",
    "carinhosa",
    "calma",
    "seria",
    "triste",
    "curiosa",
    "neutra",
)
CORES_DAS_EMOCOES = {nome: cor_da_emocao(nome) for nome in NOMES_DOS_TONS}
# Cor de base de cada área (o corpo do nó). Áreas novas ganham uma cor estável da reserva.
CORES_DAS_AREAS = {
    "trabalho": "#2F6BFF",  # azul
    "pessoal": "#F09BD8",  # rosa/lilás
    "saude": "#4ADE80",  # verde
    "familia": "#FBBF24",  # amarelo quente
    "estudos": "#22D3EE",  # ciano
    "projetos": "#FF8A3D",  # laranja
    "rotina": "#CBD5E1",  # prata
    "financas": "#059669",  # verde-esmeralda (mais escuro que saúde)
    "espiritualidade": "#A855F7",  # violeta
    "tecnologia": "#7C8CFF",  # azul elétrico (mais claro e arroxeado que trabalho)
}
_RESERVA_DE_CORES = ["#E879F9", "#FACC15", "#4ADE80", "#F472B6", "#38BDF8", "#FB7185", "#A3E635"]
COR_SEM_AREA = "#9CA3AF"

# Palavras com maiúscula que não são nomes (começo de frase, dias, meses, pronomes).
_NAO_SAO_NOMES = {
    "a", "o", "as", "os", "e", "eu", "ele", "ela", "eles", "elas", "voce", "nos", "hoje",
    "amanha", "ontem", "em", "no", "na", "de", "do", "da", "para", "pra", "com", "por", "um",
    "uma", "segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo", "janeiro",
    "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
    "novembro", "dezembro", "dia", "mes", "ano", "sim", "nao", "quando", "depois", "antes",
}  # fmt: skip
_NOME = re.compile(
    r"\b([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+(?:\s+(?:de|da|do|dos|das)?\s*[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÀ-ÿ]+)*)"
)
_ENTRE_NUMEROS = re.compile(r"(?<=\d)[/\\:](?=\d)")
_PROIBIDOS_NO_NOME = re.compile(r'[\\/:*?"<>|#^\[\]{}\x00-\x1f]')
TAMANHO_DO_TITULO = 60
AVISO_DA_NOTA = (
    "> Nota gerada pela Nora a partir da memória dela. Para corrigir, fale com ela ou use "
    "`nora memoria`. Se você editar esta nota, ela deixa de atualizá-la (vira conflito em "
    "`nora cerebro status`)."
)

log = logging.getLogger(__name__)


def _chave(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).strip()


def cor_da_area(area: str) -> str:
    chave = _chave(area)
    if not chave:
        return COR_SEM_AREA
    if chave in CORES_DAS_AREAS:
        return CORES_DAS_AREAS[chave]
    indice = int(hashlib.sha1(chave.encode()).hexdigest(), 16) % len(_RESERVA_DE_CORES)
    return _RESERVA_DE_CORES[indice]


def nome_de_arquivo(texto: str, tamanho: int = TAMANHO_DO_TITULO) -> str:
    """Um nome que serve de arquivo no Windows e de [[link]] no Obsidian. Barras e dois-pontos
    entre números viram hífen ("21/11/2026" → "21-11-2026", "10:30" → "10-30"), para a data
    continuar legível; o resto dos caracteres proibidos vira espaço."""
    texto = _ENTRE_NUMEROS.sub("-", texto)
    limpo = " ".join(_PROIBIDOS_NO_NOME.sub(" ", texto).split())
    if len(limpo) > tamanho:
        corte = limpo[:tamanho].rsplit(" ", 1)[0] or limpo[:tamanho]
        limpo = corte + "…"
    limpo = limpo.strip(" .")  # Windows não aceita nome terminado em ponto ou espaço
    return limpo or "sem título"


def _yaml(valor) -> str:
    """Valor de propriedade YAML seguro: textos entre aspas (JSON é YAML válido)."""
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, int | float):
        return str(valor)
    return json.dumps(str(valor), ensure_ascii=False)


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash(conteudo: str) -> str:
    return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()


# --- o que vem da memória -----------------------------------------------------------------------


@dataclass(frozen=True)
class FatoExportavel:
    id: int
    texto: str
    area: str
    criado: str
    atualizado: str
    origem: str
    emocao: str = ""
    data: str = ""  # AAAA-MM-DD, se está na agenda


@dataclass
class Conteudo:
    fatos: list[FatoExportavel] = field(default_factory=list)
    preferencias: list[tuple[int, str]] = field(default_factory=list)


def ler_memoria(caminho: Path) -> Conteudo:
    """Lê a memória numa conexão só de leitura (não trava a conversa, que escreve na dela)."""
    if not caminho.is_file():
        return Conteudo()
    db = sqlite3.connect(f"{caminho.resolve().as_uri()}?mode=ro", uri=True, timeout=5)
    try:
        colunas = {linha[1] for linha in db.execute("PRAGMA table_info(fatos)")}
        emocao = "emocao" if "emocao" in colunas else "''"
        area = "area" if "area" in colunas else "''"
        datas: dict[int, str] = {}
        tabelas = {linha[0] for linha in db.execute("SELECT name FROM sqlite_master")}
        if "agenda" in tabelas:
            for fato_id, data in db.execute(
                "SELECT fato_id, MIN(data) FROM agenda WHERE fato_id IS NOT NULL GROUP BY fato_id"
            ):
                datas[fato_id] = data
        fatos = [
            FatoExportavel(*linha, data=datas.get(linha[0], ""))
            for linha in db.execute(
                f"SELECT id, texto, {area}, criado, atualizado, origem, {emocao} FROM fatos "
                "ORDER BY id"
            )
        ]
        preferencias = (
            list(db.execute("SELECT id, texto FROM preferencias ORDER BY id"))
            if "preferencias" in tabelas
            else []
        )
        return Conteudo(fatos, preferencias)
    finally:
        db.close()


# --- o que vira nota e grafo --------------------------------------------------------------------


@dataclass
class Grafo:
    nos: list[dict] = field(default_factory=list)
    ligacoes: list[dict] = field(default_factory=list)


@dataclass
class Plano:
    notas: dict[str, str] = field(default_factory=dict)  # caminho relativo → conteúdo
    grafo: Grafo = field(default_factory=Grafo)


def _origem_legivel(origem: str) -> str:
    if origem == "manual":
        return "anotado pelo terminal (nora memoria lembrar)"
    if origem.startswith("historico"):
        return f"importado do histórico ({origem.split(' ', 1)[-1]})"
    if origem:
        return f"conversa de {origem[:10]}"
    return "desconhecida"


def nomes_no_texto(texto: str, ignorar: set[str]) -> list[str]:
    """Nomes próprios do texto (pessoas, lugares, siglas). O primeiro nome da frase só conta se
    for sigla, porque ele tem maiúscula de qualquer jeito."""
    nomes = []
    for achado in _NOME.finditer(texto):
        nome = achado.group(1).strip()
        palavras = nome.split()
        no_comeco = achado.start() == 0 or texto[: achado.start()].rstrip()[-1:] in ".!?:"
        while palavras and _chave(palavras[0]) in _NAO_SAO_NOMES:
            palavras.pop(0)
            no_comeco = False
        nome = " ".join(palavras)
        if not nome or _chave(nome) in ignorar or _chave(nome) in _NAO_SAO_NOMES:
            continue
        if no_comeco and not nome.isupper() and len(palavras) == 1:
            continue
        if len(nome) < 3:
            continue
        nomes.append(nome)
    return nomes


class Planejador:
    """Monta as notas e o grafo a partir da memória (função pura de `Conteudo`)."""

    def __init__(self, config, prefixo_dos_links: str) -> None:
        self.opcoes = config.segundo_cerebro
        self.prefixo = prefixo_dos_links  # caminho da pasta do Second Brain dentro do vault
        nomes_proprios = {config.assistente.nome, config.nome_usuario}
        self.ignorar_nomes = {_chave(n) for n in nomes_proprios if n}
        self.privadas = {_chave(area) for area in self.opcoes.areas_privadas}

    def _link(self, caminho: str, rotulo: str) -> str:
        alvo = f"{self.prefixo}/{caminho}" if self.prefixo else caminho
        return f"[[{alvo.removesuffix('.md')}|{rotulo}]]"

    def planejar(self, conteudo: Conteudo) -> Plano:
        plano = Plano()
        fatos = [f for f in conteudo.fatos if _chave(f.area) not in self.privadas]

        titulos: dict[int, str] = {}
        usados: set[str] = set()
        for fato in fatos:
            titulo = nome_de_arquivo(fato.texto)
            if _chave(titulo) in usados:
                titulo = f"{titulo} ({fato.id})"
            usados.add(_chave(titulo))
            titulos[fato.id] = titulo

        # Nomes que aparecem em 2 memórias ou mais: ligam memórias de verdade. Um nome que só
        # aparece uma vez não vira nó (não enche o grafo de pontas soltas).
        mencoes: dict[str, list[int]] = {}
        formas: dict[str, dict[str, int]] = {}
        for fato in fatos:
            for nome in dict.fromkeys(nomes_no_texto(fato.texto, self.ignorar_nomes)):
                chave = _chave(nome)
                if fato.id not in mencoes.setdefault(chave, []):
                    mencoes[chave].append(fato.id)
                formas.setdefault(chave, {}).setdefault(nome, 0)
                formas[chave][nome] += 1
        entidades = {
            chave: max(formas[chave], key=formas[chave].get)
            for chave, ids in mencoes.items()
            if len(ids) >= 2
        }
        nome_da_entidade = {chave: nome_de_arquivo(nome, 80) for chave, nome in entidades.items()}

        por_area: dict[str, list[FatoExportavel]] = {}
        por_mes: dict[str, list[FatoExportavel]] = {}
        nos, ligacoes = plano.grafo.nos, plano.grafo.ligacoes

        for fato in fatos:
            area = fato.area or "sem área"
            por_area.setdefault(area, []).append(fato)
            caminho = f"Memórias/{titulos[fato.id]}.md"
            emocao = fato.emocao if self.opcoes.emocoes else ""
            mes = fato.data[:7] if (self.opcoes.agenda and fato.data) else ""
            if mes:
                por_mes.setdefault(mes, []).append(fato)
            camada = "episodica" if fato.data else "semantica"
            meus_nomes = [
                c
                for c in dict.fromkeys(
                    _chave(n) for n in nomes_no_texto(fato.texto, self.ignorar_nomes)
                )
                if c in entidades
            ]
            propriedades = {
                "nora_id": f"mem-{fato.id:06d}",
                "nora_gerenciado": True,
                "tipo": "memoria",
                "camada": camada,
                "area": area,
                **({"emocao": emocao, "emocao_fonte": "tom da resposta da Nora"} if emocao else {}),
                **({"data": fato.data} if fato.data else {}),
                "origem": _origem_legivel(fato.origem),
                "criado_em": fato.criado,
                "atualizado_em": fato.atualizado,
            }
            tags = [
                "nora",
                f"nora/area/{_tag(area)}",
                "nora/tipo/memoria",
                f"nora/camada/{camada}",
            ]
            if emocao:
                tags.append(f"nora/emocao/{_tag(emocao)}")
            ligado = [f"- Área: {self._link(f'Áreas/{_rotulo_area(area)}.md', _rotulo_area(area))}"]
            ligado += [
                f"- Menciona: {self._link(f'Nomes/{nome_da_entidade[c]}.md', entidades[c])} "
                "(nome que aparece em outras memórias)"
                for c in meus_nomes
            ]
            if mes:
                ligado.append(
                    f"- Agenda: {self._link(f'Agenda/{mes}.md', _rotulo_mes(mes))} "
                    f"({fato.data[8:10]}/{fato.data[5:7]}/{fato.data[:4]})"
                )
            plano.notas[caminho] = _nota(
                propriedades,
                tags,
                f"# {titulos[fato.id]}\n\n{fato.texto}\n\n## Ligações\n\n" + "\n".join(ligado),
            )
            no_id = f"mem-{fato.id}"
            nos.append(
                {
                    "id": no_id,
                    "tipo": "memoria",
                    "rotulo": titulos[fato.id],
                    "texto": fato.texto,
                    "area": area,
                    "camada": camada,
                    "emocao": emocao,
                    "data": fato.data,
                    "origem": _origem_legivel(fato.origem),
                    "atualizado": fato.atualizado,
                    "caminho": caminho,
                }
            )
            ligacoes.append(
                {
                    "de": no_id,
                    "para": f"area-{_tag(area)}",
                    "tipo": "pertence_a",
                    "base": "área anotada pela curadoria",
                }
            )
            for c in meus_nomes:
                ligacoes.append(
                    {
                        "de": no_id,
                        "para": f"nome-{_tag(c)}",
                        "tipo": "menciona",
                        "base": f'o texto cita "{entidades[c]}"',
                    }
                )
            if mes:
                ligacoes.append(
                    {
                        "de": no_id,
                        "para": f"mes-{mes}",
                        "tipo": "aconteceu_em",
                        "base": f"data na agenda: {fato.data}",
                    }
                )

        for area, lista in sorted(por_area.items()):
            rotulo = _rotulo_area(area)
            linhas = [
                f"- {self._link(f'Memórias/{titulos[f.id]}.md', titulos[f.id])}" for f in lista
            ]
            plano.notas[f"Áreas/{rotulo}.md"] = _nota(
                {
                    "nora_id": f"area-{_tag(area)}",
                    "nora_gerenciado": True,
                    "tipo": "area",
                    "area": area,
                    "cor": cor_da_area(area),
                },
                ["nora", f"nora/area/{_tag(area)}", "nora/tipo/area"],
                f"# {rotulo}\n\nMemórias da Nora nesta área ({len(lista)}):\n\n"
                + "\n".join(linhas),
            )
            nos.append(
                {
                    "id": f"area-{_tag(area)}",
                    "tipo": "area",
                    "rotulo": rotulo,
                    "area": area,
                    "caminho": f"Áreas/{rotulo}.md",
                }
            )

        for chave, nome in sorted(entidades.items()):
            ids = [i for i in mencoes[chave] if i in titulos]
            linhas = [f"- {self._link(f'Memórias/{titulos[i]}.md', titulos[i])}" for i in ids]
            caminho = f"Nomes/{nome_da_entidade[chave]}.md"
            plano.notas[caminho] = _nota(
                {"nora_id": f"nome-{_tag(chave)}", "nora_gerenciado": True, "tipo": "nome"},
                ["nora", "nora/tipo/nome"],
                f"# {nome}\n\nAparece em {len(ids)} memórias:\n\n" + "\n".join(linhas),
            )
            nos.append(
                {"id": f"nome-{_tag(chave)}", "tipo": "nome", "rotulo": nome, "caminho": caminho}
            )

        for mes, lista in sorted(por_mes.items()):
            linhas = [
                f"- {f.data[8:10]}/{f.data[5:7]}: "
                f"{self._link(f'Memórias/{titulos[f.id]}.md', titulos[f.id])}"
                for f in sorted(lista, key=lambda f: f.data)
            ]
            plano.notas[f"Agenda/{mes}.md"] = _nota(
                {"nora_id": f"mes-{mes}", "nora_gerenciado": True, "tipo": "agenda"},
                ["nora", "nora/tipo/agenda"],
                f"# {_rotulo_mes(mes)}\n\n" + "\n".join(linhas),
            )
            nos.append(
                {
                    "id": f"mes-{mes}",
                    "tipo": "agenda",
                    "rotulo": _rotulo_mes(mes),
                    "caminho": f"Agenda/{mes}.md",
                }
            )

        if self.opcoes.preferencias and conteudo.preferencias:
            linhas = [f"- {texto}" for _, texto in conteudo.preferencias]
            plano.notas["Preferências.md"] = _nota(
                {
                    "nora_id": "preferencias",
                    "nora_gerenciado": True,
                    "tipo": "preferencia",
                    "camada": "procedural",
                },
                ["nora", "nora/tipo/preferencia"],
                "# Preferências\n\nComo você pediu que a Nora fale (ela segue sempre):\n\n"
                + "\n".join(linhas),
            )
            nos.append(
                {
                    "id": "preferencias",
                    "tipo": "preferencia",
                    "rotulo": "Preferências",
                    "texto": "\n".join(t for _, t in conteudo.preferencias),
                    "caminho": "Preferências.md",
                }
            )

        indice = [
            "# Nora Brain",
            "",
            "O que a Nora lembra, organizado por ela.",
            "",
            "## Áreas",
            "",
        ]
        indice += [
            f"- {self._link(f'Áreas/{_rotulo_area(a)}.md', _rotulo_area(a))}"
            for a in sorted(por_area)
        ]
        if por_mes:
            indice += ["", "## Agenda", ""]
            indice += [f"- {self._link(f'Agenda/{m}.md', _rotulo_mes(m))}" for m in sorted(por_mes)]
        if "Preferências.md" in plano.notas:
            indice += ["", f"## {self._link('Preferências.md', 'Preferências')}"]
        plano.notas["Nora Brain.md"] = _nota(
            {"nora_id": "indice", "nora_gerenciado": True, "tipo": "indice"},
            ["nora"],
            "\n".join(indice),
        )
        return plano


def _tag(texto: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _chave(texto)).strip("-") or "sem-area"


def _rotulo_area(area: str) -> str:
    return nome_de_arquivo(area[:1].upper() + area[1:], 40)


def _rotulo_mes(mes: str) -> str:
    return f"{NOMES_DOS_MESES[int(mes[5:7]) - 1]} de {mes[:4]}"


def _nota(propriedades: dict, tags: list[str], corpo: str) -> str:
    linhas = ["---"]
    linhas += [f"{chave}: {_yaml(valor)}" for chave, valor in propriedades.items()]
    linhas.append("tags:")
    linhas += [f"  - {_yaml(tag)}" for tag in tags]
    linhas += ["---", "", corpo.rstrip(), "", AVISO_DA_NOTA, ""]
    return "\n".join(linhas)


# --- escrever no vault, de forma incremental e segura -------------------------------------------


def escrever_atomico(caminho: Path, conteudo: str) -> None:
    """Escreve num arquivo temporário ao lado e troca de uma vez: uma queda no meio deixa o
    arquivo antigo inteiro, nunca pela metade."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(dir=caminho.parent, prefix=".nora-", suffix=".tmp")
    try:
        with os.fdopen(descritor, "w", encoding="utf-8", newline="\n") as arquivo:
            arquivo.write(conteudo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


class VaultAusente(Exception):
    """A pasta do vault (ou a de cima do Second Brain) não existe."""


@dataclass
class Resumo:
    escritas: int = 0
    removidas: int = 0
    conflitos: int = 0
    notas: int = 0
    interrompido: bool = False
    erro: str = ""


class Sincronizador:
    """Leva a memória para a pasta do Second Brain e grava o grafo e o mapa."""

    def __init__(self, config, destino: Path, prefixo_dos_links: str, vault: str = "") -> None:
        self.config = config
        self.destino = destino
        self.vault = vault  # nome do vault, para abrir a nota no Obsidian pelo mapa
        # A pasta que precisa existir antes: o vault (pasta relativa) ou a pasta acima dela
        # (caminho absoluto). Sem ela, não cria nada: um caminho errado na config não vira um
        # vault novo no lugar errado.
        relativa = not Path(config.segundo_cerebro.pasta).expanduser().is_absolute()
        self.base = Path(config.notas.pasta) if relativa else destino.parent
        self.pasta = config.pasta_dados / "segundo_cerebro"
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.planejador = Planejador(config, prefixo_dos_links)
        self._trava = threading.Lock()
        self._estado = sqlite3.connect(str(self.pasta / "estado.db"), check_same_thread=False)
        with self._estado:
            self._estado.executescript(
                """
                CREATE TABLE IF NOT EXISTS notas (caminho TEXT PRIMARY KEY, hash TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS conflitos (
                    caminho TEXT PRIMARY KEY, motivo TEXT NOT NULL, quando TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
                """
            )

    # estado ---------------------------------------------------------------------------------

    def _exportadas(self) -> dict[str, str]:
        return dict(self._estado.execute("SELECT caminho, hash FROM notas"))

    def _registrar(self, caminho: str, hash_: str | None) -> None:
        with self._estado:
            if hash_ is None:
                self._estado.execute("DELETE FROM notas WHERE caminho = ?", (caminho,))
            else:
                self._estado.execute(
                    "INSERT OR REPLACE INTO notas(caminho, hash) VALUES (?, ?)", (caminho, hash_)
                )
            self._estado.execute("DELETE FROM conflitos WHERE caminho = ?", (caminho,))

    def _conflito(self, caminho: str, motivo: str) -> None:
        with self._estado:
            self._estado.execute(
                "INSERT OR REPLACE INTO conflitos(caminho, motivo, quando) VALUES (?, ?, ?)",
                (caminho, motivo, datetime.now().isoformat(timespec="seconds")),
            )

    def _meta(self, **valores) -> None:
        with self._estado:
            for chave, valor in valores.items():
                self._estado.execute(
                    "INSERT OR REPLACE INTO meta(chave, valor) VALUES (?, ?)", (chave, str(valor))
                )

    def status(self) -> dict:
        meta = dict(self._estado.execute("SELECT chave, valor FROM meta"))
        conflitos = list(self._estado.execute("SELECT caminho, motivo FROM conflitos ORDER BY 1"))
        notas = self._estado.execute("SELECT COUNT(*) FROM notas").fetchone()[0]
        return {"meta": meta, "conflitos": conflitos, "notas": notas, "destino": self.destino}

    # sincronizar ----------------------------------------------------------------------------

    def sincronizar(self, pausar: Callable[[], bool] = lambda: False) -> Resumo:
        """Uma rodada: lê a memória, escreve o que mudou, apaga o que saiu dela e grava o grafo.
        `pausar` é consultado entre arquivos: se a Nora voltou a falar, para (e continua na
        próxima rodada, do ponto em que estiver)."""
        with self._trava:
            inicio = time.perf_counter()
            resumo = Resumo()
            try:
                if not self.base.is_dir():
                    raise VaultAusente(str(self.base))
                plano = self.planejador.planejar(
                    ler_memoria(self.config.pasta_dados / "memoria.db")
                )
                resumo.notas = len(plano.notas)
                exportadas = self._exportadas()
                for caminho, conteudo in plano.notas.items():
                    if pausar():
                        resumo.interrompido = True
                        break
                    self._aplicar(caminho, conteudo, exportadas.get(caminho), resumo)
                else:
                    for caminho, hash_ in exportadas.items():
                        if caminho in plano.notas:
                            continue
                        if pausar():
                            resumo.interrompido = True
                            break
                        self._remover(caminho, hash_, resumo)
                    if not resumo.interrompido:
                        self._gravar_grafo(plano.grafo)
                resumo.conflitos = self._estado.execute(
                    "SELECT COUNT(*) FROM conflitos"
                ).fetchone()[0]
            except Exception as erro:
                # Sem a mensagem: pode ter caminho ou trecho pessoal. Só o tipo do erro.
                resumo.erro = type(erro).__name__
                log.error("Second Brain: falha na sincronização (%s)", resumo.erro)
            self._meta(
                ultima_rodada=_agora(),
                ultima_duracao_ms=round((time.perf_counter() - inicio) * 1000),
                ultimo_erro=resumo.erro,
                **({} if resumo.erro or resumo.interrompido else {"ultima_completa": _agora()}),
            )
            return resumo

    def _aplicar(self, caminho: str, conteudo: str, exportado: str | None, resumo: Resumo) -> None:
        arquivo = self.destino / caminho
        novo = _hash(conteudo)
        if arquivo.exists():
            atual = _hash(arquivo.read_text(encoding="utf-8", errors="replace"))
            if atual == novo:  # já está certo (inclusive depois de uma queda no meio)
                if exportado != novo:
                    self._registrar(caminho, novo)
                return
            if exportado is None:
                self._conflito(caminho, "já existe uma nota sua com esse nome; não sobrescrevi")
                return
            if atual != exportado:
                self._conflito(caminho, "você editou esta nota; não atualizei")
                return
        escrever_atomico(arquivo, conteudo)
        self._registrar(caminho, novo)
        resumo.escritas += 1

    def _remover(self, caminho: str, exportado: str, resumo: Resumo) -> None:
        arquivo = self.destino / caminho
        if arquivo.exists():
            atual = _hash(arquivo.read_text(encoding="utf-8", errors="replace"))
            if atual != exportado:
                self._conflito(caminho, "a memória saiu, mas você editou a nota; não apaguei")
                return
            arquivo.unlink()
            resumo.removidas += 1
            pasta = arquivo.parent
            if pasta != self.destino and not any(pasta.iterdir()):
                pasta.rmdir()
        self._registrar(caminho, None)

    def _gravar_grafo(self, grafo: Grafo) -> None:
        dados = {
            "versao": VERSAO_DO_CONTRATO,
            "vault": self.vault,
            "prefixo": self.planejador.prefixo,
            # Caminho completo da pasta: o link "Abrir no Obsidian" usa ?path=, que acha o vault
            # sozinho (o nome da pasta de [notas] nem sempre é o nome do vault no Obsidian).
            "raiz": str(self.destino.resolve()),
            "nos": grafo.nos,
            "ligacoes": grafo.ligacoes,
            "legenda": {"areas": _legenda_das_areas(grafo), "emocoes": CORES_DAS_EMOCOES},
        }
        texto = json.dumps(dados, ensure_ascii=False, sort_keys=True)
        from nora.mapa_memoria import pagina

        # Compara o arquivo inteiro: uma versão nova da página ou da config também refaz o mapa.
        arquivos = {
            self.pasta / "grafo.json": texto,
            self.pasta / "mapa.html": pagina(
                texto, self.config.segundo_cerebro.mostrar_texto_no_mapa
            ),
        }
        for caminho, conteudo in arquivos.items():
            atual = caminho.read_text(encoding="utf-8") if caminho.exists() else None
            if atual != conteudo:
                escrever_atomico(caminho, conteudo)

    def fechar(self) -> None:
        with self._trava:
            self._estado.close()


def _legenda_das_areas(grafo: Grafo) -> dict[str, str]:
    areas = sorted({no["area"] for no in grafo.nos if no.get("area")})
    return {area: cor_da_area(area) for area in areas}


# --- linha em segundo plano ---------------------------------------------------------------------


class Trabalhador(threading.Thread):
    """Sincroniza quando avisado (a memória mudou) ou a cada `intervalo`, sempre esperando a
    Nora ficar livre. Nunca é chamado de dentro da resposta: a conversa só chama `avisar()`."""

    def __init__(
        self,
        sincronizador: Sincronizador,
        ocupado: Callable[[], bool],
        intervalo: float = 60.0,
        folga: float = 0.5,
    ) -> None:
        super().__init__(daemon=True, name="nora-segundo-cerebro")
        self.sincronizador = sincronizador
        self.ocupado = ocupado
        self.intervalo = intervalo
        self.folga = folga
        self._sinal = threading.Event()
        self._parar = threading.Event()
        self.rodadas = 0
        self.ultimo: Resumo | None = None

    def avisar(self) -> None:
        """A memória mudou. Não bloqueia: só levanta o sinal."""
        self._sinal.set()

    def _pausar(self) -> bool:
        return self._parar.is_set() or self.ocupado()

    def run(self) -> None:
        self._sinal.set()  # uma rodada ao abrir: pega o que mudou com a Nora fechada
        while not self._parar.is_set():
            self._sinal.wait(self.intervalo)
            self._sinal.clear()
            while self.ocupado() and not self._parar.is_set():
                self._parar.wait(self.folga)  # respondendo ou falando: espera
            if self._parar.is_set():
                break
            try:
                self.ultimo = self.sincronizador.sincronizar(pausar=self._pausar)
            except Exception as erro:
                log.error("Second Brain: falha (%s)", type(erro).__name__)
                continue
            self.rodadas += 1
            if self.ultimo.interrompido:
                self._sinal.set()  # a Nora voltou a falar no meio: tenta de novo depois

    def encerrar(self, espera: float = 15.0) -> None:
        """Ao fechar a Nora: para a linha e faz uma última rodada (fora da conversa)."""
        self._parar.set()
        self._sinal.set()
        self.join(espera)
        try:
            self.sincronizador.sincronizar()
        except Exception:
            pass
        self.sincronizador.fechar()


# --- abrir pela config --------------------------------------------------------------------------


def destino(config) -> tuple[Path, str, str] | None:
    """(pasta do Second Brain, prefixo dos links no vault, nome do vault), ou None se não dá
    para saber onde (pasta relativa sem [notas] pasta)."""
    pasta = Path(config.segundo_cerebro.pasta).expanduser()
    vault = config.notas.pasta
    if pasta.is_absolute():
        if vault is not None:
            try:
                relativo = pasta.resolve().relative_to(Path(vault).resolve())
                return pasta, relativo.as_posix(), Path(vault).name
            except ValueError:
                pass
        return pasta, "", pasta.name
    if vault is None:
        return None
    return Path(vault) / pasta, pasta.as_posix(), Path(vault).name


def abrir_sincronizador(config) -> Sincronizador | None:
    if not config.segundo_cerebro.ativo:
        return None
    onde = destino(config)
    if onde is None:
        return None
    return Sincronizador(config, *onde)


def iniciar(conversa) -> Trabalhador | None:
    """Liga o Second Brain na conversa, se estiver ativo e houver memória. Nunca levanta erro:
    sem Second Brain, a conversa segue igual."""
    config = conversa.config
    if conversa.memoria is None or not config.segundo_cerebro.ativo:
        return None
    try:
        sincronizador = abrir_sincronizador(config)
    except Exception as erro:
        log.error("Second Brain: não abriu (%s)", type(erro).__name__)
        return None
    if sincronizador is None:
        return None
    trabalhador = Trabalhador(
        sincronizador,
        ocupado=lambda: bool(conversa.ocupada or conversa.falando),
        intervalo=config.segundo_cerebro.intervalo_s,
    )
    conversa.segundo_cerebro = trabalhador
    trabalhador.start()
    return trabalhador


def caminho_do_mapa(config) -> Path:
    return config.pasta_dados / "segundo_cerebro" / "mapa.html"
