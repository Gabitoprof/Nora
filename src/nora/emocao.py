"""Emotion in the voice: Nora marks each sentence with an internal tag ({alegre}, {risada}...) and
each voice engine translates it its own way.

- ElevenLabs v3: becomes an audio tag ([happy], [laughs], [whispers]...), which really changes
  the tone.
- ElevenLabs Flash/Turbo/Multilingual: becomes a per-request voice adjustment (stability, style,
  speed), because those models do not understand the tags.
- Piper, Kokoro and ComfyUI: the tag is just removed.

The screen, the history and the memory never see the tags.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Emocao:
    nome: str
    tag_v3: str  # ElevenLabs v3 audio tag
    estabilidade: float  # ElevenLabs: lower = more expressive
    estilo: float  # ElevenLabs: voice style exaggeration
    velocidade: float  # ElevenLabs: 0.7 a 1.2
    reacao: bool = False  # laugh, sigh: only a few per answer at most


EMOCOES = {
    e.nome: e
    for e in (
        Emocao("alegre", "[happy]", 0.40, 0.35, 1.03),
        Emocao("empolgada", "[excited]", 0.30, 0.50, 1.07),
        Emocao("carinhosa", "[warmly]", 0.50, 0.30, 0.97),
        Emocao("calma", "[calmly]", 0.65, 0.10, 0.95),
        Emocao("seria", "[serious]", 0.70, 0.05, 0.98),
        Emocao("triste", "[sad]", 0.55, 0.25, 0.92),
        Emocao("curiosa", "[curious]", 0.45, 0.30, 1.00),
        Emocao("sussurro", "[whispers]", 0.55, 0.20, 0.95),
        Emocao("risada", "[laughs]", 0.35, 0.45, 1.03, reacao=True),
        Emocao("suspiro", "[sighs]", 0.55, 0.20, 0.95, reacao=True),
    )
}
NOMES = ("alegre", "empolgada", "carinhosa", "calma", "séria", "triste", "curiosa", "sussurro",
         "risada", "suspiro")  # fmt: skip
NEUTRA = {"estabilidade": 0.5, "estilo": 0.0, "velocidade": 1.0}

# {word} in braces; accepts spaces and accents ({ séria }).
_ETIQUETA = re.compile(r"\{\s*([^{}\s]{2,20})\s*\}")


def _chave(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _espacos(texto: str) -> str:
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    return re.sub(r" +([,.!?…])", r"\1", texto).strip()


def emocoes_em(texto: str) -> list[Emocao]:
    """The known emotions tagged in the text, in order."""
    return [EMOCOES[c] for c in map(_chave, _ETIQUETA.findall(texto)) if c in EMOCOES]


# Tones that count as "conversation tone" in the Second Brain (reactions and whisper do not).
TONS = {"alegre", "empolgada", "carinhosa", "calma", "seria", "triste", "curiosa"}


def tom_predominante(texto: str) -> str:
    """The tone that appeared most in the answer's tags ({alegre}, {calma}...), or "" without a
    tone tag. Tie: the first one that appeared."""
    contagem: dict[str, int] = {}
    for achado in _ETIQUETA.finditer(texto):
        chave = _chave(achado.group(1))
        if chave in TONS:
            contagem[chave] = contagem.get(chave, 0) + 1
    return max(contagem, key=contagem.get) if contagem else ""


def sem_emocoes(texto: str) -> str:
    """The text without the tags (for the screen, the memory and voices that do not understand
    them)."""
    return _espacos(_ETIQUETA.sub(" ", texto))


def para_v3(texto: str, intensidade: float = 0.5) -> str:
    """Replaces the tags with ElevenLabs v3 audio tags. With low intensity, only the emotions stay
    (no laughs or sighs); with zero, none."""

    def trocar(achado: re.Match) -> str:
        emocao = EMOCOES.get(_chave(achado.group(1)))
        if emocao is None or intensidade <= 0 or (emocao.reacao and intensidade < 0.34):
            return " "
        return f" {emocao.tag_v3} "

    return _espacos(_ETIQUETA.sub(trocar, texto))


def ajustes_de_voz(texto: str, intensidade: float = 0.5) -> dict[str, float] | None:
    """ElevenLabs adjustments (Flash and others without tags) for the text's first emotion,
    stronger or weaker according to the intensity; None if there is no emotion."""
    emocoes = emocoes_em(texto)
    if not emocoes or intensidade <= 0:
        return None
    emocao = emocoes[0]
    peso = min(
        1.0, intensidade * 2
    )  # 0.5 = the full adjustment; above that it does not exaggerate further
    return {
        "stability": round(NEUTRA["estabilidade"] + (emocao.estabilidade - 0.5) * peso, 2),
        "style": round(emocao.estilo * peso, 2),
        "speed": round(1.0 + (emocao.velocidade - 1.0) * peso, 2),
    }


class FiltroDeTela:
    """Removes the tags from text arriving in chunks (a tag may come split across two chunks:
    "{ale" + "gre} Que bom!")."""

    def __init__(self) -> None:
        self._pendente = ""
        self._comecou = False
        self._ultimo = ""

    def alimentar(self, pedaco: str) -> str:
        texto = self._pendente + pedaco
        abre = texto.rfind("{")
        if abre != -1 and "}" not in texto[abre:] and len(texto) - abre <= 22:
            texto, self._pendente = texto[:abre], texto[abre:]
        else:
            self._pendente = ""
        texto = re.sub(r"[ \t]{2,}", " ", _ETIQUETA.sub("", texto))
        # the removed tag leaves no extra space (at the start or between two chunks)
        if not self._comecou or self._ultimo in " \t\n":
            texto = texto.lstrip(" \t") if self._comecou else texto.lstrip()
        if texto:
            self._comecou, self._ultimo = True, texto[-1]
        return texto

    def finalizar(self) -> str:
        resto, self._pendente = self._pendente, ""
        return _ETIQUETA.sub("", resto)


def instrucoes(intensidade: float, reacoes: int) -> str:
    """The instruction to the persona: how to tag the emotions."""
    if intensidade < 0.34:
        dose = "Use emoção com moderação: só quando ela for clara."
    elif intensidade < 0.67:
        dose = "Use emoção quando combinar com o momento."
    else:
        dose = "Seja expressiva: marque emoção sempre que fizer sentido."
    lista = ", ".join(f"{{{nome}}}" for nome in NOMES)
    return (
        "Sua voz tem emoção. Você pode começar uma frase com uma destas etiquetas, que só a "
        f"voz usa (nunca aparecem escritas para a pessoa): {lista}. Escolha pelo momento: o "
        "que a pessoa disse e como disse, o que você lembra dela, a agenda e a hora do dia. "
        f"{dose} No máximo {reacoes} {{risada}} ou {{suspiro}} por resposta. Nunca ria de "
        "assunto triste; em saúde, dinheiro ou más notícias, prefira {calma} ou {séria}. "
        "Frases neutras ficam sem etiqueta."
    )
