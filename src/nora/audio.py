"""Áudio: WAV em memória (biblioteca padrão) e microfone/alto-falante (sounddevice, opcional)."""

from __future__ import annotations

import io
import re
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
    "e rode 'nora audio' para ver e testar os dispositivos."
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
    # O WDM-KS escreve o nome de outro jeito, mas mantém o modelo entre parênteses no fim:
    # "Headset (@System32\\drivers\\bthhfenum.sys,...;(HAYLOU S40))".
    modelo = re.search(r"\(([^()]+)\)\s*$", nome)
    marca = f"({modelo.group(1)})" if modelo else None

    def mesmo_aparelho(outro: str) -> bool:
        return outro[:31] == base or bool(marca and outro.rstrip().endswith(marca + ")"))

    mesmos = [
        (indice, apis[info["hostapi"]])
        for indice, info in dispositivos
        if info["max_input_channels"] > 0 and mesmo_aparelho(info["name"])
    ]
    ordem = {api: posicao for posicao, api in enumerate(_PREFERENCIA_DE_API)}
    for indice, _api in sorted(mesmos, key=lambda item: ordem.get(item[1], len(ordem))):
        if indice not in candidatos:
            candidatos.append(indice)
    return candidatos


TAXAS_ALTERNATIVAS = (48_000, 44_100, 16_000, 32_000, 22_050, 8_000)


def _abrir_microfone(sd, microfone: int | str | None, callback):
    """Abre o microfone; se falhar, tenta outras taxas, estéreo e o mesmo microfone pelas outras
    APIs de áudio do Windows. Devolve (fluxo já gravando, taxa, canais).

    O fluxo é iniciado aqui porque alguns aparelhos abrem sem erro e só falham ao começar a
    gravar (ex.: fone Bluetooth com o modo de chamada desligado: "dispositivo não conectado").

    Fones Bluetooth são o caso típico: o Windows anuncia 44,1 kHz, mas o microfone deles só
    aceita 16 ou 8 kHz quando está em uso.
    """
    erros: list[str] = []
    for candidato in _candidatos_de_microfone(sd, microfone):
        try:
            info = sd.query_devices(candidato, "input")
            api = sd.query_hostapis(info["hostapi"])["name"] if "hostapi" in info else "?"
        except (sd.PortAudioError, ValueError) as erro:
            erros.append(f"{candidato}: {erro}")
            continue
        taxas = dict.fromkeys((int(info["default_samplerate"]), *TAXAS_ALTERNATIVAS))
        extras = {}
        if "WASAPI" in api and hasattr(sd, "WasapiSettings"):
            # Deixa o Windows converter taxa e canais, em vez de exigir o formato exato do aparelho.
            extras["extra_settings"] = sd.WasapiSettings(auto_convert=True)
        canais_possiveis = dict.fromkeys((1, min(2, int(info["max_input_channels"]) or 1)))
        ultimo = ""
        for taxa in taxas:
            for canais in canais_possiveis:
                try:
                    fluxo = sd.RawInputStream(
                        device=candidato,
                        samplerate=taxa,
                        channels=canais,
                        dtype="int16",
                        callback=callback,
                        **extras,
                    )
                except (sd.PortAudioError, ValueError) as erro:
                    ultimo = str(erro)
                    continue
                try:
                    fluxo.start()
                except sd.PortAudioError as erro:
                    ultimo = str(erro)
                    fluxo.close()
                    continue
                return fluxo, taxa, canais
        rotulo = "padrão" if candidato is None else candidato
        erros.append(
            f"{rotulo} {info.get('name', '')} [{api}], taxas {', '.join(map(str, taxas))} Hz: "
            f"{ultimo}"
        )
    tentativas = "\n    ".join(erros) or "?"
    raise RuntimeError(f"Não consegui abrir o microfone. {_DICA}\n  Tentativas:\n    {tentativas}")


def _para_mono(amostras: bytes, canais: int) -> bytes:
    if canais == 1:
        return amostras
    todas = array("h")
    todas.frombytes(amostras[: len(amostras) // (2 * canais) * 2 * canais])
    return todas[::canais].tobytes()


def gravar_ate_enter(entrada=input, microfone: int | str | None = None) -> bytes:
    """Grava do microfone até a pessoa apertar Enter; devolve um WAV de 16 kHz mono.

    Grava na taxa que o microfone aceita (muitos só aceitam 44,1 ou 48 kHz) e converte
    para 16 kHz, que é o que o Whisper espera.
    """
    sd = _sounddevice()
    blocos: list[bytes] = []

    def guardar(dados, quadros, tempo, status) -> None:
        blocos.append(bytes(dados))

    fluxo, taxa, canais = _abrir_microfone(sd, microfone, guardar)
    try:
        entrada("  (gravando... aperte Enter para parar) ")
    finally:
        fluxo.stop()
        fluxo.close()
    return para_wav(reamostrar(_para_mono(b"".join(blocos), canais), taxa))


class Microfone:
    """Microfone sempre aberto: entrega blocos de PCM 16 kHz mono, conforme chegam."""

    def __init__(self, microfone: int | str | None = None) -> None:
        import queue

        self._sd = _sounddevice()
        self._fila: queue.Queue[bytes] = queue.Queue()
        self._fluxo, self._taxa, self._canais = _abrir_microfone(
            self._sd, microfone, lambda dados, *_: self._fila.put(bytes(dados))
        )

    def __enter__(self) -> Microfone:
        return self  # o fluxo já começa a gravar ao abrir

    def __exit__(self, *args) -> None:
        self._fluxo.stop()
        self._fluxo.close()

    def pausar(self) -> None:
        """Para de captar enquanto a Nora fala. Em fone Bluetooth isso é obrigatório: com o
        microfone aberto o fone fica no modo chamada e a saída de som normal fica muda."""
        if self._fluxo.active:
            self._fluxo.stop()

    def retomar(self) -> None:
        if self._fluxo.stopped:
            self._fluxo.start()

    def limpar(self) -> None:
        """Descarta o que foi captado até agora (ex.: a própria voz da Nora)."""
        while not self._fila.empty():
            self._fila.get_nowait()

    def blocos(self):
        import queue

        while True:
            try:
                # Espera em pedaços curtos: no Windows, uma espera sem prazo ignora o Ctrl+C.
                bloco = self._fila.get(timeout=0.2)
            except queue.Empty:
                yield b""  # sinal de vida: quem consome pode olhar outras coisas (o teclado)
                continue
            yield reamostrar(_para_mono(bloco, self._canais), self._taxa)


def _tocar(sd, amostras: bytes, taxa: int, canais: int, alto_falante) -> None:
    """Toca PCM 16 bits entregando o áudio aos pedaços (callback) e espera terminar.

    O modo "callback" funciona em todas as APIs de áudio do Windows; o modo bloqueante
    (escrever tudo de uma vez) não existe no WDM-KS, a única API que mostra a saída do
    modo chamada de fones Bluetooth."""
    import threading

    terminou = threading.Event()
    posicao = 0
    bytes_por_quadro = 2 * canais

    def entregar(saida, quadros, tempo, status) -> None:
        nonlocal posicao
        pedaco = amostras[posicao : posicao + quadros * bytes_por_quadro]
        posicao += len(pedaco)
        saida[: len(pedaco)] = pedaco
        if len(pedaco) < len(saida):
            saida[len(pedaco) :] = bytes(len(saida) - len(pedaco))
            raise sd.CallbackStop

    fluxo = sd.RawOutputStream(
        device=alto_falante,
        samplerate=taxa,
        channels=canais,
        dtype="int16",
        callback=entregar,
        finished_callback=terminou.set,
    )
    with fluxo:
        segundos = len(amostras) / (bytes_por_quadro * taxa)
        terminou.wait(timeout=segundos + 5)


_avisos_de_saida: list[str] = []


def avisos_de_saida() -> list[str]:
    """Avisos da saída de som ainda não mostrados (e os esquece)."""
    avisos = list(dict.fromkeys(_avisos_de_saida))
    _avisos_de_saida.clear()
    return avisos


def _tocar_em(sd, amostras: bytes, taxa: int, canais: int, alto_falante) -> None:
    """Toca numa saída; se ela recusar a taxa do áudio, converte para a taxa dela."""
    try:
        _tocar(sd, amostras, taxa, canais, alto_falante)
        return
    except sd.PortAudioError:
        if canais != 1:
            raise
    padrao = int(sd.query_devices(alto_falante, "output")["default_samplerate"])
    _tocar(sd, reamostrar(amostras, taxa, padrao), padrao, 1, alto_falante)


def tocar_wav(dados: bytes, alto_falante: int | str | None = None) -> None:
    """Toca um WAV e espera terminar.

    Se a saída escolhida em [audio] alto_falante não abrir (sumiu, mudou de número, ou está
    ocupada por outro programa, como acontece no WDM-KS), toca na saída padrão do Windows."""
    sd = _sounddevice()
    amostras, taxa, canais = ler_wav(dados)
    try:
        _tocar_em(sd, amostras, taxa, canais, alto_falante)
        return
    except (sd.PortAudioError, ValueError) as erro:
        if alto_falante is None:
            raise
        _avisos_de_saida.append(
            f"A saída '{alto_falante}' não abriu ({erro}); usei a saída padrão. "
            "Confira [audio] alto_falante com 'nora audio'."
        )
    _tocar_em(sd, amostras, taxa, canais, None)


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
