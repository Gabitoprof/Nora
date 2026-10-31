"""Voz: transforma texto em fala (WAV) pelo motor escolhido em [voz] motor."""

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
from nora.servico import ServicoIndisponivel, enviar

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"


def aplicar_pronuncias(texto: str, pronuncias: dict[str, str]) -> str:
    """Troca palavras inteiras pelo jeito de falar (ex.: 'Nora' -> 'Nóra'), sem olhar maiúsculas."""
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

    chave: str = field(repr=False)
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


@dataclass
class VozComReserva:
    """Usa a voz principal; se ela falhar, fala com a reserva e deixa um aviso."""

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
    """Reescreve as perguntas para a voz marcar melhor a entonação: "duplo" (??), "invertido"
    (¿...?) ou "exclamado" (?!). Modo vazio devolve o texto como está."""
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
    """Passa as perguntas pelo realce antes de mandar à voz."""

    voz: object
    modo: str

    def sintetizar(self, texto: str) -> bytes:
        return self.voz.sintetizar(realcar_perguntas(texto, self.modo))


MARCADOR = "{{texto}}"


def _trocar_texto(no, texto: str) -> tuple[object, int]:
    """Troca {{texto}} pela frase em todos os textos do fluxo; devolve (fluxo, quantas trocas)."""
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
    """Usa um fluxo do ComfyUI como voz: troca {{texto}} pela frase, pede a execução pela API
    (/prompt), espera terminar (/history) e baixa o áudio gerado (/view)."""

    url: str
    fluxo: Path
    espera_s: float = 120.0
    pronuncias: dict = field(default_factory=dict)
    campo: str = ""  # "ID.campo": onde vai a frase, em vez de {{texto}}
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

        texto = aplicar_pronuncias(texto, self.pronuncias)
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
    """O motor de voz pedido, com o realce de perguntas da config (ou o `realce` dado)."""
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
        return VozHTTP("o Piper", voz.piper.url, pronuncias=pronuncias)
    if motor == "comfyui":
        comfy = voz.comfyui
        return VozComfyUI(comfy.url, comfy.fluxo, comfy.espera_s, pronuncias, comfy.campo)
    return VozElevenLabs(
        config.chave_elevenlabs, voz.elevenlabs.voz_id, voz.elevenlabs.modelo, pronuncias
    )


def criar_voz(config: Config) -> VozHTTP | VozElevenLabs | VozComReserva:
    principal = _criar_motor(config, config.voz.motor)
    if not config.voz.reserva:
        return principal
    return VozComReserva(principal, _criar_motor(config, config.voz.reserva))
