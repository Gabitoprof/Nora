"""Importa as conversas antigas de <dados>/historico para a memória (nora memoria importar)."""

from __future__ import annotations

import json
from pathlib import Path

from nora.config import Config
from nora.curadoria import extrair_fatos
from nora.memoria import Memoria


def trocas(arquivo: Path) -> list[tuple[str, str, str, str]]:
    """(quando, sessão, pergunta, resposta) de um arquivo do histórico, na ordem."""
    resultado, pergunta = [], None
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        try:
            registro = json.loads(linha)
        except json.JSONDecodeError:
            continue
        if registro.get("papel") == "usuario":
            pergunta = registro
        elif registro.get("papel") == "assistente" and pergunta is not None:
            resultado.append(
                (
                    pergunta["quando"],
                    pergunta.get("sessao", ""),
                    pergunta["texto"],
                    registro["texto"],
                )
            )
            pergunta = None
    return resultado


def importar_historico(config: Config, memoria: Memoria, saida=print) -> int:
    """Passa cada troca ainda não importada pela curadoria. Pode ser rodado de novo: continua
    de onde parou."""
    ja_ate = memoria.meta("importado_ate") or ""
    arquivos = sorted((config.pasta_dados / "historico").glob("*.jsonl"))
    pendentes = [t for a in arquivos for t in trocas(a) if t[0] > ja_ate]
    saida(f"{len(pendentes)} trocas para ler (pode demorar alguns segundos por troca).")
    novos = 0
    for numero, (quando, sessao, pergunta, resposta) in enumerate(pendentes, start=1):
        dia = f"{quando[8:10]}/{quando[5:7]}/{quando[:4]}"
        memoria.guardar_troca(pergunta, resposta, quando, sessao)
        for fato in extrair_fatos(config, pergunta, resposta, dia):
            _, novo = memoria.lembrar(fato, origem=f"historico {quando[:10]}")
            novos += novo
            saida(f"  {'+' if novo else '~'} {fato}")
        memoria.definir_meta("importado_ate", quando)
        if numero % 10 == 0:
            saida(f"  ({numero}/{len(pendentes)})")
    saida(
        f"Pronto: {novos} fatos novos. Total: {memoria.contar()} fatos e "
        f"{memoria.contar_trocas()} trocas guardadas."
    )
    return 0
