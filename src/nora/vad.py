"""Detecção de fala: o Silero VAD dá a chance de cada pedacinho de áudio ser voz, e o
DetectorDeFala junta esses pedacinhos em falas inteiras (começo e fim)."""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from collections import deque
from collections.abc import Iterable, Iterator
from pathlib import Path

QUADRO = 512  # amostras por quadro a 16 kHz (32 ms), o tamanho que o Silero espera
BYTES_POR_QUADRO = QUADRO * 2
MS_POR_QUADRO = QUADRO * 1000 // 16_000

# O modelo vem dentro do pacote silero-vad (licença MIT) no PyPI. Pegamos só o arquivo .onnx:
# o pacote em si puxaria o PyTorch, que não é necessário.
SILERO_VERSAO = "6.2.3"
SILERO_ARQUIVO = "silero_vad/data/silero_vad.onnx"


def baixar_modelo(destino: Path, versao: str = SILERO_VERSAO) -> Path:
    """Baixa o silero_vad.onnx do pacote do PyPI, se ainda não existir."""
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
    """Probabilidade de haver voz em cada quadro de 512 amostras (16 kHz, PCM 16 bits)."""

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
    """Recebe quadros com a chance de voz e devolve cada fala completa (PCM 16 kHz).

    Começa quando a chance passa de `limiar`; termina depois de `silencio_ms` abaixo de
    `limiar_fim`. Guarda um pouco do áudio de antes do começo, para não cortar a primeira sílaba.
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


def em_quadros(blocos: Iterable[bytes]) -> Iterator[bytes]:
    """Reagrupa blocos de PCM de qualquer tamanho em quadros de 512 amostras."""
    sobra = b""
    for bloco in blocos:
        sobra += bloco
        while len(sobra) >= BYTES_POR_QUADRO:
            yield sobra[:BYTES_POR_QUADRO]
            sobra = sobra[BYTES_POR_QUADRO:]


def falas(quadros: Iterable[bytes], vad, detector: DetectorDeFala) -> Iterator[bytes]:
    """Passa cada quadro pelo VAD e pelo detector; devolve as falas completas."""
    for quadro in quadros:
        fala = detector.alimentar(quadro, vad.probabilidade(quadro))
        if fala:
            yield fala
