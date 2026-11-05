"""Observador da auto-melhoria: anota, sem atrapalhar a conversa, como foi cada etapa (tempos,
falhas, quem respondeu, reclamações). Só métricas e categorias: nunca o texto do que foi dito
nem áudio. Fica em <dados>/auto_melhoria/auto_melhoria.db; o fechamento do dia (melhorias.py)
lê daqui.

Tipos de evento: resposta, escalou, erro_provedor, timeout, resposta_vazia, stream_interrompido,
sem_resposta, cancelada, feedback_negativo, rota_suspeita, comando, transcricao, voz.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from nora import __version__

ESQUEMA = """
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY,
    quando TEXT NOT NULL,
    interacao TEXT NOT NULL DEFAULT '',
    etapa TEXT NOT NULL,
    motor TEXT NOT NULL DEFAULT '',
    tipo TEXT NOT NULL,
    duracao_ms INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT '',
    tentativa INTEGER NOT NULL DEFAULT 0,
    modo_jogo INTEGER NOT NULL DEFAULT 0,
    gravidade TEXT NOT NULL DEFAULT 'info',
    correlacao TEXT NOT NULL DEFAULT '',
    versao TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS eventos_quando ON eventos(quando);
"""
CAMPOS = (
    "quando, interacao, etapa, motor, tipo, duracao_ms, status, tentativa, modo_jogo, "
    "gravidade, correlacao, versao"
)
GRAVES = {"erro_provedor", "timeout", "stream_interrompido", "sem_resposta"}


def caminho_do_banco(pasta_dados: Path) -> Path:
    return pasta_dados / "auto_melhoria" / "auto_melhoria.db"


class Observador:
    def __init__(self, caminho: Path) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.caminho = caminho
        self._trava = threading.Lock()
        self._db = sqlite3.connect(caminho, check_same_thread=False)
        with self._db:
            self._db.executescript(ESQUEMA)

    def registrar(
        self,
        etapa: str,
        tipo: str,
        motor: str = "",
        interacao: str = "",
        duracao_ms: int = 0,
        status: str = "",
        tentativa: int = 0,
        modo_jogo: bool = False,
        gravidade: str = "",
        correlacao: str = "",
        quando: datetime | None = None,
    ) -> None:
        """Anota um evento. Nunca levanta erro: o observador não pode derrubar a conversa."""
        gravidade = gravidade or ("erro" if tipo in GRAVES else "info")
        momento = (quando or datetime.now()).isoformat(timespec="seconds")
        try:
            with self._trava, self._db:
                self._db.execute(
                    f"INSERT INTO eventos({CAMPOS}) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        momento,
                        interacao,
                        etapa,
                        motor,
                        tipo,
                        int(duracao_ms),
                        status,
                        tentativa,
                        int(modo_jogo),
                        gravidade,
                        correlacao,
                        __version__,
                    ),
                )
        except Exception:
            pass

    def eventos(self, depois: str = "", ate: str = "9999") -> list[dict]:
        """Os eventos com `depois < quando <= ate` (datas ISO)."""
        with self._trava:
            cursor = self._db.execute(
                f"SELECT {CAMPOS} FROM eventos WHERE quando > ? AND quando <= ? ORDER BY quando",
                (depois, ate),
            )
            nomes = [c[0] for c in cursor.description]
            return [dict(zip(nomes, linha, strict=True)) for linha in cursor.fetchall()]

    def limpar_antigos(self, dias: int, agora: datetime | None = None) -> int:
        limite = ((agora or datetime.now()) - timedelta(days=dias)).isoformat(timespec="seconds")
        with self._trava, self._db:
            return self._db.execute("DELETE FROM eventos WHERE quando < ?", (limite,)).rowcount

    def fechar(self) -> None:
        with self._trava:
            self._db.close()


def abrir_observador(config) -> Observador | None:
    """O observador da config, ou None se a auto-melhoria estiver desligada."""
    if not config.auto_melhoria.ativa:
        return None
    try:
        return Observador(caminho_do_banco(config.pasta_dados))
    except Exception:
        return None
