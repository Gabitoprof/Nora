"""Obsidian notes index (v0.3.0): Nora reads the notes in your vault and uses the passages similar
to the question to answer ("o que eu anotei sobre a prova de cálculo?").

The notes are only read, never changed. Each note becomes passages (by heading and paragraphs),
each passage gets a meaning vector (the same embeddings model as memory) and everything lives in
<dados>/notas.db, which can be deleted and rebuilt whenever you want. Only the notes that are new
or changed since last time are read again.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from nora.memoria import _cosseno, _desempacotar, _empacotar

TAMANHO_DO_TRECHO = 900  # characters, roughly one large paragraph
LOTE = 32  # passages per embeddings request
_PASTAS_IGNORADAS = {"node_modules", "__pycache__"}


@dataclass(frozen=True)
class Trecho:
    caminho: str  # relative to the vault
    titulo: str  # "Note > Section"
    texto: str
    similaridade: float = 0.0


@dataclass(frozen=True)
class Resumo:
    lidas: int  # new or changed notes
    removidas: int
    trechos: int  # total in the index
    notas: int  # total in the index


def limpar_markdown(texto: str) -> str:
    """Removes what only Obsidian understands: properties (frontmatter), comments, embedded
    images, and leaves the [[links]] as text."""
    texto = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", texto, flags=re.DOTALL)
    texto = re.sub(r"%%.*?%%", "", texto, flags=re.DOTALL)
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.DOTALL)
    texto = re.sub(r"!\[\[[^\]]*\]\]", "", texto)
    texto = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", texto)
    texto = re.sub(r"\[\[([^\]|#]*)(?:#[^\]|]*)?\|([^\]]*)\]\]", r"\2", texto)
    texto = re.sub(r"\[\[([^\]|#]*)(?:#([^\]|]*))?\]\]", lambda m: m.group(1) or m.group(2), texto)
    return texto


def dividir(nome: str, texto: str, tamanho: int = TAMANHO_DO_TRECHO) -> list[tuple[str, str]]:
    """Splits the note into passages (heading, text): one section per heading and, if it is large,
    into pieces of whole paragraphs."""
    trechos: list[tuple[str, str]] = []
    caminho_titulos: list[tuple[int, str]] = []
    secao: list[str] = []

    def fechar() -> None:
        corpo = "\n".join(secao).strip()
        secao.clear()
        if not corpo:
            return
        titulo = " > ".join([nome, *(t for _, t in caminho_titulos)])
        pedaco = ""
        for paragrafo in re.split(r"\n\s*\n", corpo):
            paragrafo = paragrafo.strip()
            if pedaco and len(pedaco) + len(paragrafo) > tamanho:
                trechos.append((titulo, pedaco))
                pedaco = ""
            while len(paragrafo) > tamanho:  # huge paragraph: cut at the nearest space
                corte = paragrafo.rfind(" ", 0, tamanho) or tamanho
                trechos.append((titulo, paragrafo[:corte].strip()))
                paragrafo = paragrafo[corte:].strip()
            pedaco = f"{pedaco}\n\n{paragrafo}".strip()
        if pedaco:
            trechos.append((titulo, pedaco))

    dentro_de_codigo = False
    for linha in limpar_markdown(texto).splitlines():
        if linha.lstrip().startswith("```"):
            dentro_de_codigo = not dentro_de_codigo
        titulo = None if dentro_de_codigo else re.match(r"(#{1,6})\s+(.+?)\s*#*\s*$", linha)
        if titulo:
            fechar()
            nivel = len(titulo.group(1))
            caminho_titulos = [(n, t) for n, t in caminho_titulos if n < nivel]
            caminho_titulos.append((nivel, titulo.group(2)))
        else:
            secao.append(linha)
    fechar()
    return trechos


class IndiceDeNotas:
    def __init__(self, caminho: Path, vault: Path, embeddings, ignorar=()) -> None:
        self.caminho = caminho
        self.vault = vault
        self.embeddings = embeddings
        self.ignorar = {p.strip("/\\").lower() for p in ignorar if p.strip("/\\")}
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self._trava = threading.RLock()
        self._db = sqlite3.connect(caminho, check_same_thread=False)
        with self._db:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT);
                CREATE TABLE IF NOT EXISTS notas (
                    caminho TEXT PRIMARY KEY, modificada REAL NOT NULL, tamanho INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trechos (
                    id INTEGER PRIMARY KEY, caminho TEXT NOT NULL, titulo TEXT NOT NULL,
                    texto TEXT NOT NULL, vetor BLOB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS trechos_caminho ON trechos(caminho);
                """
            )
        self.vetorial = self._carregar_sqlite_vec()

    # --- sqlite-vec (optional, as in memory) ----------------------------------------------------

    def _carregar_sqlite_vec(self) -> bool:
        try:
            import sqlite_vec

            self._db.enable_load_extension(True)
            sqlite_vec.load(self._db)
            self._db.enable_load_extension(False)
            return True
        except (ImportError, AttributeError, sqlite3.Error):
            return False

    def _meta(self, chave: str) -> str | None:
        linha = self._db.execute("SELECT valor FROM meta WHERE chave = ?", (chave,)).fetchone()
        return linha[0] if linha else None

    def _garantir_indice(self, dimensao: int) -> None:
        if not self.vetorial:
            return
        existe = self._db.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'vec_trechos'"
        ).fetchone()
        if existe and self._meta("dimensao") == str(dimensao):
            return
        self._db.execute("DROP TABLE IF EXISTS vec_trechos")
        self._db.execute(
            "CREATE VIRTUAL TABLE vec_trechos USING vec0("
            f"embedding float[{dimensao}] distance_metric=cosine)"
        )
        for trecho_id, vetor in self._db.execute("SELECT id, vetor FROM trechos").fetchall():
            if len(vetor) // 4 == dimensao:
                self._db.execute(
                    "INSERT INTO vec_trechos(rowid, embedding) VALUES (?, ?)", (trecho_id, vetor)
                )
        self._db.execute(
            "INSERT INTO meta(chave, valor) VALUES ('dimensao', ?) "
            "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
            (str(dimensao),),
        )

    # --- reading the vault --------------------------------------------------------------------

    def _arquivos(self) -> dict[str, Path]:
        """The vault's notes (.md), without hidden (.obsidian, .trash, .git) and ignored folders."""
        achadas = {}
        for arquivo in self.vault.rglob("*.md"):
            partes = arquivo.relative_to(self.vault).parts
            if any(p.startswith(".") or p in _PASTAS_IGNORADAS for p in partes[:-1]):
                continue
            relativo = "/".join(partes)
            if any(
                relativo.lower() == p or relativo.lower().startswith(p + "/") for p in self.ignorar
            ):
                continue
            achadas[relativo] = arquivo
        return achadas

    def _tem_indice_vetorial(self) -> bool:
        return self.vetorial and bool(
            self._db.execute("SELECT 1 FROM sqlite_master WHERE name = 'vec_trechos'").fetchone()
        )

    def _apagar(self, caminho: str) -> None:
        if self._tem_indice_vetorial():
            self._db.execute(
                "DELETE FROM vec_trechos WHERE rowid IN (SELECT id FROM trechos WHERE caminho = ?)",
                (caminho,),
            )
        self._db.execute("DELETE FROM trechos WHERE caminho = ?", (caminho,))
        self._db.execute("DELETE FROM notas WHERE caminho = ?", (caminho,))

    def atualizar(self, aviso=None) -> Resumo:
        """Reads the new or changed notes and forgets the deleted ones. `aviso(lidas, total)` gets
        the progress (to show on screen)."""
        if not self.vault.is_dir():
            raise FileNotFoundError(f"A pasta das notas não existe: {self.vault}")
        arquivos = self._arquivos()
        with self._trava:
            conhecidas = {
                caminho: (modificada, tamanho)
                for caminho, modificada, tamanho in self._db.execute("SELECT * FROM notas")
            }
        removidas = [c for c in conhecidas if c not in arquivos]
        mudadas = []
        for relativo, arquivo in arquivos.items():
            estado = arquivo.stat()
            if conhecidas.get(relativo) != (estado.st_mtime, estado.st_size):
                mudadas.append((relativo, arquivo, estado))
        with self._trava, self._db:
            for caminho in removidas:
                self._apagar(caminho)
        for numero, (relativo, arquivo, estado) in enumerate(mudadas, 1):
            texto = arquivo.read_text(encoding="utf-8-sig", errors="replace")
            trechos = dividir(arquivo.stem, texto)
            vetores = []
            for inicio in range(0, len(trechos), LOTE):
                lote = trechos[inicio : inicio + LOTE]
                vetores += self.embeddings.vetores([f"{t}\n{c}" for t, c in lote])
            with self._trava, self._db:
                self._apagar(relativo)
                if vetores:
                    self._garantir_indice(len(vetores[0]))
                for (titulo, corpo), vetor in zip(trechos, vetores, strict=True):
                    cursor = self._db.execute(
                        "INSERT INTO trechos(caminho, titulo, texto, vetor) VALUES (?,?,?,?)",
                        (relativo, titulo, corpo, _empacotar(vetor)),
                    )
                    if self.vetorial:
                        self._db.execute(
                            "INSERT INTO vec_trechos(rowid, embedding) VALUES (?, ?)",
                            (cursor.lastrowid, _empacotar(vetor)),
                        )
                self._db.execute(
                    "INSERT INTO notas(caminho, modificada, tamanho) VALUES (?, ?, ?)",
                    (relativo, estado.st_mtime, estado.st_size),
                )
            if aviso:
                aviso(numero, len(mudadas))
        return Resumo(len(mudadas), len(removidas), self.contar_trechos(), self.contar_notas())

    # --- search ---------------------------------------------------------------------------------

    def buscar(self, texto: str, k: int = 3, minimo: float = 0.0) -> list[Trecho]:
        if k <= 0 or not self.contar_trechos():
            return []
        vetor = self.embeddings.vetor(texto)
        with self._trava:
            if self._tem_indice_vetorial() and self._meta("dimensao") == str(len(vetor)):
                achados = [
                    (trecho_id, 0.0 if distancia is None else 1.0 - distancia)
                    for trecho_id, distancia in self._db.execute(
                        "SELECT rowid, distance FROM vec_trechos WHERE embedding MATCH ? "
                        "AND k = ? ORDER BY distance",
                        (_empacotar(vetor), k),
                    ).fetchall()
                ]
            else:
                todos = [
                    (trecho_id, _cosseno(vetor, _desempacotar(dados)))
                    for trecho_id, dados in self._db.execute("SELECT id, vetor FROM trechos")
                    if len(dados) // 4 == len(vetor)
                ]
                achados = sorted(todos, key=lambda par: par[1], reverse=True)[:k]
            trechos = []
            for trecho_id, similaridade in achados:
                if similaridade < minimo:
                    continue
                linha = self._db.execute(
                    "SELECT caminho, titulo, texto FROM trechos WHERE id = ?", (trecho_id,)
                ).fetchone()
                if linha:
                    trechos.append(Trecho(*linha, similaridade=similaridade))
            return trechos

    def contar_trechos(self) -> int:
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM trechos").fetchone()[0]

    def contar_notas(self) -> int:
        with self._trava:
            return self._db.execute("SELECT COUNT(*) FROM notas").fetchone()[0]

    def fechar(self) -> None:
        with self._trava:
            self._db.close()


def abrir_notas(config) -> IndiceDeNotas | None:
    """The config's notes index, or None if no notes folder is configured."""
    notas = config.notas
    if notas.pasta is None:
        return None
    from nora.embeddings import EmbeddingsOllama

    return IndiceDeNotas(
        config.pasta_dados / "notas.db",
        notas.pasta,
        EmbeddingsOllama(config),
        (*notas.ignorar, *pastas_da_nora(config)),
    )


def pastas_da_nora(config) -> tuple[str, ...]:
    """The Second Brain folder inside the vault: these are notes Nora generated from her own memory
    and they must not come back to her as if they were yours (export → reread → duplicate).
    Applies even with the Second Brain off, if the folder already exists from before."""
    pasta = Path(config.segundo_cerebro.pasta).expanduser()
    if not pasta.is_absolute():
        return (pasta.as_posix(),)
    try:
        return (pasta.resolve().relative_to(Path(config.notas.pasta).resolve()).as_posix(),)
    except ValueError:
        return ()
