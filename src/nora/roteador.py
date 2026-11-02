"""Roteador de modelos (v0.3.0): decide quem responde cada pergunta.

- automático: o cérebro local (Ollama) conversa; quando acha a pergunta difícil demais, escreve
  {pensar} e a pergunta sobe para o Claude, com uma frase de espera na mesma voz;
- "pensa com calma", "pergunta difícil", "usa o Claude" na pergunta: direto para o Claude;
- comandos: "use o cérebro local", "use o Claude", "modo automático", "modo jogo" (tira o
  modelo local da placa de vídeo e responde tudo pela nuvem), "sair do modo jogo";
- reserva: sem Ollama, responde o Claude; sem Claude, responde o local; os dois avisam.

Para a conversa, o roteador é um cérebro como outro qualquer: responder(), medidas, aquecer().
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Iterator

from nora.cerebro import CerebroIndisponivel, CerebroLocal, Medidas
from nora.cerebro_nuvem import CerebroNuvem, nome_do_modelo
from nora.config import Config

ESCALAR = "{pensar}"
INSTRUCAO_ESCALAR = (
    "Se a pergunta pedir um raciocínio longo ou difícil (contas complexas, código, uma análise "
    "detalhada, um plano com muitas etapas, informação técnica precisa que você pode errar), "
    f"não responda: escreva apenas {ESCALAR} e nada mais. Uma assistente mais forte vai "
    "responder por você, com a mesma voz. Para conversa do dia a dia, responda normalmente."
)
FRASES_DE_ESPERA = (
    "Deixa eu pensar com calma.",
    "Boa pergunta, um instante.",
    "Vou caprichar nessa, só um momento.",
    "Hum, deixa eu ver isso direito.",
)

_PEDE_PESADO = re.compile(
    r"\b(pensa|pense|pensar) (com calma|bem|direito)\b|\bpergunta dificil\b|"
    r"\b(usa|use|usando|pergunta pro|pergunte ao|pede pro) (o )?claude\b"
)
_COMANDOS = (
    (
        "jogo_fim",
        r"\b(sai|sair|saia|desliga|desligar|fim do|acabou o) (do )?modo jogo\b"
        r"|\bacabou o jogo\b",
    ),
    ("jogo", r"\b(modo jogo|vou jogar|hora do jogo)\b"),
    (
        "automatico",
        r"\b(modo|cerebro) automatico\b|\bvolta (pro|ao|para o) (modo )?automatico\b",
    ),
    ("local", r"\b(cerebro|modelo) local\b|\bmodo local\b|\bso (o )?local\b"),
    (
        "nuvem",
        r"\b(use|usa|usar|troca|troque|mude|muda|passa|passe)\b.{0,20}\b(claude|nuvem)\b"
        r"|\bmodo nuvem\b|\bcerebro da nuvem\b",
    ),
)


# Triagem: sinais de pergunta pesada, vistos no texto antes de qualquer modelo. Não depende do
# cérebro local se julgar capaz (modelos pequenos costumam se achar capazes demais).
_SINAIS_DE_PESO = (
    (
        "código",
        r"\b(codigo|script|programa|programar|funcao|python|javascript|typescript|java|sql|"
        r"regex|html|css|api|bug|traceback|compilar|compila|debug|algoritmo)\b|```",
    ),
    (
        "conta",
        r"\d+(?:[.,]\d+)?\s*[-+*/^x×÷]\s*\d+|\b(calcule|calcula|calcular|resolva|resolve a|"
        r"integral|derivada|equacao|inequacao|matriz|logaritmo|juros|porcentagem de|"
        r"probabilidade|estatistica)\b",
    ),
    (
        "análise",
        r"\b(analise|analisa|analisar|compare|compara|comparar|comparacao|avalie|avalia|"
        r"pros e contras|vantagens e desvantagens|explique em detalhes|explica em detalhes|"
        r"detalhadamente|aprofunda|por que exatamente)\b",
    ),
    (
        "plano",
        r"\b(plano de|planejamento|cronograma|roteiro de|passo a passo|estrategia|"
        r"monte um|monta um|montar um|organize|organiza um)\b",
    ),
    (
        "texto",
        r"\b(escreva|escreve|redija|redacao|resuma|resume este|resume esse|revise|revisa|"
        r"traduza|traduz este|traduz esse|e-?mail formal|artigo|relatorio|curriculo)\b",
    ),
)
# Reação a uma resposta ruim do local: a pergunta ganha uma segunda chance com o Claude.
_INSATISFEITO = (
    r"\b(nao (e|foi) (isso|bem isso|o que (eu )?perguntei)|ta errado|esta errado|errou|"
    r"resposta errada|nao entendi|voce nao entendeu|explica melhor|explique melhor|"
    r"nao faz sentido|nada a ver|que isso)\b"
)


def peso_da_pergunta(texto: str) -> str:
    """Por que a pergunta parece pesada ("código", "conta"...), ou "" se parece conversa."""
    limpo = _texto(texto)
    if len(limpo.split()) > 60 or len(texto) > 400:
        return "texto longo"
    for motivo, padrao in _SINAIS_DE_PESO:
        if re.search(padrao, limpo):
            return motivo
    return ""


def insatisfeito(texto: str) -> bool:
    return bool(re.search(_INSATISFEITO, _texto(texto)))


def _texto(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto.lower())
    return " ".join("".join(c for c in sem_acento if not unicodedata.combining(c)).split())


def comando_em(texto: str) -> str | None:
    """O comando de troca de cérebro na fala, se ela for só um comando (frase curta)."""
    limpo = _texto(texto)
    if len(limpo.split()) > 10:  # frase longa é pergunta, não comando
        return None
    for nome, padrao in _COMANDOS:
        if re.search(padrao, limpo):
            return nome
    return None


def pede_pesado(texto: str) -> bool:
    return bool(_PEDE_PESADO.search(_texto(texto)))


class Roteador:
    def __init__(
        self,
        config: Config,
        local: CerebroLocal | None = None,
        rapido: CerebroNuvem | None = None,
        pesado: CerebroNuvem | None = None,
    ) -> None:
        nuvem = config.modelo_nuvem
        self.config = config
        self.local = local or CerebroLocal(config)
        self.rapido = rapido or CerebroNuvem(config, nuvem.rapido, nuvem.esforco_rapido)
        self.pesado = pesado or CerebroNuvem(config, nuvem.pesado, nuvem.esforco_pesado)
        self.modo = config.roteador.modo  # automatico | local | nuvem
        self.jogo = False
        self.ativo = self.local  # quem respondeu por último (para as medidas)
        self.origem = ""
        self.avisos: list[str] = []
        self._avisou_sem_nuvem = False

    # --- o que a conversa usa ---------------------------------------------------------------

    @property
    def medidas(self) -> Medidas:
        return self.ativo.medidas

    def aquecer(self) -> float:
        if self.modo == "nuvem" or self.jogo:
            return 0.0
        return self.local.aquecer()

    def nuvem_disponivel(self) -> bool:
        if self.rapido.cliente is not None or self.pesado.cliente is not None:
            return True  # (testes) cliente já pronto
        if not self.config.chave_anthropic:
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def responder(self, mensagens: list[dict[str, str]]) -> Iterator[str]:
        pergunta = next((m["content"] for m in reversed(mensagens) if m["role"] == "user"), "")
        comando = comando_em(pergunta)
        if comando:
            yield self._trocar(comando)
            return
        anterior_local = self.origem.startswith("local")
        if self.jogo or self.modo == "nuvem":
            pesada = pede_pesado(pergunta) or bool(self._triagem(pergunta))
            yield from self._nuvem(mensagens, self.pesado if pesada else self.rapido, pesada)
            return
        if self.modo == "local":
            yield from self._local(mensagens, escalar=False)
            return
        motivo = (
            "pedido"
            if pede_pesado(pergunta)
            else self._triagem(pergunta)
            or ("segunda chance" if anterior_local and insatisfeito(pergunta) else "")
        )
        if motivo and self.nuvem_disponivel():
            yield from self._nuvem(mensagens, self.pesado, espera=True)
            return
        if motivo:
            self._avisar_sem_nuvem()
        escalar = self.config.roteador.escalar and self.nuvem_disponivel()
        yield from self._local(mensagens, escalar=escalar)

    def _triagem(self, pergunta: str) -> str:
        return peso_da_pergunta(pergunta) if self.config.roteador.triagem else ""

    def _avisar_sem_nuvem(self) -> None:
        """Uma vez por conversa: a pergunta era para o Claude, mas ele não está disponível."""
        if self._avisou_sem_nuvem:
            return
        self._avisou_sem_nuvem = True
        if not self.config.chave_anthropic:
            falta = "falta a ANTHROPIC_API_KEY no .env"
        else:
            falta = 'falta o pacote do Claude (pip install -e ".[nuvem]")'
        self.avisos.append(
            f"Essa pergunta era para o Claude, mas ele não está disponível ({falta}). "
            "Respondi pelo cérebro local."
        )

    # --- caminhos ---------------------------------------------------------------------------

    def _usar(self, cerebro, origem: str) -> None:
        self.ativo, self.origem = cerebro, origem

    def _local(self, mensagens, escalar: bool) -> Iterator[str]:
        self._usar(self.local, f"local ({self.config.modelo_local.modelo})")
        envio = (
            mensagens + [{"role": "system", "content": INSTRUCAO_ESCALAR}] if escalar else mensagens
        )
        try:
            fluxo = self.local.responder(envio)
            if not escalar:
                yield from fluxo
                return
            inicio = ""
            for pedaco in fluxo:
                inicio += pedaco
                if ESCALAR in inicio:
                    fluxo.close()  # a pergunta sobe para o Claude
                    yield from self._nuvem(mensagens, self.pesado, espera=True)
                    return
                comeco = inicio.lstrip()
                if len(comeco) >= len(ESCALAR) or not ESCALAR.startswith(comeco):
                    yield inicio
                    yield from fluxo
                    return
            if inicio:
                yield inicio
        except CerebroIndisponivel as erro:
            if not self.nuvem_disponivel():
                raise
            self.avisos.append(f"O cérebro local não respondeu ({erro}); respondi pelo Claude.")
            yield from self._nuvem(mensagens, self.rapido, espera=False, reserva=False)

    def _nuvem(self, mensagens, cerebro: CerebroNuvem, espera: bool, reserva: bool = True):
        if espera:
            yield random.choice(FRASES_DE_ESPERA) + " "
        self._usar(cerebro, nome_do_modelo(cerebro.modelo))
        try:
            yield from cerebro.responder(mensagens)
        except CerebroIndisponivel as erro:
            if not reserva:
                raise
            self.avisos.append(f"{erro} Respondi pelo cérebro local.")
            yield from self._local(mensagens, escalar=False)

    # --- comandos ---------------------------------------------------------------------------

    def _trocar(self, comando: str) -> str:
        self._usar(self.local, "comando")
        sem_nuvem = (
            " Mas ainda não tenho acesso ao Claude: falta a chave ANTHROPIC_API_KEY no .env."
        )
        if comando == "jogo":
            self.jogo = True
            try:
                self.local.descarregar()
            except CerebroIndisponivel:
                pass  # o Ollama já estava fora: a placa de vídeo já está livre
            resposta = "Modo jogo ligado: liberei a placa de vídeo e respondo pela nuvem."
            return resposta + ("" if self.nuvem_disponivel() else sem_nuvem)
        if comando == "jogo_fim":
            self.jogo = False
            return "Modo jogo desligado. Voltei a pensar por aqui."
        if comando == "nuvem":
            self.modo = "nuvem"
            resposta = "Pronto, agora respondo tudo pelo Claude."
            return resposta + ("" if self.nuvem_disponivel() else sem_nuvem)
        if comando == "local":
            self.modo = "local"
            return "Pronto, agora respondo só com o cérebro local."
        self.modo = "automatico"
        return "Pronto, modo automático: converso por aqui e chamo o Claude nas perguntas difíceis."

    def avisos_pendentes(self) -> list[str]:
        avisos, self.avisos = self.avisos, []
        return avisos
