"""Measurements derived from PCM, without recording or sending audio to the browser."""

from __future__ import annotations

import cmath
import math
import re
import sys
from array import array
from functools import lru_cache

from nora.emocao import emocoes_em, sem_emocoes

BANDAS_HZ = (0, 200, 500, 1200, 2500, 5000)
JANELA = 512
MAX_QUADROS = 2048
MAX_DURACAO_MS = 600_000
_numpy = None


def mono(pcm: bytes, canais: int = 1) -> list[float]:
    valores = array("h")
    valores.frombytes(pcm[: min(len(pcm) // (2 * canais), MAX_QUADROS) * 2 * canais])
    if sys.byteorder != "little":
        valores.byteswap()
    return [sum(valores[i : i + canais]) / (32768 * canais) for i in range(0, len(valores), canais)]


@lru_cache(maxsize=1)
def _janela():
    return tuple(0.5 - 0.5 * math.cos(2 * math.pi * i / (JANELA - 1)) for i in range(JANELA))


@lru_cache(maxsize=9)
def _raizes(n):
    return tuple(cmath.exp(-2j * math.pi * i / n) for i in range(n // 2))


def _fft(x):
    if len(x) == 1:
        return x
    a, b = _fft(x[::2]), _fft(x[1::2])
    termos = [w * v for w, v in zip(_raizes(len(x)), b, strict=True)]
    return [p + q for p, q in zip(a, termos, strict=True)] + [
        p - q for p, q in zip(a, termos, strict=True)
    ]


class Medidor:
    """512-point FFT, relative bands and a 35 ms attack / 180 ms release envelope."""

    def __init__(self):
        self.envelope = 0.0
        self.bandas = [0.0] * 6

    def medir(self, pcm: bytes, taxa: int, canais: int = 1, dt: float = 0.05) -> dict:
        if not 8000 <= taxa <= 192000 or canais not in (1, 2):
            raise ValueError("Formato PCM inválido para a HUD")
        pontos = mono(pcm, canais)
        rms = math.sqrt(sum(x * x for x in pontos) / max(1, len(pontos)))
        pico = max(map(abs, pontos), default=0.0)
        tau = 0.035 if rms > self.envelope else 0.18
        self.envelope += (rms - self.envelope) * (1 - math.exp(-max(0, dt) / tau))
        # Contiguous points at the real rate; decimating by skipping would invent frequencies.
        janela = pontos[-JANELA:] + [0.0] * max(0, JANELA - len(pontos))
        media = sum(janela) / JANELA
        ponderada = [(v - media) * w for v, w in zip(janela, _janela(), strict=True)]
        global _numpy
        if _numpy is None:
            try:
                import numpy

                _numpy = numpy
            except (ImportError, OSError):
                _numpy = False
        espectro = (
            _numpy.fft.rfft(ponderada)
            if _numpy is not False
            else _fft([complex(v) for v in ponderada])
        )
        energias = [float(abs(v) ** 2) for v in espectro[: JANELA // 2 + 1]]
        soma = sum(energias)
        bandas, centroide = [0.0] * 6, 0.0
        if rms >= 0.0003 and soma > 1e-12:
            for i, energia in enumerate(energias):
                hz = i * taxa / JANELA
                faixa = next((j - 1 for j, limite in enumerate(BANDAS_HZ) if hz < limite), 5)
                bandas[max(0, faixa)] += energia / soma
                centroide += energia * (i / (JANELA // 2)) / soma
        fluxo = sum(max(0, a - b) for a, b in zip(bandas, self.bandas, strict=True))
        self.bandas = bandas
        return {
            "rms": round(min(1.0, rms), 6),
            "pico": round(min(1.0, pico), 6),
            "envelope": round(min(1.0, self.envelope), 6),
            "bandas": [round(min(1.0, b), 6) for b in bandas],
            "centroide": round(min(1.0, centroide), 6),
            "fluxo": round(min(1.0, fluxo), 6),
        }


class EnvelopeTemporal:
    """RMS every 20 ms; stores only measurements and a remainder smaller than one window.

    Feeding happens on the thread that receives the blocks, never in the PortAudio callback.
    Up to ten minutes; past the limit, it turns words off without affecting playback.
    """

    def __init__(self, taxa: int, canais: int):
        self.taxa, self.canais = taxa, canais
        self.quadros_janela = max(1, taxa // 50)
        self.largura = self.quadros_janela * canais * 2
        self.sobra = b""
        self.quadros = 0
        self.rms: list[float] = []
        self.valido = True

    def alimentar(self, pcm: bytes):
        if not self.valido:
            return
        self.quadros += len(pcm) // (2 * self.canais)
        if self.quadros / self.taxa * 1000 > MAX_DURACAO_MS:
            self.valido = False
            self.rms.clear()
            self.sobra = b""
            return
        dados = self.sobra + pcm
        limite = len(dados) // self.largura * self.largura
        for inicio in range(0, limite, self.largura):
            self.rms.append(self._rms(dados[inicio : inicio + self.largura]))
        self.sobra = dados[limite:]

    def _rms(self, pcm):
        valores = array("h")
        valores.frombytes(pcm)
        if sys.byteorder != "little":
            valores.byteswap()
        if self.canais == 1:
            soma, n = sum(v * v for v in valores), len(valores)
        else:
            soma = sum(((valores[i] + valores[i + 1]) / 2) ** 2 for i in range(0, len(valores), 2))
            n = len(valores) // 2
        return math.sqrt(soma / max(1, n)) / 32768

    def finalizar(self, texto: str) -> dict | None:
        if not self.valido:
            return None
        intensidades = self.rms + ([self._rms(self.sobra)] if self.sobra else [])
        return _temporizar(
            texto,
            intensidades,
            self.quadros / self.taxa * 1000,
            self.quadros_janela / self.taxa * 1000,
        )


def _temporizar(texto, intensidades, duracao, passo):
    palavras = sem_emocoes(texto).split()
    if not palavras or len(palavras) > 256 or sum(map(len, palavras)) > 6000:
        return None
    if any(len(p) > 80 for p in palavras) or not 0 < duracao <= MAX_DURACAO_MS:
        return None
    limiar = max(0.002, max(intensidades, default=0.0) * 0.08)
    ativas = [i for i, rms in enumerate(intensidades) if rms >= limiar]
    if not ativas:
        return None
    pesos = [max(1, len(re.sub(r"[^\w]", "", p))) for p in palavras]
    soma, acumulado, resultado = sum(pesos), 0, []
    emocionada = bool(emocoes_em(texto))
    for palavra, peso in zip(palavras, pesos, strict=True):
        primeiro = min(len(ativas) - 1, int(acumulado / soma * len(ativas)))
        acumulado += peso
        ultimo = max(primeiro, min(len(ativas) - 1, math.ceil(acumulado / soma * len(ativas)) - 1))
        inicio = ativas[primeiro] * passo
        fim = min(duracao, (ativas[ultimo] + 1) * passo)
        if resultado:
            inicio = max(inicio, resultado[-1]["fim_ms"])
        if round(fim, 3) <= round(inicio, 3):
            return None
        resultado.append(
            {
                "texto": palavra,
                "inicio_ms": round(inicio, 3),
                "fim_ms": round(fim, 3),
                "destaque": emocionada and peso >= 5,
            }
        )
    return {"duracao_ms": round(duracao, 3), "precisao": "estimada", "palavras": resultado}


def temporizar(texto: str, pcm: bytes, taxa: int, canais: int) -> dict | None:
    envelope = EnvelopeTemporal(taxa, canais)
    envelope.alimentar(pcm)
    return envelope.finalizar(texto)
