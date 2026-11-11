"""Audio: in-memory WAV (standard library) and microphone/speaker (sounddevice, optional)."""

from __future__ import annotations

import io
import re
import time
import wave
from array import array
from collections.abc import Callable, Iterable, Iterator

TAXA = 16_000  # Hz, what Whisper expects


def para_wav(amostras: bytes, taxa: int = TAXA, canais: int = 1) -> bytes:
    """Packs 16-bit PCM audio into an in-memory WAV file."""
    saida = io.BytesIO()
    with wave.open(saida, "wb") as arquivo:
        arquivo.setnchannels(canais)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa)
        arquivo.writeframes(amostras)
    return saida.getvalue()


def ler_wav(dados: bytes) -> tuple[bytes, int, int]:
    """Returns (16-bit PCM samples, rate, channels) from a WAV."""
    with wave.open(io.BytesIO(dados), "rb") as arquivo:
        if arquivo.getsampwidth() != 2:
            raise ValueError("Só WAV de 16 bits é suportado.")
        return (
            arquivo.readframes(arquivo.getnframes()),
            arquivo.getframerate(),
            arquivo.getnchannels(),
        )


def como_wav_16bits(dados: bytes) -> bytes:
    """Any audio (16- or 32-bit WAV, FLAC, MP3...) as 16-bit mono PCM WAV, which is what Nora
    plays. 16-bit WAV passes straight through; the rest needs the soundfile package."""
    try:
        amostras, taxa, canais = ler_wav(dados)
        return para_wav(_para_mono(amostras, canais), taxa)
    except (ValueError, EOFError, wave.Error):
        pass
    try:
        import numpy
        import soundfile
    except ImportError as erro:
        raise RuntimeError(
            'Para tocar este formato de áudio, instale: pip install -e ".[voz]"'
        ) from erro
    sinal, taxa = soundfile.read(io.BytesIO(dados), dtype="float32", always_2d=True)
    mono = sinal.mean(axis=1)
    pcm = (numpy.clip(mono, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return para_wav(pcm, int(taxa))


def duracao_wav(dados: bytes) -> float:
    amostras, taxa, canais = ler_wav(dados)
    return len(amostras) / (2 * canais * taxa)


def reamostrar(amostras: bytes, de: int, para: int = TAXA) -> bytes:
    """Converts 16-bit mono PCM audio from one rate to another (linear interpolation)."""
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


def reamostrar_qualidade(amostras: bytes, de: int, para: int) -> bytes:
    """Like reamostrar, but with a frequency cutoff (through the FFT, with numpy): it neither
    muffles nor adds hiss when lowering the rate. For preparing training audio; without numpy, uses
    the simple version."""
    if de == para or not amostras:
        return amostras
    try:
        import numpy
    except ImportError:
        return reamostrar(amostras, de, para)
    sinal = numpy.frombuffer(amostras, dtype="<i2").astype(numpy.float64)
    folga = de // 10  # silence at the edges: the FFT treats the signal as cyclic
    sinal = numpy.pad(sinal, folga)
    total = max(1, round(len(sinal) * para / de))
    espectro = numpy.fft.rfft(sinal)
    novo = numpy.zeros(total // 2 + 1, dtype=complex)
    bins = min(len(novo), len(espectro))
    novo[:bins] = espectro[:bins]
    saida = numpy.fft.irfft(novo, total) * (total / len(sinal))
    corte = round(folga * para / de)
    saida = saida[corte : len(saida) - corte] if corte else saida
    return numpy.clip(numpy.round(saida), -32768, 32767).astype("<i2").tobytes()


def dispositivo(valor: str) -> int | str | None:
    """Converts the config choice: empty = system default, number = index, text = name."""
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
    except ModuleNotFoundError as erro:
        if erro.name == "sounddevice":
            raise RuntimeError(
                'Falta a parte de áudio. Instale com: pip install -e ".[voz]"'
            ) from erro
        raise RuntimeError(_audio_nao_carregou(erro)) from erro
    except (ImportError, OSError) as erro:
        raise RuntimeError(_audio_nao_carregou(erro)) from erro
    return sounddevice


def _audio_nao_carregou(erro: BaseException) -> str:
    """The package is there, but does not load: shows the real cause. The common case is a .venv
    recreated with another Python version, with the packages compiled for the old one."""
    return (
        f"A parte de áudio está instalada, mas não carregou: {erro}. "
        "Se o .venv foi recriado com outra versão do Python, reinstale nele: "
        'python -m pip install --force-reinstall -e ".[voz]"'
    )


_PREFERENCIA_DE_API = ("Windows WASAPI", "Windows DirectSound", "Windows WDM-KS", "MME")


def _candidatos_de_microfone(sd, microfone: int | str | None) -> list[int | str | None]:
    """The requested microphone and, after it, the same microphone through Windows' other audio
    APIs.

    On Windows each microphone shows up once per API (MME, DirectSound, WASAPI, WDM-KS) and
    sometimes only some of them work; MME also cuts the name at 31 characters.
    """
    candidatos: list[int | str | None] = [microfone]
    try:
        nome = sd.query_devices(microfone, "input")["name"]
        dispositivos = list(enumerate(sd.query_devices()))
        apis = [sd.query_hostapis(i)["name"] for i in range(len(sd.query_hostapis()))]
    except Exception:
        return candidatos
    base = nome[:31]
    # WDM-KS writes the name differently, but keeps the model in parentheses at the end:
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
    """Opens the microphone; if it fails, tries other rates, stereo and the same microphone through
    Windows' other audio APIs. Returns (stream already recording, rate, channels).

    The stream is started here because some devices open without error and only fail when they
    start recording (e.g. a Bluetooth headset with call mode off: "dispositivo não conectado").

    Bluetooth headsets are the typical case: Windows announces 44.1 kHz, but their microphone
    only accepts 16 or 8 kHz while in use.
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
            # Lets Windows convert rate and channels, instead of requiring the device's exact
            # format.
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
    """Records from the microphone until the person presses Enter; returns a 16 kHz mono WAV.

    Records at the rate the microphone accepts (many only accept 44.1 or 48 kHz) and converts
    to 16 kHz, which is what Whisper expects.
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
    """Always-open microphone: delivers 16 kHz mono PCM blocks as they arrive."""

    def __init__(self, microfone: int | str | None = None) -> None:
        import queue

        self._sd = _sounddevice()
        self._fila: queue.Queue[bytes] = queue.Queue()
        self._fluxo, self._taxa, self._canais = _abrir_microfone(
            self._sd, microfone, lambda dados, *_: self._fila.put(bytes(dados))
        )

    def __enter__(self) -> Microfone:
        return self  # the stream starts recording on opening

    def __exit__(self, *args) -> None:
        self._fluxo.stop()
        self._fluxo.close()

    def pausar(self) -> None:
        """Stops capturing while Nora speaks. On a Bluetooth headset this is mandatory: with the
        microphone open the headset stays in call mode and the normal sound output goes mute."""
        if self._fluxo.active:
            self._fluxo.stop()

    def retomar(self) -> None:
        if self._fluxo.stopped:
            self._fluxo.start()

    def limpar(self) -> None:
        """Discards what was captured so far (e.g. Nora's own voice)."""
        while not self._fila.empty():
            self._fila.get_nowait()

    def blocos(self):
        import queue

        while True:
            try:
                # Waits in short pieces: on Windows, a wait without a timeout ignores Ctrl+C.
                bloco = self._fila.get(timeout=0.2)
            except queue.Empty:
                yield b""  # sign of life: the consumer can check other things (the keyboard)
                continue
            convertido = reamostrar(_para_mono(bloco, self._canais), self._taxa)
            from nora.hud import amostrar_pcm

            amostrar_pcm(bloco, "microfone", self._taxa, self._canais)
            yield convertido


def _tocar(sd, amostras: bytes, taxa: int, canais: int, alto_falante) -> None:
    """Plays 16-bit PCM by handing the audio over in pieces (callback) and waits for it to finish.

    The "callback" mode works on all Windows audio APIs; the blocking mode (writing everything
    at once) does not exist on WDM-KS, the only API that shows the call-mode output of
    Bluetooth headsets."""
    import threading

    terminou = threading.Event()
    posicao = 0
    iniciou = False
    bytes_por_quadro = 2 * canais
    from nora.hud import preparar_reproducao

    observador = preparar_reproducao(amostras, taxa, canais)

    def entregar(saida, quadros, tempo, status) -> None:
        nonlocal posicao, iniciou
        from nora.hud import reproducao

        if not iniciou:
            reproducao(True)  # first real output callback, not the start of synthesis
            iniciou = True
        antes = posicao
        pedaco = amostras[posicao : posicao + quadros * bytes_por_quadro]
        posicao += len(pedaco)
        if observador is not None:
            try:
                observador.entregar(antes // bytes_por_quadro, posicao // bytes_por_quadro, tempo)
            except Exception as erro:  # the HUD never stops speech; the failure is counted
                from nora.falhas_hud import registrar

                registrar("audio.entregar", erro)
        saida[: len(pedaco)] = pedaco
        if len(pedaco) < len(saida):
            saida[len(pedaco) :] = bytes(len(saida) - len(pedaco))
            raise sd.CallbackStop

    try:
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
    finally:
        from nora.hud import reproducao

        por_ms = bytes_por_quadro * taxa / 1000
        reproducao(False, (posicao / por_ms, len(amostras) / por_ms, posicao < len(amostras)))


_avisos_de_saida: list[str] = []


def avisos_de_saida() -> list[str]:
    """Sound output notices not shown yet (and forgets them)."""
    avisos = list(dict.fromkeys(_avisos_de_saida))
    _avisos_de_saida.clear()
    return avisos


def _tocar_em(sd, amostras: bytes, taxa: int, canais: int, alto_falante) -> None:
    """Plays on an output; if it refuses the audio's rate, converts to its rate."""
    try:
        _tocar(sd, amostras, taxa, canais, alto_falante)
        return
    except sd.PortAudioError:
        if canais != 1:
            raise
    padrao = int(sd.query_devices(alto_falante, "output")["default_samplerate"])
    _tocar(sd, reamostrar(amostras, taxa, padrao), padrao, 1, alto_falante)


def com_silencio_inicial(dados: bytes, ms: int) -> bytes:
    """Adds a little silence before the sound. Bluetooth headsets and some sound cards "wake up"
    after the sound has started and swallow the beginning ("Oi" comes out cut)."""
    if ms <= 0:
        return dados
    amostras, taxa, canais = ler_wav(dados)
    silencio = b"\x00\x00" * canais * (taxa * ms // 1000)
    return para_wav(silencio + amostras, taxa, canais)


class AudioEmPartes:
    """16-bit PCM audio that is still arriving (streaming voice). A thread of its own downloads the
    parts as soon as it is created; the player starts with the first ones, without waiting."""

    def __init__(self, partes: Iterable[bytes], taxa: int, canais: int = 1) -> None:
        import queue
        import threading

        self.taxa = taxa
        self.canais = canais
        self.erro: Exception | None = None
        self.primeira = threading.Event()  # the first part arrived (or it ended without any)
        self.baixado = threading.Event()  # everything arrived (or there was an error)
        self.cancelado = threading.Event()  # barge-in: stop playing and discard the rest
        # Words with real timing (voice alignment), for the HUD; the version goes up on every
        # change.
        self.palavras: list[dict] = []
        self.versao_palavras = 0
        self.texto = ""  # the whole text, to estimate the words if no alignment comes
        # Playback measurements (diagnostics): when the sound started and the silence from missing
        # data.
        self.inicio_som: float | None = None
        self.silencio_ms = 0.0
        self.maior_silencio_ms = 0.0
        self._fila: queue.Queue = queue.Queue()
        threading.Thread(target=self._baixar, args=(partes,), daemon=True).start()

    @classmethod
    def de_fila(cls, taxa: int, canais: int = 1):
        """Audio fed in pieces by the caller (e.g. a WebSocket). Returns
        (audio, pôr(pcm), fechar(erro=None))."""
        import queue

        fila: queue.Queue = queue.Queue()

        def partes():
            while (item := fila.get()) is not None:
                if isinstance(item, BaseException):
                    raise item
                yield item

        audio = cls(partes(), taxa, canais)

        def fechar(erro: BaseException | None = None) -> None:
            if erro is not None:
                fila.put(erro)
            fila.put(None)

        return audio, fila.put, fechar

    def cancelar(self) -> None:
        """Stops playback immediately (the rest of the audio is discarded)."""
        self.cancelado.set()

    def definir_palavras(self, palavras: list[dict]) -> None:
        self.palavras = palavras
        self.versao_palavras += 1

    def _baixar(self, partes: Iterable[bytes]) -> None:
        sobra = b""  # a byte of a sample cut in half, which goes with the next part
        quadro = 2 * self.canais
        try:
            for parte in partes:
                dados = sobra + parte
                inteiro = len(dados) - len(dados) % quadro
                sobra = dados[inteiro:]
                if inteiro:
                    self._fila.put(dados[:inteiro])
                    self.primeira.set()
        except Exception as erro:  # the internet dropped midway: play what arrived
            self.erro = erro
        finally:
            self._fila.put(None)
            self.primeira.set()
            self.baixado.set()

    def partes(self) -> Iterator[bytes]:
        """The parts in order, as they arrive (can only be iterated once)."""
        while (parte := self._fila.get()) is not None:
            yield parte

    def tudo(self) -> bytes:
        """Waits for everything to arrive and returns the whole PCM; raises the error if the
        download dropped."""
        pcm = b"".join(self.partes())
        if self.erro is not None:
            raise self.erro
        return pcm


# How much audio to gather before opening the speaker: less than this and a network delay becomes
# a gap in the sound.
PRE_CARGA_S = 0.15


def _deslocar(palavras: list[dict], atraso_ms: float) -> list[dict]:
    """The aligned words at the real position of the played audio (after the initial silence)."""
    if not atraso_ms:
        return list(palavras)
    return [
        {**p, "inicio_ms": p["inicio_ms"] + atraso_ms, "fim_ms": p["fim_ms"] + atraso_ms}
        for p in palavras
    ]


def _tocar_partes(sd, audio: AudioEmPartes, silencio_ms: int, alto_falante) -> None:
    """Plays the audio as it arrives. If the output refuses the rate, converts each part."""
    import threading

    taxa, canais = audio.taxa, audio.canais
    bytes_por_quadro = 2 * canais
    buffer = bytearray(b"\x00\x00" * canais * (taxa * max(0, silencio_ms) // 1000))
    trava = threading.Lock()
    chegou = threading.Event()  # everything downloaded and put in the buffer
    terminou = threading.Event()
    saida_taxa = [taxa]
    observador = None
    posicao = 0
    iniciou = False
    buraco = [0.0]  # continuous silence from missing data (the longest becomes diagnostics)
    # The initial silence (Bluetooth headsets) comes before the voice PCM: the words shift with it.
    atraso_ms = float(max(0, silencio_ms))

    def observar(metodo, *args):
        if observador is not None:
            try:
                getattr(observador, metodo)(*args)
            except Exception as erro:  # the HUD never stops speech; the failure is counted
                from nora.falhas_hud import registrar

                registrar(f"audio.{metodo}", erro)

    def encher() -> None:
        versao = 0
        for parte in audio.partes():
            if audio.cancelado.is_set():
                break
            if saida_taxa[0] != taxa:
                parte = reamostrar(parte, taxa, saida_taxa[0])
            observar("receber_pcm", parte)
            if audio.versao_palavras != versao:  # real voice alignment: words for the HUD
                versao = audio.versao_palavras
                observar("alinhar", _deslocar(audio.palavras, atraso_ms))
            with trava:
                buffer.extend(parte)
        if audio.texto and not audio.palavras:
            observar("definir_texto", audio.texto)
        observar("concluir_tempos")
        chegou.set()

    def entregar(saida, quadros, tempo, status) -> None:
        nonlocal posicao, iniciou
        from nora.hud import reproducao

        if not iniciou:
            reproducao(True)
            iniciou = True
        precisa = quadros * bytes_por_quadro
        if audio.cancelado.is_set():  # barge-in: silence now, without playing the rest
            saida[:] = bytes(len(saida))
            raise sd.CallbackStop
        with trava:
            pedaco = bytes(buffer[:precisa])
            del buffer[:precisa]
            acabou = chegou.is_set() and not buffer
        saida[: len(pedaco)] = pedaco
        if pedaco and audio.inicio_som is None:
            audio.inicio_som = time.perf_counter()
        if len(pedaco) < precisa:
            saida[len(pedaco) :] = bytes(precisa - len(pedaco))
            if audio.inicio_som is not None and not acabou:  # gap: the network was late
                falta = (precisa - len(pedaco)) / bytes_por_quadro / saida_taxa[0] * 1000
                audio.silencio_ms += falta
                buraco[0] += falta
                audio.maior_silencio_ms = max(audio.maior_silencio_ms, buraco[0])
        else:
            buraco[0] = 0.0
        anterior = posicao
        posicao += len(pedaco) // bytes_por_quadro  # zeros from network gaps do not advance words
        observar("entregar_pcm", saida, anterior, posicao, tempo)
        if len(pedaco) < precisa and acabou:
            raise sd.CallbackStop

    def abrir(taxa_saida: int):
        return sd.RawOutputStream(
            device=alto_falante,
            samplerate=taxa_saida,
            channels=canais,
            dtype="int16",
            callback=entregar,
            finished_callback=terminou.set,
        )

    try:
        fluxo = abrir(taxa)
    except sd.PortAudioError:
        if canais != 1:
            raise
        saida_taxa[0] = int(sd.query_devices(alto_falante, "output")["default_samplerate"])
        with trava:
            buffer[:] = reamostrar(bytes(buffer), taxa, saida_taxa[0])
        fluxo = abrir(saida_taxa[0])
    from nora.hud import preparar_reproducao, reproducao

    observador = preparar_reproducao(None, saida_taxa[0], canais)
    observar("receber_pcm", bytes(buffer))
    try:
        threading.Thread(target=encher, daemon=True).start()
        pre_carga = int(saida_taxa[0] * PRE_CARGA_S) * bytes_por_quadro
        while not chegou.wait(0.01):
            with trava:
                if len(buffer) >= pre_carga:
                    break
        with fluxo:
            while not terminou.wait(0.1):
                pass
    finally:
        with trava:
            restante = len(buffer) // bytes_por_quadro
        natural = chegou.is_set() and restante == 0 and not audio.cancelado.is_set()
        quadros_ms = saida_taxa[0] / 1000
        reproducao(False, (posicao / quadros_ms, (posicao + restante) / quadros_ms, not natural))


def tocar_partes(audio: AudioEmPartes, alto_falante=None, silencio_ms: int = 0) -> None:
    """Plays a streaming audio and waits for it to finish. If the chosen output does not open, plays
    on the default one (like tocar_wav)."""
    sd = _sounddevice()
    try:
        _tocar_partes(sd, audio, silencio_ms, alto_falante)
        return
    except (sd.PortAudioError, ValueError) as erro:
        if alto_falante is None:
            raise
        _avisos_de_saida.append(
            f"A saída '{alto_falante}' não abriu ({erro}); usei a saída padrão. "
            "Confira [audio] alto_falante com 'nora audio'."
        )
    _tocar_partes(sd, audio, silencio_ms, None)


def tocador(config_audio) -> Callable[[bytes | AudioEmPartes], None]:
    """Function that plays a WAV (or a streaming audio) on the config's output ([audio]
    alto_falante and silencio_inicial_ms)."""
    alto_falante = dispositivo(config_audio.alto_falante)
    ms = config_audio.silencio_inicial_ms

    def tocar(audio: bytes | AudioEmPartes) -> None:
        if isinstance(audio, AudioEmPartes):
            tocar_partes(audio, alto_falante, ms)
        else:
            tocar_wav(com_silencio_inicial(audio, ms), alto_falante)

    return tocar


def tocar_wav(dados: bytes, alto_falante: int | str | None = None) -> None:
    """Plays a WAV and waits for it to finish.

    If the output chosen in [audio] alto_falante does not open (it disappeared, changed number,
    or is taken by another program, as happens on WDM-KS), plays on the Windows default output."""
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
