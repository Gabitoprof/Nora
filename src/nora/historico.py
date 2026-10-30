"""Histórico bruto: toda pergunta e resposta, guardado desde o primeiro dia (em data/)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Historico:
    def __init__(self, pasta_dados: Path, sessao: str | None = None) -> None:
        self.pasta = pasta_dados / "historico"
        self.sessao = sessao or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    @property
    def arquivo(self) -> Path:
        return self.pasta / f"{self.sessao[:10]}.jsonl"

    def registrar(self, papel: str, texto: str, **extra: object) -> None:
        self.pasta.mkdir(parents=True, exist_ok=True)
        registro = {
            "quando": datetime.now().isoformat(timespec="seconds"),
            "sessao": self.sessao,
            "papel": papel,
            "texto": texto,
            **extra,
        }
        with self.arquivo.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
