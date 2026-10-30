"""Áudio: WAV em memória (biblioteca padrão) e microfone/alto-falante (sounddevice, opcional)."""

from __future__ import annotations

import io
import wave

TAXA = 16_000  # Hz, o que o Whisper espera


def para_wav(amostras: bytes, taxa: int = TAXA, canais: int = 1) -> bytes:
    """Empacota áudio PCM 16 bits em um arquivo WAV na memória."""
    saida = io.BytesIO()
    with wave.open(saida, "wb") as arquivo:
        arquivo.setnchannels(canais)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa)
        arquivo.writeframes(amostras)
    return saida.getvalue()


def ler_wav(dados: bytes) -> tuple[bytes, int, int]:
    """Devolve (amostras PCM 16 bits, taxa, canais) de um WAV."""
    with wave.open(io.BytesIO(dados), "rb") as arquivo:
        if arquivo.getsampwidth() != 2:
            raise ValueError("Só WAV de 16 bits é suportado.")
        return (
            arquivo.readframes(arquivo.getnframes()),
            arquivo.getframerate(),
            arquivo.getnchannels(),
        )


def duracao_wav(dados: bytes) -> float:
    amostras, taxa, canais = ler_wav(dados)
    return len(amostras) / (2 * canais * taxa)


def _sounddevice():
    try:
        import sounddevice
    except (ImportError, OSError) as erro:
        raise RuntimeError('Falta a parte de áudio. Instale com: pip install -e ".[voz]"') from erro
    return sounddevice


def gravar_ate_enter(entrada=input) -> bytes:
    """Grava do microfone até a pessoa apertar Enter; devolve um WAV de 16 kHz mono."""
    sd = _sounddevice()
    blocos: list[bytes] = []

    def guardar(dados, quadros, tempo, status) -> None:
        blocos.append(bytes(dados))

    with sd.RawInputStream(samplerate=TAXA, channels=1, dtype="int16", callback=guardar):
        entrada("  (gravando... aperte Enter para parar) ")
    return para_wav(b"".join(blocos))


def tocar_wav(dados: bytes) -> None:
    """Toca um WAV e espera terminar."""
    sd = _sounddevice()
    amostras, taxa, canais = ler_wav(dados)
    with sd.RawOutputStream(samplerate=taxa, channels=canais, dtype="int16") as saida:
        saida.write(amostras)


def parar_audio() -> None:
    try:
        _sounddevice().stop()
    except RuntimeError:
        pass
