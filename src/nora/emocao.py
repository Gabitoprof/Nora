"""Emoção na voz: a Nora marca cada frase com uma etiqueta interna ({alegre}, {risada}...) e
cada motor de voz a traduz do seu jeito.

- ElevenLabs v3: vira audio tag ([happy], [laughs], [whispers]...), que muda o tom de verdade.
- ElevenLabs Flash/Turbo/Multilingual: vira ajuste de voz por pedido (estabilidade, estilo,
  velocidade), porque esses modelos não entendem as tags.
- Piper, Kokoro e ComfyUI: a etiqueta só é tirada.

A tela, o histórico e a memória nunca veem as etiquetas.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class Emocao:
    nome: str
    tag_v3: str  # audio tag do ElevenLabs v3
    estabilidade: float  # ElevenLabs: menor = mais expressiva
    estilo: float  # ElevenLabs: exagero do estilo da voz
    velocidade: float  # ElevenLabs: 0.7 a 1.2
    reacao: bool = False  # risada, suspiro: no máximo poucas por resposta


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

# {palavra} entre chaves; aceita espaços e acentos ({ séria }).
_ETIQUETA = re.compile(r"\{\s*([^{}\s]{2,20})\s*\}")


def _chave(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome.lower())
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _espacos(texto: str) -> str:
    texto = re.sub(r"[ \t]{2,}", " ", texto)
    return re.sub(r" +([,.!?…])", r"\1", texto).strip()


def emocoes_em(texto: str) -> list[Emocao]:
    """As emoções conhecidas marcadas no texto, em ordem."""
    return [EMOCOES[c] for c in map(_chave, _ETIQUETA.findall(texto)) if c in EMOCOES]


# Tons que valem como "tom da conversa" no Second Brain (reações e sussurro não contam).
TONS = {"alegre", "empolgada", "carinhosa", "calma", "seria", "triste", "curiosa"}


def tom_predominante(texto: str) -> str:
    """O tom que mais apareceu nas etiquetas da resposta ({alegre}, {calma}...), ou "" sem
    etiqueta de tom. Empate: o primeiro que apareceu."""
    contagem: dict[str, int] = {}
    for achado in _ETIQUETA.finditer(texto):
        chave = _chave(achado.group(1))
        if chave in TONS:
            contagem[chave] = contagem.get(chave, 0) + 1
    return max(contagem, key=contagem.get) if contagem else ""


def sem_emocoes(texto: str) -> str:
    """O texto sem as etiquetas (para a tela, a memória e vozes que não as entendem)."""
    return _espacos(_ETIQUETA.sub(" ", texto))


def para_v3(texto: str, intensidade: float = 0.5) -> str:
    """Troca as etiquetas pelas audio tags do ElevenLabs v3. Com intensidade baixa, ficam só
    as emoções (sem risadas e suspiros); com zero, nenhuma."""

    def trocar(achado: re.Match) -> str:
        emocao = EMOCOES.get(_chave(achado.group(1)))
        if emocao is None or intensidade <= 0 or (emocao.reacao and intensidade < 0.34):
            return " "
        return f" {emocao.tag_v3} "

    return _espacos(_ETIQUETA.sub(trocar, texto))


def ajustes_de_voz(texto: str, intensidade: float = 0.5) -> dict[str, float] | None:
    """Ajustes do ElevenLabs (Flash e outros sem tags) para a primeira emoção do texto, mais
    fortes ou mais fracos conforme a intensidade; None se não há emoção."""
    emocoes = emocoes_em(texto)
    if not emocoes or intensidade <= 0:
        return None
    emocao = emocoes[0]
    peso = min(1.0, intensidade * 2)  # 0.5 = o ajuste cheio; acima disso não exagera mais
    return {
        "stability": round(NEUTRA["estabilidade"] + (emocao.estabilidade - 0.5) * peso, 2),
        "style": round(emocao.estilo * peso, 2),
        "speed": round(1.0 + (emocao.velocidade - 1.0) * peso, 2),
    }


class FiltroDeTela:
    """Tira as etiquetas de um texto que chega aos pedaços (uma etiqueta pode vir partida em
    dois pedaços: "{ale" + "gre} Que bom!")."""

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
        # a etiqueta tirada não deixa espaço sobrando (no começo ou entre dois pedaços)
        if not self._comecou or self._ultimo in " \t\n":
            texto = texto.lstrip(" \t") if self._comecou else texto.lstrip()
        if texto:
            self._comecou, self._ultimo = True, texto[-1]
        return texto

    def finalizar(self) -> str:
        resto, self._pendente = self._pendente, ""
        return _ETIQUETA.sub("", resto)


def instrucoes(intensidade: float, reacoes: int) -> str:
    """O pedido à persona: como marcar as emoções."""
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
