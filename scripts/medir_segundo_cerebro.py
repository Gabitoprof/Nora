"""Mede se o Second Brain atrasa a fala da Nora (requisito do documento 2 da v0.3.1).

Roda o caminho da voz de verdade (Conversa → responder_falando → Locutor → tocar) com um cérebro
e uma voz falsos de tempo fixo, para tirar a variação da rede e da GPU, em três cenários:

  desligado   Second Brain desligado (referência)
  ligado      Second Brain ligado, com memória grande, avisado a cada resposta (uso real: ele
              espera a Nora ficar livre)
  estresse    sincronização rodando sem parar, ignorando se a Nora está falando (pior caso
              artificial: mede a disputa de CPU/GIL)

Métricas por resposta: início do áudio (fim da fala → primeiro áudio tocando) e a maior pausa
entre trechos de áudio. Mostra p50, p95 e p99. Uso:

    python scripts/medir_segundo_cerebro.py --respostas 60 --fatos 2000

Não substitui a medição no Windows com a voz e o modelo de verdade (checklist em
docs/SEGUNDO_CEREBRO.md).
"""

from __future__ import annotations

import argparse
import hashlib
import math
import platform
import shutil
import statistics
import sys
import tempfile
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from nora.config import carregar  # noqa: E402
from nora.conversa import nova_conversa  # noqa: E402
from nora.conversa_voz import responder_falando  # noqa: E402
from nora.memoria import Memoria  # noqa: E402
from nora.segundo_cerebro import Sincronizador, Trabalhador, destino  # noqa: E402

RESPOSTA = [
    "Claro! ",
    "Daqui a vinte e três dias será sábado, ",
    "vinte e oito de novembro. ",
    "Quer que eu anote isso na agenda? ",
    "Posso te lembrar um dia antes também.",
]


class Embeddings:
    def vetor(self, texto: str) -> list[float]:
        vetor = [0.0] * 64
        for palavra in texto.lower().split():
            vetor[int(hashlib.md5(palavra.encode()).hexdigest(), 16) % 64] += 1.0
        norma = math.sqrt(sum(x * x for x in vetor)) or 1.0
        return [x / norma for x in vetor]


class CerebroFalso:
    """Primeiro pedaço em 150 ms, depois um pedaço a cada 40 ms."""

    situacao = "completa"

    class medidas:
        primeiro_pedaco = 0.15
        total = 0.31

    def responder(self, mensagens):
        time.sleep(0.15)
        for i, pedaco in enumerate(RESPOSTA):
            if i:
                time.sleep(0.04)
            yield pedaco


class VozFalsa:
    """Sintetiza em 120 ms + 2 ms por caractere; o áudio dura 60 ms por palavra."""

    def sintetizar(self, frase: str) -> bytes:
        time.sleep(0.12 + 0.002 * len(frase))
        return frase.encode()


def tocador(marcas: list):
    def tocar(wav: bytes) -> None:
        inicio = time.perf_counter()
        time.sleep(0.06 * len(wav.split()))
        marcas.append((inicio, time.perf_counter()))

    return tocar


def percentis(valores: list[float]) -> dict[str, float]:
    ordenados = sorted(valores)

    def p(q: float) -> float:
        indice = min(len(ordenados) - 1, max(0, math.ceil(q * len(ordenados)) - 1))
        return ordenados[indice] * 1000

    return {
        "p50": p(0.50),
        "p95": p(0.95),
        "p99": p(0.99),
        "desvio": statistics.pstdev(ordenados) * 1000,
    }


def criar_memoria(arquivo: Path, fatos: int) -> None:
    """A memória grande, criada uma vez e copiada para cada cenário."""
    memoria = Memoria(arquivo, Embeddings())
    areas = ["estudos", "trabalho", "rotina", "projetos", "pessoal"]
    for i in range(fatos):
        memoria.lembrar(
            f"Lia anotou o assunto {i} do Projeto Exemplo{i % 40} com a equipe Time{i % 7}",
            "manual",
            areas[i % len(areas)],
            ["", "curiosa", "alegre", "calma"][i % 4],
        )
    memoria.fechar()


def preparar(pasta: Path, modelo: Path, ativo: bool):
    (pasta / "config").mkdir(parents=True, exist_ok=True)
    (pasta / "vault").mkdir(exist_ok=True)
    (pasta / "config/nora.toml").write_text(
        (RAIZ / "src/nora/nora.toml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (pasta / "config/local.toml").write_text(
        '[usuario]\nnome = "Lia"\n[notas]\npasta = "vault"\natualizar_ao_abrir = false\n'
        "[memoria]\nativa = false\n[auto_melhoria]\nativa = false\n"
        f"[segundo_cerebro]\nativo = {'true' if ativo else 'false'}\n",
        encoding="utf-8",
    )
    config = carregar(pasta, ambiente={})
    config.pasta_dados.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(modelo, config.pasta_dados / "memoria.db")
    return config


def medir(cenario: str, respostas: int, modelo: Path) -> dict:
    with tempfile.TemporaryDirectory() as temporaria:
        config = preparar(Path(temporaria), modelo, ativo=cenario != "desligado")
        conversa = nova_conversa(config, CerebroFalso(), memoria=None, notas=None, observador=None)
        trabalhador = None
        parar = threading.Event()
        rodadas = [0]
        if cenario == "ligado":
            trabalhador = Trabalhador(
                Sincronizador(config, *destino(config)),
                ocupado=lambda: bool(conversa.ocupada or conversa.falando),
                intervalo=60,
            )
            trabalhador.start()
        elif cenario == "estresse":
            sincronizador = Sincronizador(config, *destino(config))

            def sem_parar():
                while not parar.is_set():
                    # Força reescrever tudo: apaga o registro do que já foi exportado.
                    with sincronizador._estado:
                        sincronizador._estado.execute("DELETE FROM notas")
                    for nota in (config.notas.pasta / "Nora Brain").rglob("*.md"):
                        nota.unlink()
                    sincronizador.sincronizar()
                    rodadas[0] += 1

            estresse = threading.Thread(target=sem_parar, daemon=True)
            estresse.start()
        time.sleep(0.5)
        inicios, pausas = [], []
        for _ in range(respostas):
            marcas: list = []
            fim_da_fala = time.perf_counter()
            tempos = responder_falando(
                conversa, VozFalsa(), tocador(marcas), "que dia vai ser daqui a 23 dias?",
                fim_da_fala, 0.0, lambda *a, **k: None, False,
            )  # fmt: skip
            inicios.append(tempos.comeco_da_voz)
            pausas.append(
                max((b[0] - a[1] for a, b in zip(marcas, marcas[1:], strict=False)), default=0.0)
            )
            if trabalhador is not None:
                trabalhador.avisar()  # a memória "mudou" a cada resposta
            time.sleep(0.05)
        parar.set()
        if cenario == "estresse":
            estresse.join(30)
        if trabalhador is not None:
            rodadas[0] = trabalhador.rodadas
            trabalhador._parar.set()
            trabalhador._sinal.set()
            trabalhador.join(5)
        return {
            "inicio": percentis(inicios),
            "pausa": percentis(pausas),
            "rodadas": rodadas[0],
            "n": respostas,
        }


def main() -> int:
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("--respostas", type=int, default=60)
    argumentos.add_argument("--fatos", type=int, default=2000)
    args = argumentos.parse_args()
    print(
        f"Ambiente: Python {platform.python_version()}, {platform.system()} "
        f"{platform.machine()}, {args.respostas} respostas por cenário, {args.fatos} fatos"
    )
    base = None
    with tempfile.TemporaryDirectory() as temporaria:
        modelo = Path(temporaria) / "memoria.db"
        criar_memoria(modelo, args.fatos)
        for cenario in ("desligado", "ligado", "estresse"):
            base = mostrar(cenario, medir(cenario, args.respostas, modelo), base)
    return 0


def mostrar(cenario: str, resultado: dict, base: float | None) -> float:
    inicio, pausa = resultado["inicio"], resultado["pausa"]
    base = base or inicio["p95"]
    print(
        f"{cenario:<10} início do áudio p50 {inicio['p50']:6.1f} ms  p95 {inicio['p95']:6.1f}"
        f"  p99 {inicio['p99']:6.1f}  (desvio {inicio['desvio']:4.1f})  "
        f"Δp95 {100 * (inicio['p95'] - base) / base:+5.1f}%  | maior pausa p95 "
        f"{pausa['p95']:5.1f} ms  | sincronizações: {resultado['rodadas']}",
        flush=True,
    )
    return base


if __name__ == "__main__":
    raise SystemExit(main())
