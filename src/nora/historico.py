"""Raw history: every question and answer, kept from day one (in data/)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class Historico:
    def __init__(self, pasta_dados: Path, sessao: str | None = None) -> None:
        self.pasta = pasta_dados / "historico"
        self.sessao = sessao or datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")

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


APAGADO = "[apagado a pedido]"


def apagar_do_historico(pasta_dados: Path, textos: set[str]) -> int:
    """Replaces, in the history files, the utterances whose text is in `textos` with APAGADO (the
    rest of the conversation stays). Returns how many utterances were deleted."""
    if not textos:
        return 0
    apagadas = 0
    for arquivo in sorted((pasta_dados / "historico").glob("*.jsonl")):
        linhas, mudou = [], False
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            try:
                registro = json.loads(linha)
            except json.JSONDecodeError:
                linhas.append(linha)
                continue
            if registro.get("texto") in textos:
                registro["texto"], registro["apagado"] = APAGADO, True
                apagadas += 1
                mudou = True
            linhas.append(json.dumps(registro, ensure_ascii=False))
        if mudou:  # writes to a side file and swaps it in, so nothing is lost on a power cut
            temporario = arquivo.with_suffix(".jsonl.tmp")
            temporario.write_text("\n".join(linhas) + "\n", encoding="utf-8")
            temporario.replace(arquivo)
    return apagadas
