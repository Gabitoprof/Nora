"""Speech detection: Silero VAD gives the probability that each small piece of audio is voice,
and DetectorDeFala joins those pieces into whole utterances (start and end)."""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from collections import deque
from collections.abc import Iterable, Iterator
from pathlib import Path

QUADRO = 512  # samples per frame at 16 kHz (32 ms), the size Silero expects
BYTES_POR_QUADRO = QUADRO * 2
MS_POR_QUADRO = QUADRO * 1000 // 16_000

# The model comes inside the silero-vad package (MIT license) on PyPI. We take only the .onnx:
# the package itself would pull in PyTorch, which is not needed.
SILERO_VERSAO = "6.2.3"
SILERO_ARQUIVO = "silero_vad/data/silero_vad.onnx"


def baixar_modelo(destino: Path, versao: str = SILERO_VERSAO) -> Path:
    """Downloads silero_vad.onnx from the PyPI package, if it does not exist yet."""
    if destino.is_file():
        return destino
    with urllib.request.urlopen(f"https://pypi.org/pypi/silero-vad/{versao}/json", timeout=30) as r:
        arquivos = json.load(r)["urls"]
    roda = next(a for a in arquivos if a["filename"].endswith(".whl"))
    with urllib.request.urlopen(roda["url"], timeout=120) as r:
        pacote = zipfile.ZipFile(io.BytesIO(r.read()))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(pacote.read(SILERO_ARQUIVO))
    return destino


class SileroVAD:
    """Probability of voice in each 512-sample frame (16 kHz, 16-bit PCM)."""

    CONTEXTO = 64

    def __init__(self, modelo: Path) -> None:
        try:
            import numpy
            import onnxruntime
        except ImportError as erro:
            raise RuntimeError(
                'Falta a parte de voz. Instale com: pip install -e ".[voz]"'
            ) from erro
        opcoes = onnxruntime.SessionOptions()
        opcoes.intra_op_num_threads = 1
        opcoes.inter_op_num_threads = 1
        self._np = numpy
        self._sessao = onnxruntime.InferenceSession(
            str(modelo), sess_options=opcoes, providers=["CPUExecutionProvider"]
        )
        self.reiniciar()

    def reiniciar(self) -> None:
        np = self._np
        self._estado = np.zeros((2, 1, 128), dtype=np.float32)
        self._contexto = np.zeros((1, self.CONTEXTO), dtype=np.float32)

    def probabilidade(self, quadro: bytes) -> float:
        np = self._np
        amostras = np.frombuffer(quadro, dtype="<i2").astype(np.float32)[None, :] / 32768.0
        entrada = np.concatenate([self._contexto, amostras], axis=1)
        saida, self._estado = self._sessao.run(
            None, {"input": entrada, "state": self._estado, "sr": np.array(16_000, dtype=np.int64)}
        )
        self._contexto = entrada[:, -self.CONTEXTO :]
        return float(saida[0][0])


class DetectorDeFala:
    """Takes frames with their voice probability and returns each complete utterance (16 kHz PCM).

    Starts when the probability goes above `limiar`; ends after `silencio_ms` below
    `limiar_fim`. Keeps a bit of the audio before the start, so the first syllable is not cut.
    """

    def __init__(
        self,
        limiar: float = 0.5,
        silencio_ms: int = 700,
        antes_ms: int = 500,
        minimo_ms: int = 250,
        maximo_s: float = 20.0,
    ) -> None:
        self.limiar = limiar
        self.limiar_fim = max(0.0, limiar - 0.15)
        self._silencio = max(1, silencio_ms // MS_POR_QUADRO)
        self._minimo = max(1, minimo_ms // MS_POR_QUADRO)
        self._maximo = max(1, int(maximo_s * 1000) // MS_POR_QUADRO)
        self._antes: deque[bytes] = deque(maxlen=max(1, antes_ms // MS_POR_QUADRO))
        self.reiniciar()

    def reiniciar(self) -> None:
        self._antes.clear()
        self._fala: list[bytes] = []
        self._em_fala = False
        self._quadros_de_voz = 0
        self._quadros_em_silencio = 0

    @property
    def em_fala(self) -> bool:
        return self._em_fala

    def alimentar(self, quadro: bytes, chance: float) -> bytes | None:
        if not self._em_fala:
            if chance >= self.limiar:
                self._em_fala = True
                self._fala = [*self._antes, quadro]
                self._quadros_de_voz = 1
                self._quadros_em_silencio = 0
            else:
                self._antes.append(quadro)
            return None

        self._fala.append(quadro)
        if chance < self.limiar_fim:
            self._quadros_em_silencio += 1
        else:
            self._quadros_em_silencio = 0
            self._quadros_de_voz += 1

        acabou = self._quadros_em_silencio >= self._silencio or len(self._fala) >= self._maximo
        if not acabou:
            return None
        fala, voz = b"".join(self._fala), self._quadros_de_voz
        self.reiniciar()
        return fala if voz >= self._minimo else None


# 32 ms frames without speech between two breaks for the keyboard (~0.3 s).
QUADROS_POR_FOLGA = 10


def em_quadros(blocos: Iterable[bytes]) -> Iterator[bytes | None]:
    """Regroups PCM blocks of any size into 512-sample frames. An empty block (the microphone
    with no new audio) becomes None, so the consumer can do other things."""
    sobra = b""
    for bloco in blocos:
        if not bloco:
            yield None
            continue
        sobra += bloco
        while len(sobra) >= BYTES_POR_QUADRO:
            yield sobra[:BYTES_POR_QUADRO]
            sobra = sobra[BYTES_POR_QUADRO:]


def falas(quadros: Iterable[bytes | None], vad, detector: DetectorDeFala) -> Iterator[bytes | None]:
    """Runs each frame through the VAD and the detector; returns the complete utterances, and None
    when the microphone has no new audio or every ~0.3 s of audio without a complete utterance:
    with the microphone capturing nonstop, the consumer also needs a break to check the keyboard."""
    sem_fala = 0
    for quadro in quadros:
        if quadro is None:
            yield None
            continue
        fala = detector.alimentar(quadro, vad.probabilidade(quadro))
        if fala:
            sem_fala = 0
            yield fala
            continue
        sem_fala += 1
        if sem_fala >= QUADROS_POR_FOLGA:
            sem_fala = 0
            yield None
