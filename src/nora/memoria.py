"""Memória entre conversas (v0.2.0): fatos sobre a pessoa, com busca por significado.

Cada fato tem um vetor (embedding). Antes de responder, a Nora busca os fatos mais parecidos
com a pergunta e os lê junto. Fica tudo em <dados>/memoria.db, só na máquina da pessoa.

A busca usa o sqlite-vec quando ele está instalado (`pip install -e ".[memoria]"`); sem ele,
compara os vetores em Python, o que basta para alguns milhares de fatos.
"""

from __future__ import annotations

import math
import sqlite3
import struct
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Acima disso, dois fatos são considerados o mesmo; o mais novo substitui o antigo.
MESMO_FATO = 0.9


@dataclass(frozen=True)
class Fato:
    id: int
    texto: str
    criado: str
    atualizado: str
    similaridade: float = 0.0


def _empacotar(vetor: list[float]) -> bytes:
    return struct.pack(f"<{len(vetor)}f", *vetor)


def _desempacotar(dados: bytes) -> list[float]:
    return list(struct.unpack(f"<{len(dados) // 4}f", dados))


def _cosseno(a: list[float], b: list[float]) -> float:
    norma = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norma if norma else 0.0


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Memoria:
    def __init__(self, caminho: Path, embeddings) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho = caminho
        self.embeddings = embeddings
        self._trava = threading.RLock()
        self._db = sqlite3.connect(str(caminho), check_same_thread=False)
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
            """
        )
        self.vetorial = self._carregar_sqlite_vec()

    # --- índice vetorial ------------------------------------------------------------------

    def _carregar_sqlite_vec(self) -> bool:
        try:
            import sqlite_vec

            self._db.enable_load_extension(True)
            sqlite_vec.load(self._db)
            self._db.enable_load_extension(False)
            return True
        except (ImportError, AttributeError, sqlite3.Error):
            return False

    def _garantir_indice(self, dimensao: int) -> None:
        """Cria o índice do sqlite-vec na primeira vez que a dimensão dos vetores é conhecida."""
        if not self.vetorial:
            return
        atual = self.meta("dimensao")
        if atual == str(dimensao):
            return
        self._db.execute("DROP TABLE IF EXISTS vec_fatos")
        self._db.execute(
            f"CREATE VIRTUAL TABLE vec_fatos USING vec0("
            f"embedding float[{dimensao}] distance_metric=cosine)"
        )
        for fato_id, vetor in self._db.execute("SELECT id, vetor FROM fatos").fetchall():
            if len(vetor) // 4 == dimensao:
                self._db.execute(
                    "INSERT INTO vec_fatos(rowid, embedding) VALUES (?, ?)", (fato_id, vetor)
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

    # --- fatos ----------------------------------------------------------------------------

    def _parecidos(self, vetor: list[float], k: int) -> list[tuple[int, float]]:
        if self.vetorial and self.meta("dimensao") == str(len(vetor)):
            linhas = self._db.execute(
                "SELECT rowid, distance FROM vec_fatos WHERE embedding MATCH ? AND k = ? "
                "ORDER BY distance",
                (_empacotar(vetor), k),
            ).fetchall()
            return [(fato_id, 1.0 - distancia) for fato_id, distancia in linhas]
        todos = [
            (fato_id, _cosseno(vetor, _desempacotar(dados)))
            for fato_id, dados in self._db.execute("SELECT id, vetor FROM fatos").fetchall()
            if len(dados) // 4 == len(vetor)
        ]
        return sorted(todos, key=lambda par: par[1], reverse=True)[:k]

    def lembrar(self, texto: str, origem: str = "") -> tuple[int, bool]:
        """Guarda um fato. Se já existe um quase igual, troca pelo novo texto.
        Devolve (id, se é um fato novo)."""
        texto = " ".join(texto.split())
        vetor = self.embeddings.vetor(texto)
        with self._trava, self._db:
            self._garantir_indice(len(vetor))
            agora = _agora()
            parecido = self._parecidos(vetor, 1)
            if parecido and parecido[0][1] >= MESMO_FATO:
                fato_id = parecido[0][0]
                self._db.execute(
                    "UPDATE fatos SET texto = ?, vetor = ?, atualizado = ? WHERE id = ?",
                    (texto, _empacotar(vetor), agora, fato_id),
                )
                if self.vetorial:
                    self._db.execute("DELETE FROM vec_fatos WHERE rowid = ?", (fato_id,))
                    self._db.execute(
                        "INSERT INTO vec_fatos(rowid, embedding) VALUES (?, ?)",
                        (fato_id, _empacotar(vetor)),
                    )
                return fato_id, False
            cursor = self._db.execute(
                "INSERT INTO fatos(texto, vetor, criado, atualizado, origem) VALUES (?,?,?,?,?)",
                (texto, _empacotar(vetor), agora, agora, origem),
            )
            fato_id = cursor.lastrowid
            if self.vetorial:
                self._db.execute(
                    "INSERT INTO vec_fatos(rowid, embedding) VALUES (?, ?)",
                    (fato_id, _empacotar(vetor)),
                )
            return fato_id, True

    def buscar(self, texto: str, k: int = 5, minimo: float = 0.0) -> list[Fato]:
        """Os fatos mais parecidos com o texto, do mais para o menos parecido."""
        if not self.contar():
            return []
        vetor = self.embeddings.vetor(texto)
        with self._trava:
            achados = [(i, s) for i, s in self._parecidos(vetor, k) if s >= minimo]
            fatos = []
            for fato_id, similaridade in achados:
                linha = self._db.execute(
                    "SELECT id, texto, criado, atualizado FROM fatos WHERE id = ?", (fato_id,)
                ).fetchone()
                if linha:
                    fatos.append(Fato(*linha, similaridade=similaridade))
            return fatos

    def listar(self, limite: int | None = None, pular: int = 0, contendo: str = "") -> list[Fato]:
        """Fatos do mais recente para o mais antigo; `contendo` filtra por um trecho do texto."""
        consulta = "SELECT id, texto, criado, atualizado FROM fatos"
        parametros: list = []
        if contendo:
            consulta += " WHERE texto LIKE ?"
            parametros.append(f"%{contendo}%")
        consulta += " ORDER BY atualizado DESC, id DESC LIMIT ? OFFSET ?"
        parametros += [-1 if limite is None else limite, pular]
        with self._trava:
            linhas = self._db.execute(consulta, parametros).fetchall()
        return [Fato(*linha) for linha in linhas]

    def contar_contendo(self, contendo: str) -> int:
        with self._trava:
            return self._db.execute(
                "SELECT COUNT(*) FROM fatos WHERE texto LIKE ?", (f"%{contendo}%",)
            ).fetchone()[0]

    def esquecer(self, fato_id: int) -> bool:
        with self._trava, self._db:
            apagados = self._db.execute("DELETE FROM fatos WHERE id = ?", (fato_id,)).rowcount
            if self.vetorial and self.meta("dimensao"):
                self._db.execute("DELETE FROM vec_fatos WHERE rowid = ?", (fato_id,))
            return apagados > 0

    def contar(self) -> int:
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM fatos").fetchone()[0]

    def fechar(self) -> None:
        with self._trava:
            self._db.close()


def abrir_memoria(config) -> Memoria | None:
    """A memória da config, ou None se estiver desligada."""
    if not config.memoria.ativa:
        return None
    from nora.embeddings import EmbeddingsOllama

    return Memoria(config.pasta_dados / "memoria.db", EmbeddingsOllama(config))
