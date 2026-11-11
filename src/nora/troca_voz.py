"""Switching the voice by speaking: "usa a voz do Piper", "volta pro ElevenLabs", "qual voz você
está usando?". Works in the voice modes (nora ouvir, nora falar, nora conversar --voz)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from nora.servico import ServicoIndisponivel
from nora.voz import NOMES_DAS_VOZES

_MOTORES = (
    ("elevenlabs", r"eleven ?labs|11 ?labs|onze ?labs|eleven"),
    ("piper", r"piper|paiper|norav1"),
    ("kokoro", r"kokoro|cocoro"),
    ("comfyui", r"comfy ?ui|comfy"),
)
_VERBOS = (
    r"\b(usa|use|usar|utiliza|utilize|troca|troque|trocar|muda|mude|mudar|passa|passe|passar|"
    r"volta|volte|voltar|liga|ligue|coloca|coloque|bota|bote)\b"
)
_FALA_COM = r"\b(fala|fale|falar)\b (com|usando|na|pela) (a )?voz\b"
_PADRAO = r"\bvoz (normal|padrao|principal|de sempre|original)\b"
_QUAL = r"\b(qual|que) (e a )?(sua )?voz\b.{0,30}\b(usando|essa|agora|atual)\b"
# A question or comparison about the voices: not a switch request.
_PERGUNTA = (
    r"\b(melhor|pior|diferenca|compara|comparar|comparando|como|por que|porque|o que|quem|"
    r"quando|onde|qual|quais|acha|ou o|ou a)\b"
)
_DESTINO = r"\b(para|pra|pro|pela|pelo)\b"


@dataclass(frozen=True)
class PedidoDeVoz:
    acao: str  # "trocar" or "qual"
    motor: str = ""  # "" with "trocar" = the config's voice


def _texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", limpo).split())


def _motores(texto: str) -> list[str]:
    """The engines mentioned in the text, in the order they appear (no repeats)."""
    achados = sorted(
        (achado.start(), motor)
        for motor, nomes in _MOTORES
        for achado in re.finditer(rf"\b({nomes})\b", texto)
    )
    return list(dict.fromkeys(motor for _, motor in achados))


def pedido_de_voz(texto: str) -> PedidoDeVoz | None:
    """The voice switch request in the speech, if that is all it is (short sentence, clear intent).
    Asking about an engine ("o Piper é melhor que o Kokoro?") switches nothing."""
    limpo = _texto(texto)
    if not limpo or len(limpo.split()) > 12:
        return None
    if re.search(_QUAL, limpo):
        return PedidoDeVoz("qual")
    if not (re.search(_VERBOS, limpo) or re.search(_FALA_COM, limpo)):
        return None
    if re.search(_PERGUNTA, limpo):
        return None
    motores = _motores(limpo)
    if len(motores) > 1:  # "troca do Kokoro para o Piper": what comes after "para" wins
        destinos = list(re.finditer(_DESTINO, limpo))
        depois = _motores(limpo[destinos[-1].end() :]) if destinos else []
        return PedidoDeVoz("trocar", depois[0]) if len(depois) == 1 else None
    if motores:
        return PedidoDeVoz("trocar", motores[0])
    if re.search(_PADRAO, limpo):
        return PedidoDeVoz("trocar")
    return None


def atender_pedido(voz, pedido: PedidoDeVoz, padrao: str) -> tuple[str, bytes | None]:
    """Makes the switch and returns (what she answers, the audio already spoken in the new voice).
    Without audio, the answer must be spoken with the current voice."""
    atual = getattr(voz, "motor", "")
    if pedido.acao == "qual" or not hasattr(voz, "trocar"):
        if not atual:
            return "Aqui não consigo trocar de voz.", None
        return f"Estou falando com a voz do {NOMES_DAS_VOZES[atual]}.", None
    motor = pedido.motor or padrao
    nome = NOMES_DAS_VOZES[motor]
    if motor == atual:
        return f"Já estou falando com a voz do {nome}.", None
    resposta = f"Pronto, agora falo com a voz do {nome}."
    try:
        return resposta, voz.trocar(motor, resposta)
    except ServicoIndisponivel as erro:
        return (
            f"Não consegui usar a voz do {nome}: {erro} "
            f"Continuo com a voz do {NOMES_DAS_VOZES[atual]}."
        ), None
