"""Memory across conversations (v0.2.0), with meaning-based search, in layers:

- facts: short summaries noted by curation ("Ana tem prova em 21/11");
- exchanges: each whole question and answer, so she remembers everything that was said;
- agenda: the facts with a date (exam, trip, birthday), to find them by day ("amanhã");
- pronunciations and preferences: what the person taught about how Nora should speak.

Each item has a vector (embedding). Before answering, Nora searches the facts and the
conversation passages most similar to the question and reads them along. Everything lives in
<dados>/memoria.db, only on the person's machine.

Search uses sqlite-vec when it is installed (`pip install -e ".[memoria]"`); without it, it
compares the vectors in Python, which is enough for a few thousand facts.
"""

from __future__ import annotations

import math
import sqlite3
import struct
import threading
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from nora.agenda import Evento, datas_no_texto, ocorrencia

# Above this, two facts are considered the same; the newer replaces the older.
MESMO_FATO = 0.9
# After an "esquece isso": a conversation passage this similar to what was forgotten
# does not come back in searches, and a fact this similar does not come back through import.
TROCA_ESQUECIDA = 0.6
FATO_ESQUECIDO = 0.85


# After this, a pending answer is no longer resumed (so it does not waste API calls).
MAX_TENTATIVAS = 3


@dataclass(frozen=True)
class Pendente:
    """An answer left halfway (or never started) that can be resumed."""

    id: int
    interacao: str
    sessao: str
    pergunta: str
    parcial: str
    motivo: str  # stream_interrompido, sem_resposta, erro_provedor, cancelada, encerramento
    provedor: str
    criada: str
    status: str  # aberta, pendente, em_recuperacao, resolvida, cancelada
    tentativas: int


@dataclass(frozen=True)
class Apagamento:
    """What "apagar de vez" removes (or would remove, in the preview) from memory."""

    fatos: list
    trocas: list
    textos: set[str]  # deleted questions and answers, to remove them from the history too


@dataclass(frozen=True)
class Troca:
    id: int
    quando: str
    sessao: str
    pergunta: str
    resposta: str
    similaridade: float = 0.0


@dataclass(frozen=True)
class Fato:
    id: int
    texto: str
    criado: str
    atualizado: str
    area: str = ""
    similaridade: float = 0.0


def _empacotar(vetor: list[float]) -> bytes:
    return struct.pack(f"<{len(vetor)}f", *vetor)


def _desempacotar(dados: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(dados) // 4}f", dados))


def _cosseno(a: list[float], b: list[float]) -> float:
    norma = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norma if norma else 0.0


def _contem(texto: str | None, trecho: str | None) -> int:
    """Whether the text contains the substring, ignoring case (accented capitals included) and
    without wildcards."""
    return int(bool(texto) and (trecho or "").casefold() in texto.casefold())


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Memoria:
    def __init__(self, caminho: Path, embeddings) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho = caminho
        self.embeddings = embeddings
        self._trava = threading.RLock()
        self._db = sqlite3.connect(str(caminho), check_same_thread=False)
        # Substring search: SQLite's LIKE only ignores case for unaccented letters ("Á" ≠ "á") and
        # treats "_" and "%" as wildcards. contem() compares in Python, with casefold and no
        # wildcards.
        self._db.create_function("contem", 2, _contem, deterministic=True)
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT);
            CREATE TABLE IF NOT EXISTS fatos (
                id INTEGER PRIMARY KEY,
                texto TEXT NOT NULL,
                vetor BLOB NOT NULL,
                criado TEXT NOT NULL,
                atualizado TEXT NOT NULL,
                origem TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS trocas (
                id INTEGER PRIMARY KEY,
                quando TEXT NOT NULL,
                sessao TEXT NOT NULL,
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                vetor BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL,
                anual INTEGER NOT NULL DEFAULT 0,
                texto TEXT NOT NULL,
                area TEXT NOT NULL DEFAULT '',
                fato_id INTEGER,
                criado TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS agenda_data ON agenda(data);
            CREATE TABLE IF NOT EXISTS pronuncias (
                palavra TEXT PRIMARY KEY,
                fala TEXT NOT NULL,
                criado TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS preferencias (
                id INTEGER PRIMARY KEY,
                texto TEXT NOT NULL UNIQUE,
                criado TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS respostas_pendentes (
                id INTEGER PRIMARY KEY,
                interacao TEXT NOT NULL UNIQUE,
                sessao TEXT NOT NULL,
                pergunta TEXT NOT NULL,
                parcial TEXT NOT NULL DEFAULT '',
                motivo TEXT NOT NULL DEFAULT '',
                provedor TEXT NOT NULL DEFAULT '',
                criada TEXT NOT NULL,
                atualizada TEXT NOT NULL,
                status TEXT NOT NULL,
                tentativas INTEGER NOT NULL DEFAULT 0,
                resultado TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS esquecidos (
                id INTEGER PRIMARY KEY,
                texto TEXT NOT NULL,
                vetor BLOB NOT NULL,
                quando TEXT NOT NULL
            );
            """
        )
        colunas = {linha[1] for linha in self._db.execute("PRAGMA table_info(fatos)")}
        if "area" not in colunas:  # databases created before areas
            self._db.execute("ALTER TABLE fatos ADD COLUMN area TEXT NOT NULL DEFAULT ''")
            self._db.commit()
        self.vetorial = self._carregar_sqlite_vec()
        if self.meta("agenda_preenchida") is None:  # databases from before the agenda
            self.preencher_agenda()

    # --- vector index ---------------------------------------------------------------------

    def _carregar_sqlite_vec(self) -> bool:
        try:
            import sqlite_vec

            self._db.enable_load_extension(True)
            sqlite_vec.load(self._db)
            self._db.enable_load_extension(False)
            return True
        except (ImportError, AttributeError, sqlite3.Error):
            return False

    def _existe(self, tabela: str) -> bool:
        return bool(
            self._db.execute("SELECT 1 FROM sqlite_master WHERE name = ?", (tabela,)).fetchone()
        )

    def _garantir_indice(self, dimensao: int) -> None:
        """Creates the sqlite-vec indexes (facts and exchanges) when the vector dimension is
        known, and recreates them if it changes (e.g. another embeddings model)."""
        if not self.vetorial:
            return
        mesma = self.meta("dimensao") == str(dimensao)
        for tabela in ("fatos", "trocas"):
            indice = f"vec_{tabela}"
            if mesma and self._existe(indice):
                continue
            self._db.execute(f"DROP TABLE IF EXISTS {indice}")
            self._db.execute(
                f"CREATE VIRTUAL TABLE {indice} USING vec0("
                f"embedding float[{dimensao}] distance_metric=cosine)"
            )
            for item_id, vetor in self._db.execute(f"SELECT id, vetor FROM {tabela}").fetchall():
                if len(vetor) // 4 == dimensao:
                    self._db.execute(
                        f"INSERT INTO {indice}(rowid, embedding) VALUES (?, ?)", (item_id, vetor)
                    )
        self.definir_meta("dimensao", str(dimensao))

    # --- meta -----------------------------------------------------------------------------

    def meta(self, chave: str) -> str | None:
        with self._trava:
            linha = self._db.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
        return linha[0] if linha else None

    def definir_meta(self, chave: str, valor: str) -> None:
        with self._trava, self._db:
            self._db.execute(
                "INSERT INTO meta(chave, valor) VALUES (?, ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                (chave, valor),
            )

    # --- facts ----------------------------------------------------------------------------

    def _parecidos(
        self, vetor: list[float], k: int, tabela: str = "fatos"
    ) -> list[tuple[int, float]]:
        indice = f"vec_{tabela}"
        if self.vetorial and self.meta("dimensao") == str(len(vetor)) and self._existe(indice):
            linhas = self._db.execute(
                f"SELECT rowid, distance FROM {indice} WHERE embedding MATCH ? AND k = ? "
                "ORDER BY distance",
                (_empacotar(vetor), k),
            ).fetchall()
            # null distance: a vector with no direction (e.g. text without words); counts as nothing
            # similar
            return [
                (item_id, 0.0 if distancia is None else 1.0 - distancia)
                for item_id, distancia in linhas
            ]
        todos = [
            (item_id, _cosseno(vetor, _desempacotar(dados)))
            for item_id, dados in self._db.execute(f"SELECT id, vetor FROM {tabela}").fetchall()
            if len(dados) // 4 == len(vetor)
        ]
        return sorted(todos, key=lambda par: par[1], reverse=True)[:k]

    # --- areas -----------------------------------------------------------------------------

    def areas(self) -> list[tuple[str, int]]:
        """The memory areas (saúde, trabalho...) with how many facts each one has."""
        with self._trava:
            return self._db.execute(
                "SELECT area, COUNT(*) FROM fatos WHERE area != '' GROUP BY area "
                "ORDER BY COUNT(*) DESC, area"
            ).fetchall()

    def normalizar_area(self, area: str) -> str:
        """Short lowercase name; if an area with the same name already exists (ignoring accents),
        uses the existing one: "Saude" becomes "saúde" if "saúde" already exists."""
        from nora.ativacao import normalizar

        area = " ".join(area.lower().split())[:40]
        if not area:
            return ""
        chave = normalizar(area)
        for existente, _ in self.areas():
            if normalizar(existente) == chave:
                return existente
        return area

    # --- facts ----------------------------------------------------------------------------

    def lembrar(self, texto: str, origem: str = "", area: str = "") -> tuple[int, bool]:
        """Stores a fact in the given area. If a near-identical one exists, replaces it with the new
        text. Returns (id, whether it is a new fact)."""
        texto = " ".join(texto.split())
        vetor = self.embeddings.vetor(texto)
        area = self.normalizar_area(area)
        with self._trava, self._db:
            esquecidos = self._esquecidos_parecidos(vetor, FATO_ESQUECIDO)
            if esquecidos and origem.startswith("historico"):
                # the person asked to forget: an old conversation does not bring it back
                return 0, False
            for esquecido_id in esquecidos:  # told again in a new conversation: it counts again
                self._db.execute("DELETE FROM esquecidos WHERE id = ?", (esquecido_id,))
            self._garantir_indice(len(vetor))
            agora = _agora()
            parecido = self._parecidos(vetor, 1)
            if parecido and parecido[0][1] >= MESMO_FATO:
                fato_id = parecido[0][0]
                self._db.execute(
                    "UPDATE fatos SET texto = ?, vetor = ?, atualizado = ?, "
                    "area = CASE WHEN ? != '' THEN ? ELSE area END WHERE id = ?",
                    (texto, _empacotar(vetor), agora, area, area, fato_id),
                )
                if self.vetorial:
                    self._db.execute("DELETE FROM vec_fatos WHERE rowid = ?", (fato_id,))
                    self._db.execute(
                        "INSERT INTO vec_fatos(rowid, embedding) VALUES (?, ?)",
                        (fato_id, _empacotar(vetor)),
                    )
                return fato_id, False
            cursor = self._db.execute(
                "INSERT INTO fatos(texto, vetor, criado, atualizado, origem, area) "
                "VALUES (?,?,?,?,?,?)",
                (texto, _empacotar(vetor), agora, agora, origem, area),
            )
            fato_id = cursor.lastrowid
            if self.vetorial:
                self._db.execute(
                    "INSERT INTO vec_fatos(rowid, embedding) VALUES (?, ?)",
                    (fato_id, _empacotar(vetor)),
                )
            return fato_id, True

    def buscar(self, texto: str, k: int = 5, minimo: float = 0.0) -> list[Fato]:
        """The facts most similar to the text, from most to least similar."""
        if k <= 0 or not self.contar():
            return []
        vetor = self.embeddings.vetor(texto)
        with self._trava:
            achados = [(i, s) for i, s in self._parecidos(vetor, k) if s >= minimo]
            fatos = []
            for fato_id, similaridade in achados:
                linha = self._db.execute(
                    "SELECT id, texto, criado, atualizado, area FROM fatos WHERE id = ?",
                    (fato_id,),
                ).fetchone()
                if linha:
                    fatos.append(Fato(*linha, similaridade=similaridade))
            return fatos

    @staticmethod
    def _filtro(contendo: str, area: str) -> tuple[str, list]:
        condicoes, parametros = [], []
        if contendo:
            condicoes.append("contem(texto, ?)")
            parametros.append(contendo)
        if area:
            condicoes.append("area = ?")
            parametros.append(area)
        return (" WHERE " + " AND ".join(condicoes) if condicoes else ""), parametros

    def listar(
        self, limite: int | None = None, pular: int = 0, contendo: str = "", area: str = ""
    ) -> list[Fato]:
        """Facts from newest to oldest; `contendo` filters by a substring of the text and `area` by
        an area."""
        filtro, parametros = self._filtro(contendo, self.normalizar_area(area))
        consulta = "SELECT id, texto, criado, atualizado, area FROM fatos" + filtro
        consulta += " ORDER BY atualizado DESC, id DESC LIMIT ? OFFSET ?"
        parametros += [-1 if limite is None else limite, pular]
        with self._trava:
            linhas = self._db.execute(consulta, parametros).fetchall()
        return [Fato(*linha) for linha in linhas]

    def contar_contendo(self, contendo: str = "", area: str = "") -> int:
        filtro, parametros = self._filtro(contendo, self.normalizar_area(area))
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM fatos" + filtro, parametros).fetchone()[0]

    def esquecer_parecido(self, texto: str, minimo: float = 0.75) -> list[Fato]:
        """Stops using what was asked to be forgotten: deletes the fact most similar to the text
        (and others nearly identical to it) and records the request, so passages of old
        conversations about it come back neither in searches nor through import. The stored
        conversations stay in the history; to remove them from there too, use apagar_de_vez. Returns
        the deleted facts."""
        apagados = self._fatos_para_esquecer(texto, minimo)
        for fato in apagados:
            self.esquecer(fato.id)
        for item in [texto, *(f.texto for f in apagados)]:
            self._anotar_esquecido(item)
        self._apagar_pendencias_sobre(texto)
        return apagados

    def _fatos_para_esquecer(self, texto: str, minimo: float) -> list[Fato]:
        achados = self.buscar(texto, k=3, minimo=minimo)
        if not achados:
            return []
        return [achados[0]] + [f for f in achados[1:] if f.similaridade >= MESMO_FATO]

    def apagar_de_vez(
        self, texto: str, confirmar: bool = False, minimo: float = 0.75
    ) -> Apagamento:
        """Removes from memory the facts and conversation passages about the text. Without
        `confirmar`, only shows what would go. The file history is cleaned separately, with the
        returned `textos` (historico.apagar_do_historico)."""
        fatos = self._fatos_para_esquecer(texto, minimo)
        vetor = self.embeddings.vetor(texto)
        with self._trava:
            trocas = [
                Troca(troca_id, quando, sessao, pergunta, resposta, similaridade)
                for troca_id, quando, sessao, pergunta, resposta, dados in self._db.execute(
                    "SELECT id, quando, sessao, pergunta, resposta, vetor FROM trocas"
                )
                if len(dados) // 4 == len(vetor)
                and (similaridade := _cosseno(vetor, _desempacotar(dados))) >= TROCA_ESQUECIDA
            ]
        textos = {t.pergunta for t in trocas} | {t.resposta for t in trocas}
        if confirmar:
            for fato in fatos:
                self.esquecer(fato.id)
            with self._trava, self._db:
                for troca in trocas:
                    self._db.execute("DELETE FROM trocas WHERE id = ?", (troca.id,))
                    if self.vetorial and self.meta("dimensao"):
                        self._db.execute("DELETE FROM vec_trocas WHERE rowid = ?", (troca.id,))
            self._anotar_esquecido(texto)
            self._apagar_pendencias_sobre(texto)
        return Apagamento(fatos, trocas, textos)

    # --- pending answers (half-finished, cancelled, or lost when the program crashed) ---------

    _CAMPOS_PENDENTE = (
        "id, interacao, sessao, pergunta, parcial, motivo, provedor, criada, status, tentativas"
    )

    def abrir_resposta(self, interacao: str, sessao: str, pergunta: str) -> None:
        """Marks that an answer started. If the program crashes before it finishes, it becomes a
        pending item next time (recuperar_abertas). Once finished, it goes away
        (concluir_resposta)."""
        agora = _agora()
        with self._trava, self._db:
            self._db.execute(
                "INSERT OR IGNORE INTO respostas_pendentes"
                "(interacao, sessao, pergunta, criada, atualizada, status) "
                "VALUES (?, ?, ?, ?, ?, 'aberta')",
                (interacao, sessao, pergunta, agora, agora),
            )

    def concluir_resposta(self, interacao: str) -> None:
        with self._trava, self._db:
            self._db.execute(
                "DELETE FROM respostas_pendentes WHERE interacao = ? AND status = 'aberta'",
                (interacao,),
            )

    def marcar_pendente(
        self, interacao: str, sessao: str, pergunta: str, parcial: str, motivo: str, provedor: str
    ) -> None:
        """The answer did not finish: stores the question and the part that came out (never as a
        fact)."""
        agora = _agora()
        with self._trava, self._db:
            self._db.execute(
                "INSERT INTO respostas_pendentes(interacao, sessao, pergunta, parcial, motivo, "
                "provedor, criada, atualizada, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pendente') "
                "ON CONFLICT(interacao) DO UPDATE SET parcial = excluded.parcial, "
                "motivo = excluded.motivo, provedor = excluded.provedor, "
                "atualizada = excluded.atualizada, status = 'pendente'",
                (interacao, sessao, pergunta, parcial, motivo, provedor, agora, agora),
            )

    def recuperar_abertas(self, exceto_sessao: str) -> int:
        """Open answers from other sessions: the program crashed midway. They become pending
        items."""
        with self._trava, self._db:
            return self._db.execute(
                "UPDATE respostas_pendentes SET status = 'pendente', motivo = 'encerramento', "
                "atualizada = ? WHERE status = 'aberta' AND sessao != ?",
                (_agora(), exceto_sessao),
            ).rowcount

    def pendentes(self) -> list[Pendente]:
        """The ones that can still be resumed, from newest to oldest."""
        with self._trava:
            linhas = self._db.execute(
                f"SELECT {self._CAMPOS_PENDENTE} FROM respostas_pendentes "
                "WHERE status IN ('pendente', 'em_recuperacao') ORDER BY id DESC"
            ).fetchall()
        return [Pendente(*linha) for linha in linhas]

    def tentar_pendencia(self, pendente_id: int) -> int:
        """Counts a new attempt; after MAX_TENTATIVAS it is cancelled. Returns the total."""
        with self._trava, self._db:
            self._db.execute(
                "UPDATE respostas_pendentes SET tentativas = tentativas + 1, "
                "status = CASE WHEN tentativas + 1 >= ? THEN 'cancelada' ELSE 'em_recuperacao' END,"
                " atualizada = ? WHERE id = ?",
                (MAX_TENTATIVAS, _agora(), pendente_id),
            )
            linha = self._db.execute(
                "SELECT tentativas FROM respostas_pendentes WHERE id = ?", (pendente_id,)
            ).fetchone()
        return linha[0] if linha else 0

    def resolver_pendencia(self, pendente_id: int, resultado: str = "") -> None:
        with self._trava, self._db:
            self._db.execute(
                "UPDATE respostas_pendentes SET status = 'resolvida', resultado = ?, "
                "atualizada = ? WHERE id = ?",
                (resultado, _agora(), pendente_id),
            )

    def cancelar_pendencia(self, pendente_id: int) -> bool:
        with self._trava, self._db:
            return (
                self._db.execute(
                    "UPDATE respostas_pendentes SET status = 'cancelada', atualizada = ? "
                    "WHERE id = ? AND status IN ('pendente', 'em_recuperacao')",
                    (_agora(), pendente_id),
                ).rowcount
                > 0
            )

    def _apagar_pendencias_sobre(self, texto: str) -> None:
        """Forgetting or deleting a subject also removes the pending items about it."""
        vetor = self.embeddings.vetor(texto)
        with self._trava:
            linhas = self._db.execute("SELECT id, pergunta FROM respostas_pendentes").fetchall()
        apagar = [
            pendente_id
            for pendente_id, pergunta in linhas
            if _cosseno(vetor, self.embeddings.vetor(pergunta)) >= TROCA_ESQUECIDA
        ]
        with self._trava, self._db:
            for pendente_id in apagar:
                self._db.execute("DELETE FROM respostas_pendentes WHERE id = ?", (pendente_id,))

    def _anotar_esquecido(self, texto: str) -> None:
        vetor = self.embeddings.vetor(texto)
        with self._trava, self._db:
            self._db.execute(
                "INSERT INTO esquecidos(texto, vetor, quando) VALUES (?, ?, ?)",
                (texto, _empacotar(vetor), _agora()),
            )

    def _esquecidos_parecidos(self, vetor: list[float], minimo: float) -> list[int]:
        """The forget requests similar to the vector (ids)."""
        return [
            esquecido_id
            for esquecido_id, dados in self._db.execute("SELECT id, vetor FROM esquecidos")
            if len(dados) // 4 == len(vetor) and _cosseno(vetor, _desempacotar(dados)) >= minimo
        ]

    def esquecer(self, fato_id: int) -> bool:
        with self._trava, self._db:
            apagados = self._db.execute("DELETE FROM fatos WHERE id = ?", (fato_id,)).rowcount
            self._db.execute("DELETE FROM agenda WHERE fato_id = ?", (fato_id,))
            if self.vetorial and self.meta("dimensao"):
                self._db.execute("DELETE FROM vec_fatos WHERE rowid = ?", (fato_id,))
            return apagados > 0

    # --- agenda (facts with a date) ------------------------------------------------------

    def marcar(
        self,
        data: date,
        texto: str,
        anual: bool = False,
        area: str = "",
        fato_id: int | None = None,
    ) -> int:
        """Puts an event in the agenda. If it comes from a fact that already had a date, replaces
        the old one."""
        texto = " ".join(texto.split())
        with self._trava, self._db:
            if fato_id is not None:
                self._db.execute("DELETE FROM agenda WHERE fato_id = ?", (fato_id,))
            else:
                self._db.execute(
                    "DELETE FROM agenda WHERE data = ? AND texto = ?", (data.isoformat(), texto)
                )
            cursor = self._db.execute(
                "INSERT INTO agenda(data, anual, texto, area, fato_id, criado) "
                "VALUES (?,?,?,?,?,?)",
                (data.isoformat(), int(anual), texto, area, fato_id, _agora()),
            )
            return cursor.lastrowid

    def marcar_do_fato(
        self, fato_id: int, texto: str, area: str = "", hoje: date | None = None
    ) -> list[int]:
        """Puts in the agenda the dates written in the fact's text ("prova em 21/11")."""
        datas = datas_no_texto(texto, hoje or date.today())
        if not datas:
            return []
        with self._trava, self._db:
            self._db.execute("DELETE FROM agenda WHERE fato_id = ?", (fato_id,))
            ids = []
            for data, anual in datas:
                cursor = self._db.execute(
                    "INSERT INTO agenda(data, anual, texto, area, fato_id, criado) "
                    "VALUES (?,?,?,?,?,?)",
                    (data.isoformat(), int(anual), texto, area, fato_id, _agora()),
                )
                ids.append(cursor.lastrowid)
            return ids

    def preencher_agenda(self, hoje: date | None = None) -> int:
        """Runs the pre-existing facts through the agenda (once, on old databases)."""
        with self._trava:
            fatos = self._db.execute(
                "SELECT id, texto, area FROM fatos WHERE id NOT IN "
                "(SELECT fato_id FROM agenda WHERE fato_id IS NOT NULL)"
            ).fetchall()
        marcados = sum(bool(self.marcar_do_fato(i, texto, area, hoje)) for i, texto, area in fatos)
        self.definir_meta("agenda_preenchida", _agora())
        return marcados

    def _eventos(self, linhas) -> list[Evento]:
        return [
            Evento(i, date.fromisoformat(d), texto, bool(anual), area, fato_id)
            for i, d, anual, texto, area, fato_id in linhas
        ]

    def agenda(self, inicio: date, fim: date) -> list[tuple[date, Evento]]:
        """The events that fall in the period, in date order (yearly ones, in the period's year)."""
        with self._trava:
            linhas = self._db.execute(
                "SELECT id, data, anual, texto, area, fato_id FROM agenda "
                "WHERE anual = 1 OR (data >= ? AND data <= ?)",
                (inicio.isoformat(), fim.isoformat()),
            ).fetchall()
        achados = []
        for evento in self._eventos(linhas):
            dia = ocorrencia(evento, inicio, fim)
            if dia:
                achados.append((dia, evento))
        return sorted(achados, key=lambda par: (par[0], par[1].id))

    def eventos_contendo(self, trecho: str) -> list[Evento]:
        """Events whose text contains the substring (ignoring case), oldest first."""
        with self._trava:
            linhas = self._db.execute(
                "SELECT id, data, anual, texto, area, fato_id FROM agenda "
                "WHERE contem(texto, ?) ORDER BY data",
                (trecho,),
            ).fetchall()
        return self._eventos(linhas)

    def desmarcar(self, evento_id: int) -> bool:
        with self._trava, self._db:
            return self._db.execute("DELETE FROM agenda WHERE id = ?", (evento_id,)).rowcount > 0

    def contar_agenda(self) -> int:
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM agenda").fetchone()[0]

    # --- how to speak: pronunciations and preferences ------------------------------------

    def ensinar_pronuncia(self, palavra: str, fala: str) -> bool:
        """Stores how to say a word ("hoje" -> "ôje"). Returns whether it is new."""
        palavra, fala = " ".join(palavra.split()).lower(), " ".join(fala.split())
        if not palavra or not fala or palavra == fala.lower():
            return False
        with self._trava, self._db:
            existia = self._db.execute(
                "SELECT 1 FROM pronuncias WHERE palavra = ?", (palavra,)
            ).fetchone()
            self._db.execute(
                "INSERT INTO pronuncias(palavra, fala, criado) VALUES (?, ?, ?) "
                "ON CONFLICT(palavra) DO UPDATE SET fala = excluded.fala",
                (palavra, fala, _agora()),
            )
            return existia is None

    def pronuncias(self) -> dict[str, str]:
        with self._trava:
            return dict(self._db.execute("SELECT palavra, fala FROM pronuncias ORDER BY palavra"))

    def esquecer_pronuncia(self, palavra: str) -> bool:
        with self._trava, self._db:
            return (
                self._db.execute(
                    "DELETE FROM pronuncias WHERE palavra = ?", (palavra.strip().lower(),)
                ).rowcount
                > 0
            )

    def preferir(self, texto: str) -> tuple[int, bool]:
        """Stores a preference about the way of speaking. Returns (number, whether it is new)."""
        texto = " ".join(texto.split())
        with self._trava, self._db:
            linha = self._db.execute(
                "SELECT id FROM preferencias WHERE texto = ?", (texto,)
            ).fetchone()
            if linha:
                return linha[0], False
            cursor = self._db.execute(
                "INSERT INTO preferencias(texto, criado) VALUES (?, ?)", (texto, _agora())
            )
            return cursor.lastrowid, True

    def preferencias(self) -> list[tuple[int, str]]:
        with self._trava:
            return self._db.execute("SELECT id, texto FROM preferencias ORDER BY id").fetchall()

    def esquecer_preferencia(self, preferencia_id: int) -> bool:
        with self._trava, self._db:
            return (
                self._db.execute(
                    "DELETE FROM preferencias WHERE id = ?", (preferencia_id,)
                ).rowcount
                > 0
            )

    # --- exchanges (everything that was said) ---------------------------------------------

    def guardar_troca(self, pergunta: str, resposta: str, quando: str, sessao: str) -> int:
        """Stores a whole question and answer, to be remembered later."""
        vetor = self.embeddings.vetor(f"{pergunta}\n{resposta}")
        with self._trava, self._db:
            self._garantir_indice(len(vetor))
            cursor = self._db.execute(
                "INSERT INTO trocas(quando, sessao, pergunta, resposta, vetor) VALUES (?,?,?,?,?)",
                (quando, sessao, pergunta, resposta, _empacotar(vetor)),
            )
            if self.vetorial:
                self._db.execute(
                    "INSERT INTO vec_trocas(rowid, embedding) VALUES (?, ?)",
                    (cursor.lastrowid, _empacotar(vetor)),
                )
            return cursor.lastrowid

    def buscar_trocas(
        self, texto: str, k: int = 3, minimo: float = 0.0, exceto_sessao: str = ""
    ) -> list[Troca]:
        """The conversation passages most similar to the text (without those from the current
        session, which are already in the conversation)."""
        if k <= 0 or not self.contar_trocas():
            return []
        vetor = self.embeddings.vetor(texto)
        with self._trava:
            achados = self._parecidos(vetor, k * 4 + 10, "trocas")
            esquecidos = [
                _desempacotar(dados)
                for (dados,) in self._db.execute("SELECT vetor FROM esquecidos")
            ]
            trocas = []
            for troca_id, similaridade in achados:
                if similaridade < minimo:
                    continue
                linha = self._db.execute(
                    "SELECT id, quando, sessao, pergunta, resposta, vetor FROM trocas WHERE id = ?",
                    (troca_id,),
                ).fetchone()
                if not linha or linha[2] == exceto_sessao:
                    continue
                vetor_troca = _desempacotar(linha[5])
                if any(  # the person asked to forget this
                    len(e) == len(vetor_troca) and _cosseno(e, vetor_troca) >= TROCA_ESQUECIDA
                    for e in esquecidos
                ):
                    continue
                trocas.append(Troca(*linha[:5], similaridade=similaridade))
                if len(trocas) == k:
                    break
            return trocas

    def contar_trocas(self) -> int:
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM trocas").fetchone()[0]

    def contar(self) -> int:
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM fatos").fetchone()[0]

    def fechar(self) -> None:
        with self._trava:
            self._db.close()


def abrir_memoria(config) -> Memoria | None:
    """The config's memory, or None if it is off."""
    if not config.memoria.ativa:
        return None
    from nora.embeddings import EmbeddingsOllama

    return Memoria(config.pasta_dados / "memoria.db", EmbeddingsOllama(config))
