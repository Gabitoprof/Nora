"""Áudio: WAV em memória (biblioteca padrão) e microfone/alto-falante (sounddevice, opcional)."""

from __future__ import annotations

import io
import wave
from array import array

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


def reamostrar(amostras: bytes, de: int, para: int = TAXA) -> bytes:
    """Converte áudio PCM 16 bits mono de uma taxa para outra (interpolação linear)."""
    if de == para or not amostras:
        return amostras
    origem = array("h")
    origem.frombytes(amostras)
    total = max(1, round(len(origem) * para / de))
    passo = (len(origem) - 1) / max(1, total - 1)
    destino = array("h", bytes(2 * total))
    ultimo = len(origem) - 1
    for i in range(total):
        posicao = i * passo
        base = int(posicao)
        proximo = min(base + 1, ultimo)
        fracao = posicao - base
        destino[i] = int(origem[base] + (origem[proximo] - origem[base]) * fracao)
    return destino.tobytes()


def dispositivo(valor: str) -> int | str | None:
    """Converte a escolha da config: vazio = padrão do sistema, número = índice, texto = nome."""
    valor = valor.strip()
    if not valor:
        return None
    return int(valor) if valor.isdigit() else valor


_DICA = (
    "Confira: Configurações do Windows > Privacidade e segurança > Microfone > "
    "'Permitir que aplicativos da área de trabalho acessem o microfone'; "
    "e rode 'ella audio' para ver e testar os dispositivos."
)


def _sounddevice():
    try:
        import sounddevice
    except (ImportError, OSError) as erro:
        raise RuntimeError('Falta a parte de áudio. Instale com: pip install -e ".[voz]"') from erro
    return sounddevice


_PREFERENCIA_DE_API = ("Windows WASAPI", "Windows DirectSound", "Windows WDM-KS", "MME")


def _candidatos_de_microfone(sd, microfone: int | str | None) -> list[int | str | None]:
    """O microfone pedido e, depois, o mesmo microfone pelas outras APIs de áudio do Windows.

    No Windows cada microfone aparece uma vez por API (MME, DirectSound, WASAPI, WDM-KS) e às
    vezes só algumas funcionam; o MME ainda corta o nome em 31 caracteres.
    """
    candidatos: list[int | str | None] = [microfone]
    try:
        nome = sd.query_devices(microfone, "input")["name"]
        dispositivos = list(enumerate(sd.query_devices()))
        apis = [sd.query_hostapis(i)["name"] for i in range(len(sd.query_hostapis()))]
    except Exception:
        return candidatos
    base = nome[:31]
    mesmos = [
        (indice, apis[info["hostapi"]])
        for indice, info in dispositivos
        if info["max_input_channels"] > 0 and info["name"][:31] == base
    ]
    ordem = {api: posicao for posicao, api in enumerate(_PREFERENCIA_DE_API)}
    for indice, _api in sorted(mesmos, key=lambda item: ordem.get(item[1], len(ordem))):
        if indice not in candidatos:
            candidatos.append(indice)
    return candidatos


def gravar_ate_enter(entrada=input, microfone: int | str | None = None) -> bytes:
    """Grava do microfone até a pessoa apertar Enter; devolve um WAV de 16 kHz mono.

    Grava na taxa que o microfone aceita (muitos só aceitam 44,1 ou 48 kHz) e converte
    para 16 kHz, que é o que o Whisper espera. Se o microfone não abrir, tenta o mesmo
    microfone por outra API de áudio e em estéreo.
    """
    sd = _sounddevice()
    blocos: list[bytes] = []

    def guardar(dados, quadros, tempo, status) -> None:
        blocos.append(bytes(dados))

    fluxo, taxa, canais, erros = None, TAXA, 1, []
    for candidato in _candidatos_de_microfone(sd, microfone):
        try:
            info = sd.query_devices(candidato, "input")
        except (sd.PortAudioError, ValueError) as erro:
            erros.append(str(erro))
            continue
        taxa = int(info["default_samplerate"])
        for canais in dict.fromkeys((1, min(2, int(info["max_input_channels"]) or 1))):
            try:
                fluxo = sd.RawInputStream(
                    device=candidato,
                    samplerate=taxa,
                    channels=canais,
                    dtype="int16",
                    callback=guardar,
                )
                break
            except (sd.PortAudioError, ValueError) as erro:
                erros.append(str(erro))
        if fluxo is not None:
            break
    if fluxo is None:
        raise RuntimeError(
            f"Não consegui abrir o microfone ({erros[0] if erros else '?'}). {_DICA}"
        )

    with fluxo:
        entrada("  (gravando... aperte Enter para parar) ")
    amostras = b"".join(blocos)
    if canais > 1:
        todas = array("h")
        todas.frombytes(amostras[: len(amostras) // (2 * canais) * 2 * canais])
        amostras = todas[::canais].tobytes()
    return para_wav(reamostrar(amostras, taxa))


def tocar_wav(dados: bytes, alto_falante: int | str | None = None) -> None:
    """Toca um WAV e espera terminar; se a saída recusar a taxa do áudio, converte."""
    sd = _sounddevice()
    amostras, taxa, canais = ler_wav(dados)
    try:
        with sd.RawOutputStream(
            device=alto_falante, samplerate=taxa, channels=canais, dtype="int16"
        ) as saida:
            saida.write(amostras)
        return
    except sd.PortAudioError:
        if canais != 1:
            raise
    padrao = int(sd.query_devices(alto_falante, "output")["default_samplerate"])
    with sd.RawOutputStream(
        device=alto_falante, samplerate=padrao, channels=1, dtype="int16"
    ) as saida:
        saida.write(reamostrar(amostras, taxa, padrao))


def listar_dispositivos() -> list[str]:
    sd = _sounddevice()
    entrada_padrao, saida_padrao = sd.default.device
    linhas = []
    for indice, info in enumerate(sd.query_devices()):
        papeis = []
        if info["max_input_channels"] > 0:
            papeis.append("microfone" + (" (padrão)" if indice == entrada_padrao else ""))
        if info["max_output_channels"] > 0:
            papeis.append("alto-falante" + (" (padrão)" if indice == saida_padrao else ""))
        api = sd.query_hostapis(info["hostapi"])["name"]
        linhas.append(
            f"  {indice:>3}  {info['name']}  [{api}, {int(info['default_samplerate'])} Hz]  "
            + ", ".join(papeis)
        )
    return linhas


def parar_audio() -> None:
    try:
        _sounddevice().stop()
    except RuntimeError:
        pass
