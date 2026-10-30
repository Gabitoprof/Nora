"""Voz: transforma texto em fala (WAV) pelo motor escolhido em [voz] motor."""

from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from ella.audio import para_wav
from ella.config import Config
from ella.servico import ServicoIndisponivel, enviar

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"


def aplicar_pronuncias(texto: str, pronuncias: dict[str, str]) -> str:
    """Troca palavras inteiras pelo jeito de falar (ex.: 'Ella' -> 'Élha'), sem olhar maiúsculas."""
    for palavra, fala in pronuncias.items():
        texto = re.sub(rf"\b{re.escape(palavra)}\b", fala, texto, flags=re.IGNORECASE)
    return texto


ELEVENLABS_TAXA = 22_050


@dataclass
class VozHTTP:
    """Servidor local que recebe POST /synthesize com JSON e devolve WAV (Kokoro, Piper)."""

    nome: str
    url: str
    extras: dict = field(default_factory=dict)
    pronuncias: dict = field(default_factory=dict)
    timeout: float = 60.0
    ultima_duracao: float = 0.0

    def sintetizar(self, texto: str) -> bytes:
        texto = aplicar_pronuncias(texto, self.pronuncias)
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
    """Voz na nuvem do ElevenLabs; pede PCM 16 bits e devolve WAV."""

    chave: str
    voz_id: str
    modelo: str
    pronuncias: dict = field(default_factory=dict)
    timeout: float = 60.0
    ultima_duracao: float = 0.0

    def sintetizar(self, texto: str) -> bytes:
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
            data=json.dumps({"text": texto, "model_id": self.modelo, "language_code": "pt"}).encode(
                "utf-8"
            ),
            headers={"Content-Type": "application/json", "xi-api-key": self.chave},
        )
        inicio = time.perf_counter()
        pcm = enviar("o ElevenLabs", pedido, self.timeout)
        self.ultima_duracao = time.perf_counter() - inicio
        return para_wav(pcm, taxa=ELEVENLABS_TAXA)


def criar_voz(config: Config) -> VozHTTP | VozElevenLabs:
    voz = config.voz
    assistente = config.assistente
    pronuncias = {assistente.nome: assistente.pronuncia} if assistente.pronuncia else {}
    if voz.motor == "kokoro":
        extras = {"voice": voz.kokoro.voz, "speed": voz.kokoro.velocidade}
        return VozHTTP("o Kokoro", voz.kokoro.url, extras, pronuncias)
    if voz.motor == "piper":
        return VozHTTP("o Piper", voz.piper.url, pronuncias=pronuncias)
    return VozElevenLabs(
        config.chave_elevenlabs, voz.elevenlabs.voz_id, voz.elevenlabs.modelo, pronuncias
    )
