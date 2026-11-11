"""Voice: turns text into speech (WAV) through the engine chosen in [voz] motor."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from nora.audio import para_wav
from nora.config import Config
from nora.emocao import ajustes_de_voz, para_v3, sem_emocoes
from nora.servico import ServicoIndisponivel, enviar

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"


@dataclass
class VozComPronuncias:
    """Applies the pronunciations the person taught in conversation (stored in memory) before
    sending to the voice. Reads them on every sentence, so what she learned applies at once."""

    voz: object
    fonte: object  # function that returns {word: how to say it}

    def sintetizar(self, texto: str) -> bytes:
        try:
            pronuncias = self.fonte()
        except Exception:  # without memory, speaks without the learned pronunciations
            pronuncias = {}
        return self.voz.sintetizar(aplicar_pronuncias(texto, pronuncias))

    # Attributes of the inner voice (e.g. the fallback notice) pass straight through, read and
    # write.
    def __getattr__(self, nome):
        return getattr(self.voz, nome)

    def __setattr__(self, nome, valor):
        if nome in ("voz", "fonte"):
            object.__setattr__(self, nome, valor)
        else:
            setattr(self.voz, nome, valor)


def com_pronuncias_aprendidas(voz, memoria):
    """The voice, also applying the pronunciations learned in memory (if there is memory)."""
    return voz if memoria is None else VozComPronuncias(voz, memoria.pronuncias)


def aplicar_pronuncias(texto: str, pronuncias: dict[str, str]) -> str:
    """Replaces whole words with how to say them (e.g. 'Nora' -> 'Nóra'), ignoring case."""
    for palavra, fala in pronuncias.items():
        texto = re.sub(rf"\b{re.escape(palavra)}\b", fala, texto, flags=re.IGNORECASE)
    return texto


ELEVENLABS_TAXA = 22_050


@dataclass
class VozHTTP:
    """Local server that takes POST /synthesize with JSON and returns WAV (Kokoro, Piper)."""

    nome: str
    url: str
    extras: dict = field(default_factory=dict)
    pronuncias: dict = field(default_factory=dict)
    timeout: float = 60.0
    ultima_duracao: float = 0.0

    def sintetizar(self, texto: str) -> bytes:
        texto = aplicar_pronuncias(sem_emocoes(texto), self.pronuncias)
        pedido = urllib.request.Request(
            f"{self.url.rstrip('/')}/synthesize",
            data=json.dumps({"text": texto, **self.extras}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        inicio = time.perf_counter()
        wav = enviar(self.nome, pedido, self.timeout)
        self.ultima_duracao = time.perf_counter() - inicio
        return wav


@dataclass
class VozElevenLabs:
    """ElevenLabs cloud voice; requests 16-bit PCM and returns WAV."""

    chave: str = field(repr=False)
    voz_id: str
    modelo: str
    pronuncias: dict = field(default_factory=dict)
    timeout: float = 60.0
    ultima_duracao: float = 0.0
    intensidade: float = 0.5  # of the emotion ([emocao]); 0 = no emotion

    def _preparar(self, texto: str) -> tuple[str, dict | None]:
        """v3 understands audio tags; the other models get the emotion as a voice adjustment."""
        if self.modelo.startswith("eleven_v3"):
            return para_v3(texto, self.intensidade), None
        return sem_emocoes(texto), ajustes_de_voz(texto, self.intensidade)

    def sintetizar(self, texto: str) -> bytes:
        texto, ajustes = self._preparar(texto)
        texto = aplicar_pronuncias(texto, self.pronuncias)
        if not self.chave:
            raise ServicoIndisponivel("Falta ELEVENLABS_API_KEY no .env para usar o ElevenLabs.")
        if not self.voz_id:
            raise ServicoIndisponivel(
                "Falta o voz_id em [voz.elevenlabs] (config/local.toml) para usar o ElevenLabs."
            )
        consulta = urllib.parse.urlencode({"output_format": f"pcm_{ELEVENLABS_TAXA}"})
        pedido = urllib.request.Request(
            f"{ELEVENLABS_API}/{urllib.parse.quote(self.voz_id)}?{consulta}",
            data=json.dumps(
                {
                    "text": texto,
                    "model_id": self.modelo,
                    "language_code": "pt",
                    **({"voice_settings": ajustes} if ajustes else {}),
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json", "xi-api-key": self.chave},
        )
        inicio = time.perf_counter()
        pcm = enviar("o ElevenLabs", pedido, self.timeout)
        self.ultima_duracao = time.perf_counter() - inicio
        return para_wav(pcm, taxa=ELEVENLABS_TAXA)


@dataclass
class VozComReserva:
    """Uses the main voice; if it fails, speaks with the fallback and leaves a notice."""

    principal: VozHTTP | VozElevenLabs
    reserva: VozHTTP | VozElevenLabs
    aviso: str = ""

    def sintetizar(self, texto: str) -> bytes:
        try:
            return self.principal.sintetizar(texto)
        except ServicoIndisponivel as erro:
            try:
                wav = self.reserva.sintetizar(texto)
            except ServicoIndisponivel as erro_reserva:
                raise ServicoIndisponivel(
                    f"{erro} A reserva também falhou: {erro_reserva}"
                ) from erro
            self.aviso = f"{erro} Usei a voz reserva."
            return wav


_PERGUNTA = re.compile(r"([^.!?…]*?)\?+(?=[\s\"'”)»]|$)")


def realcar_perguntas(texto: str, modo: str) -> str:
    """Rewrites the questions so the voice marks the intonation better: "duplo" (??), "invertido"
    (¿...?) or "exclamado" (?!). An empty mode returns the text as is."""
    if not modo:
        return texto

    def trocar(achado: re.Match) -> str:
        corpo = achado.group(1)
        if modo == "duplo":
            return f"{corpo}??"
        if modo == "exclamado":
            return f"{corpo}?!"
        inicio = len(corpo) - len(corpo.lstrip())
        return f"{corpo[:inicio]}¿{corpo[inicio:]}?"

    return _PERGUNTA.sub(trocar, texto)


@dataclass
class VozComRealce:
    """Runs the questions through the emphasis before sending them to the voice."""

    voz: object
    modo: str

    def sintetizar(self, texto: str) -> bytes:
        return self.voz.sintetizar(realcar_perguntas(texto, self.modo))


MARCADOR = "{{texto}}"


def _trocar_texto(no, texto: str) -> tuple[object, int]:
    """Replaces {{texto}} with the sentence in all the flow's texts; returns (flow,
    replacements)."""
    if isinstance(no, str):
        return no.replace(MARCADOR, texto), no.count(MARCADOR)
    if isinstance(no, dict):
        trocas = 0
        novo = {}
        for chave, valor in no.items():
            novo[chave], n = _trocar_texto(valor, texto)
            trocas += n
        return novo, trocas
    if isinstance(no, list):
        itens = [_trocar_texto(valor, texto) for valor in no]
        return [item for item, _ in itens], sum(n for _, n in itens)
    return no, 0


@dataclass
class VozComfyUI:
    """Uses a ComfyUI flow as the voice: replaces {{texto}} with the sentence, requests the run
    through the API (/prompt), waits for it to finish (/history) and downloads the generated audio
    (/view)."""

    url: str
    fluxo: Path
    espera_s: float = 120.0
    pronuncias: dict = field(default_factory=dict)
    campo: str = ""  # "ID.campo": where the sentence goes, instead of {{texto}}
    intervalo: float = 0.2
    ultima_duracao: float = 0.0

    def _pedir(self, caminho: str, corpo: dict | None = None) -> bytes:
        pedido = urllib.request.Request(
            f"{self.url.rstrip('/')}{caminho}",
            data=None if corpo is None else json.dumps(corpo).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        return enviar("o ComfyUI", pedido, 30.0)

    def _carregar_fluxo(self) -> dict:
        try:
            fluxo = json.loads(self.fluxo.read_text(encoding="utf-8"))
        except FileNotFoundError as erro:
            raise ServicoIndisponivel(
                f"Fluxo do ComfyUI não encontrado em {self.fluxo}. Exporte o seu em "
                "'Workflow > Export (API)' e salve nesse caminho."
            ) from erro
        except json.JSONDecodeError as erro:
            raise ServicoIndisponivel(
                f"O fluxo {self.fluxo} não é um JSON válido ({erro})."
            ) from erro
        if isinstance(fluxo, dict) and "nodes" in fluxo and "links" in fluxo:
            raise ServicoIndisponivel(
                f"O fluxo {self.fluxo} está no formato normal do ComfyUI (com 'widgets_values'), "
                "não no formato da API. Exporte de novo em 'Workflow > Export (API)' (se não "
                "aparecer, ligue 'Enable dev mode options' nas configurações do ComfyUI)."
            )
        return fluxo

    def _por_no_campo(self, fluxo: dict, texto: str) -> dict:
        no_id, _, nome = self.campo.partition(".")
        no = fluxo.get(no_id)
        if not isinstance(no, dict) or nome not in no.get("inputs", {}):
            nos = ", ".join(
                f"{chave} ({valor.get('_meta', {}).get('title') or valor.get('class_type', '?')}: "
                f"{', '.join(k for k, v in valor.get('inputs', {}).items() if isinstance(v, str))})"
                for chave, valor in fluxo.items()
                if isinstance(valor, dict)
            )
            raise ServicoIndisponivel(
                f"[voz.comfyui] campo = '{self.campo}' não existe no fluxo. Nós e campos de "
                f"texto: {nos}"
            )
        no["inputs"][nome] = texto
        return fluxo

    def sintetizar(self, texto: str) -> bytes:
        from nora.audio import como_wav_16bits

        texto = aplicar_pronuncias(sem_emocoes(texto), self.pronuncias)
        fluxo = self._carregar_fluxo()
        if self.campo:
            fluxo = self._por_no_campo(fluxo, texto)
        else:
            fluxo, trocas = _trocar_texto(fluxo, texto)
            if not trocas:
                raise ServicoIndisponivel(
                    f"O fluxo {self.fluxo} não tem {MARCADOR}: escreva {MARCADOR} no nó de "
                    'texto, ou diga o nó e o campo em [voz.comfyui] campo (ex.: "12.text").'
                )
        inicio = time.perf_counter()
        resposta = json.loads(
            self._pedir("/prompt", {"prompt": fluxo, "client_id": f"nora-{uuid.uuid4().hex}"})
        )
        if "prompt_id" not in resposta:
            raise ServicoIndisponivel(
                f"O ComfyUI recusou o fluxo: {resposta.get('error', resposta)}"
            )
        prompt_id = resposta["prompt_id"]
        while True:
            historico = json.loads(self._pedir(f"/history/{prompt_id}")).get(prompt_id)
            if historico:
                status = historico.get("status", {})
                if status.get("status_str") == "error":
                    raise ServicoIndisponivel("O fluxo do ComfyUI deu erro (veja a janela dele).")
                audios = [
                    arquivo
                    for saida in historico.get("outputs", {}).values()
                    for arquivo in saida.get("audio", [])
                ]
                if audios:
                    break
                if status.get("completed"):
                    raise ServicoIndisponivel(
                        "O fluxo do ComfyUI terminou sem gerar áudio. Ele precisa de um nó que "
                        "salve o áudio (ex.: Save Audio)."
                    )
            if time.perf_counter() - inicio > self.espera_s:
                raise ServicoIndisponivel(
                    f"O ComfyUI não terminou em {self.espera_s:.0f} s ([voz.comfyui] espera_s)."
                )
            time.sleep(self.intervalo)
        arquivo = audios[0]
        consulta = urllib.parse.urlencode(
            {
                "filename": arquivo["filename"],
                "subfolder": arquivo.get("subfolder", ""),
                "type": arquivo.get("type", "output"),
            }
        )
        wav = como_wav_16bits(self._pedir(f"/view?{consulta}"))
        self.ultima_duracao = time.perf_counter() - inicio
        return wav


def _criar_motor(config: Config, motor: str, realce: str | None = None):
    """The requested voice engine, with the config's question emphasis (or the given `realce`)."""
    motor_puro = _criar_motor_puro(config, motor)
    modo = config.voz.realce_pergunta if realce is None else realce
    return VozComRealce(motor_puro, modo) if modo else motor_puro


def _criar_motor_puro(config: Config, motor: str) -> VozHTTP | VozElevenLabs | VozComfyUI:
    voz = config.voz
    assistente = config.assistente
    pronuncias = dict(voz.pronuncias)
    if assistente.pronuncia:
        pronuncias[assistente.nome] = assistente.pronuncia
    if motor == "kokoro":
        extras = {"voice": voz.kokoro.voz, "speed": voz.kokoro.velocidade}
        return VozHTTP("o Kokoro", voz.kokoro.url, extras, pronuncias)
    if motor == "piper":
        # length_scale is the duration of each sound: higher = slower
        extras = {"length_scale": round(1 / voz.piper.velocidade, 3)}
        if voz.piper.variacao:  # sound variation: higher = more expressive (and more noise)
            extras["noise_scale"] = voz.piper.variacao
        if voz.piper.variacao_ritmo:  # rhythm variation: higher = less monotone
            extras["noise_w_scale"] = voz.piper.variacao_ritmo
        return VozHTTP("o Piper", voz.piper.url, extras, pronuncias)
    if motor == "comfyui":
        comfy = voz.comfyui
        return VozComfyUI(comfy.url, comfy.fluxo, comfy.espera_s, pronuncias, comfy.campo)
    intensidade = config.emocao.intensidade if config.emocao.ativa else 0.0
    return VozElevenLabs(
        config.chave_elevenlabs,
        voz.elevenlabs.voz_id,
        voz.elevenlabs.modelo,
        pronuncias,
        intensidade=intensidade,
    )


def criar_voz(config: Config) -> VozHTTP | VozElevenLabs | VozComReserva:
    principal = _criar_motor(config, config.voz.motor)
    if not config.voz.reserva:
        return principal
    return VozComReserva(principal, _criar_motor(config, config.voz.reserva))


NOMES_DAS_VOZES = {
    "elevenlabs": "ElevenLabs",
    "piper": "Piper",
    "kokoro": "Kokoro",
    "comfyui": "ComfyUI",
}


class VozTrocavel:
    """The conversation's voice, which can be switched by speaking ("usa a voz do Piper"). The
    switch lasts until Nora closes; when she opens again, [voz] motor is back."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.motor = config.voz.motor
        self.voz = self._montar(self.motor)

    def _montar(self, motor: str):
        """The requested engine, with the config's fallback (or the config's main voice, if the
        fallback is the requested engine itself)."""
        principal = _criar_motor(self.config, motor)
        reserva = self.config.voz.reserva
        if reserva == motor:
            reserva = self.config.voz.motor if self.config.voz.motor != motor else ""
        return (
            VozComReserva(principal, _criar_motor(self.config, reserva)) if reserva else principal
        )

    def sintetizar(self, texto: str) -> bytes:
        return self.voz.sintetizar(texto)

    @property
    def aviso(self) -> str:
        return getattr(self.voz, "aviso", "")

    @aviso.setter
    def aviso(self, valor: str) -> None:
        if isinstance(self.voz, VozComReserva):
            self.voz.aviso = valor

    def trocar(self, motor: str, frase: str) -> bytes:
        """Switches to speaking with `motor`, saying `frase` with it right away. If the new voice
        does not answer, raises ServicoIndisponivel and keeps the previous one (the fallback is not
        part of the test)."""
        nova = self._montar(motor)
        teste = nova.principal if isinstance(nova, VozComReserva) else nova
        try:
            wav = teste.sintetizar(frase)
        except ServicoIndisponivel:
            raise
        except Exception as erro:  # incomplete config, missing ComfyUI flow...
            raise ServicoIndisponivel(str(erro)) from erro
        self.voz, self.motor = nova, motor
        return wav
