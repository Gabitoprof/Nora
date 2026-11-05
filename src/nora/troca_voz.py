"""Trocar a voz falando: "usa a voz do Piper", "volta pro ElevenLabs", "qual voz você está
usando?". Vale nos modos com voz (nora ouvir, nora falar, nora conversar --voz)."""

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
# Pergunta ou comparação sobre as vozes: não é pedido de troca.
_PERGUNTA = (
    r"\b(melhor|pior|diferenca|compara|comparar|comparando|como|por que|porque|o que|quem|"
    r"quando|onde|qual|quais|acha|ou o|ou a)\b"
)
_DESTINO = r"\b(para|pra|pro|pela|pelo)\b"


@dataclass(frozen=True)
class PedidoDeVoz:
    acao: str  # "trocar" ou "qual"
    motor: str = ""  # "" com "trocar" = a voz da config


def _texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    limpo = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", " ", limpo).split())


def _motores(texto: str) -> list[str]:
    """Os motores citados no texto, na ordem em que aparecem (sem repetir)."""
    achados = sorted(
        (achado.start(), motor)
        for motor, nomes in _MOTORES
        for achado in re.finditer(rf"\b({nomes})\b", texto)
    )
    return list(dict.fromkeys(motor for _, motor in achados))


def pedido_de_voz(texto: str) -> PedidoDeVoz | None:
    """O pedido de troca de voz na fala, se ela for só isso (frase curta e intenção clara).
    Perguntar sobre um motor ("o Piper é melhor que o Kokoro?") não troca nada."""
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
    if len(motores) > 1:  # "troca do Kokoro para o Piper": vale o que vem depois do "para"
        destinos = list(re.finditer(_DESTINO, limpo))
        depois = _motores(limpo[destinos[-1].end() :]) if destinos else []
        return PedidoDeVoz("trocar", depois[0]) if len(depois) == 1 else None
    if motores:
        return PedidoDeVoz("trocar", motores[0])
    if re.search(_PADRAO, limpo):
        return PedidoDeVoz("trocar")
    return None


def atender_pedido(voz, pedido: PedidoDeVoz, padrao: str) -> tuple[str, bytes | None]:
    """Faz a troca e devolve (o que ela responde, o áudio já falado com a voz nova).
    Sem áudio, a resposta deve ser falada com a voz atual."""
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
