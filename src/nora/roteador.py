"""Model router (v0.3.0): decides who answers each question.

- automatic: the local brain (Ollama) handles conversation; the hard questions (triage, the
  local model's {pensar}, a complaint) go to the cloud, with a holding phrase in the same voice;
- cloud: the hard ones go first to ChatGPT (`[roteador] complexas`); if it fails, refuses or does
  not answer, to Claude; if both fail, the local model answers;
- "pensa com calma", "pergunta difícil", "pergunta pro ChatGPT", "usa o Claude" in the question:
  straight to the cloud (and to whoever was called);
- commands: "use o cérebro local", "use o ChatGPT", "use o Claude", "modo automático",
  "modo jogo" (unloads the local model from the graphics card and answers everything through
  the cloud), "sair do modo jogo";
- fallback: without Ollama, the cloud answers; without the cloud, the local model answers; all
  of them warn.

To the conversation, the router is a brain like any other: responder(), medidas, aquecer().
"""

from __future__ import annotations

import random
import re
import time
import unicodedata
from collections.abc import Iterator

from nora import cerebro_nuvem, cerebro_openai
from nora.cerebro import CerebroIndisponivel, CerebroLocal, Medidas, categoria_do_erro
from nora.cerebro_nuvem import CerebroNuvem
from nora.cerebro_openai import CerebroOpenAI
from nora.config import Config
from nora.confirmacao import confirmacao

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
FRASE_JOGO_SEM_NUVEM = (
    "Agora não consegui falar com a nuvem, e no modo jogo eu não uso o cérebro daqui para não "
    'pesar na placa de vídeo. Se quiser que eu responda mesmo assim, diga "sair do modo jogo".'
)
NOMES = {"openai": "ChatGPT", "anthropic": "Claude"}
CHAVES = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}

_NUVENS = r"(claude|chat ?gpt|gpt|openai)"
_PEDE_NUVEM = re.compile(
    r"\b(usa|use|usando|utilize|utiliza|utilizar|chama|chame|consulta|consulte|pergunta pro|"
    r"pergunta pra|pergunta para o|pergunte ao|pergunte pro|pede pro|pede para o|pede ao) "
    rf"(o )?{_NUVENS}\b"
)
_PEDE_PESADO = re.compile(r"\b(pensa|pense|pensar) (com calma|bem|direito)\b|\bpergunta dificil\b")
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
        r"\b(use|usa|usar|utilize|utiliza|troca|troque|mude|muda|passa|passe)\b.{0,20}"
        rf"\b({_NUVENS[1:-1]}|nuvem)\b"
        r"|\bmodo nuvem\b|\bcerebro da nuvem\b",
    ),
)

# Triage: signs of a heavy question, seen in the text before any model. It does not depend on
# the local brain judging itself capable (small models tend to think themselves too capable).
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
# Reaction to a bad local answer: the question gets a second chance in the cloud.
_INSATISFEITO = (
    r"\b(nao (e|foi) (isso|bem isso|o que (eu )?perguntei)|ta errado|esta errado|errou|"
    r"resposta errada|nao entendi|voce nao entendeu|explica melhor|explique melhor|"
    r"nao faz sentido|nada a ver|que isso)\b"
)


def peso_da_pergunta(texto: str) -> str:
    """Why the question looks heavy ("código", "conta"...), or "" if it looks like conversation."""
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


# Words that may be left over in a pure command ("Nora, usa o Claude agora, por favor").
_SOBRAS_DE_COMANDO = set(
    (
        "nora agora por favor pf pfv entao ai ok beleza bem a o e de da do partir daqui pra "
        "frente em diante sempre so somente apenas pode voce vc tudo nessa nisso mesmo isso ta "
        "certo vamos vai la modo quero que com no na pro pelo pela para usa use usar utilize "
        "utiliza troca troque mude muda passa passe volta volte liga ligue ativa ative entra "
        "entre fica fique responda responde responder seu"
    ).split()
)


# Before the command, one of these makes the sentence a question about it ("como sair do modo
# jogo?").
_PERGUNTA_SOBRE = (
    r"\b(como|o que|por que|porque|quando|qual|quais|onde|quanto|explica|explique|significa|"
    r"funciona|serve)\b"
)


def achar_comando(texto: str) -> tuple[str | None, bool]:
    """(command, whether it is pure). Pure is just the command ("use o Claude"); with content, the
    sentence also asks for something ("use o Claude para explicar fotossíntese") and that
    thing must be done."""
    limpo = _texto(texto)
    if len(limpo.split()) > 10:  # a long sentence is a question, not a command
        return None, False
    for nome, padrao in _COMANDOS:
        achado = re.search(padrao, limpo)
        if achado and re.search(_PERGUNTA_SOBRE, limpo[: achado.start()]):
            return None, False  # "como sair do modo jogo?": a question about the command
        if achado:
            resto = re.sub(r"[^\w\s]", " ", limpo[: achado.start()] + " " + limpo[achado.end() :])
            resto = resto.split()
            return nome, all(palavra in _SOBRAS_DE_COMANDO for palavra in resto)
    return None, False


def comando_em(texto: str) -> str | None:
    """The brain switch command in the speech, if it is only a command."""
    nome, puro = achar_comando(texto)
    return nome if puro else None


def pede_pesado(texto: str) -> bool:
    limpo = _texto(texto)
    return bool(_PEDE_PESADO.search(limpo) or _PEDE_NUVEM.search(limpo))


def provedor_em(texto: str) -> str:
    """Which cloud the text mentions: "anthropic" (Claude), "openai" (ChatGPT) or ""."""
    achou = re.search(_NUVENS, _texto(texto))
    if not achou:
        return ""
    return "anthropic" if achou.group(1) == "claude" else "openai"


def quem_foi_chamado(texto: str) -> str:
    """The cloud requested in the question ("pergunta pro ChatGPT ..."), or "" if none was
    requested."""
    achou = _PEDE_NUVEM.search(_texto(texto))
    return provedor_em(achou.group(0)) if achou else ""


class Roteador:
    def __init__(
        self,
        config: Config,
        local: CerebroLocal | None = None,
        rapido: CerebroNuvem | None = None,
        pesado: CerebroNuvem | None = None,
        rapido_openai: CerebroOpenAI | None = None,
        pesado_openai: CerebroOpenAI | None = None,
    ) -> None:
        claude, gpt = config.modelo_nuvem, config.modelo_openai
        self.config = config
        self.local = local or CerebroLocal(config)
        self.rapido = rapido or CerebroNuvem(config, claude.rapido, claude.esforco_rapido)
        self.pesado = pesado or CerebroNuvem(config, claude.pesado, claude.esforco_pesado)
        self.rapido_openai = rapido_openai or CerebroOpenAI(config, gpt.rapido, gpt.esforco_rapido)
        self.pesado_openai = pesado_openai or CerebroOpenAI(config, gpt.pesado, gpt.esforco_pesado)
        self.modo = config.roteador.modo  # automatico | local | nuvem
        self.provedor = config.roteador.complexas  # the cloud tried first
        self.jogo = False
        self.ativo = self.local  # who answered last (for the measurements)
        self.origem = ""
        self.avisos: list[str] = []
        # How the last answer ended: "completa", "interrompida" (stopped midway) or
        # "sem resposta" (nobody could answer). The conversation only learns from complete ones.
        self.situacao = "completa"
        self._avisou_sem_nuvem = False
        self._aguardando: str | None = None  # command waiting for a "sim" (leaving game mode)
        # Each brain tried in the last answer, for diagnostics (self-improvement):
        # {"motor", "resultado" (resposta, escalou or the failure category), "duracao_ms"}.
        self.tentativas: list[dict] = []
        self._avisou_sem: set[str] = set()

    # --- what the conversation uses ---------------------------------------------------------

    @property
    def medidas(self) -> Medidas:
        return self.ativo.medidas

    def aquecer(self) -> float:
        if self.modo == "nuvem" or self.jogo:
            return 0.0
        return self.local.aquecer()

    def _cerebros(self, provedor: str):
        if provedor == "openai":
            return self.rapido_openai, self.pesado_openai
        return self.rapido, self.pesado

    def disponivel(self, provedor: str) -> bool:
        rapido, pesado = self._cerebros(provedor)
        if rapido.cliente is not None or pesado.cliente is not None:
            return True  # (tests) ready-made client
        return not self._falta(provedor)

    def nuvem_disponivel(self) -> bool:
        return self.disponivel("openai") or self.disponivel("anthropic")

    def _falta(self, provedor: str) -> str:
        """What is missing to use that cloud ("" if nothing)."""
        chave = self.config.chave_openai if provedor == "openai" else self.config.chave_anthropic
        if not chave:
            return f"falta a {CHAVES[provedor]} no .env"
        modulo = cerebro_openai if provedor == "openai" else cerebro_nuvem
        return modulo.problema_do_pacote()

    def responder(self, mensagens: list[dict[str, str]]) -> Iterator[str]:
        pergunta = next((m["content"] for m in reversed(mensagens) if m["role"] == "user"), "")
        self.situacao = "completa"
        self.tentativas = []
        aguardando, self._aguardando = self._aguardando, None
        if aguardando:  # resolved by rule: no model, without touching the graphics card
            resposta = confirmacao(pergunta)
            if resposta == "sim":
                self.situacao = "comando"
                yield self._trocar(aguardando, pergunta)
                return
            if resposta == "nao":
                self.situacao = "comando"
                self._usar(self.local, "comando")
                yield "Tudo bem, continuo no modo jogo."
                return
        comando, puro = achar_comando(pergunta)
        if comando == "jogo_fim":
            self.situacao = "comando"
            self._usar(self.local, "comando")
            if not self.jogo:
                yield "Não estou no modo jogo."
                return
            self._aguardando = "jogo_fim"
            yield (
                "Quer sair do modo jogo? Eu volto a pensar aqui no PC, usando a placa de vídeo. "
                'Confirma? Diga "sim".'
            )
            return
        if comando and puro:
            self.situacao = "comando"  # state change: not a fact for memory
            yield self._trocar(comando, pergunta)
            return
        if (
            comando == "local"
        ):  # "use o cérebro local para ...": only this question, on the local model
            yield from self._local(mensagens, escalar=False)
            return
        if (
            comando == "nuvem"
        ):  # "use o Claude para ...": only this question, on the requested cloud
            chamado = provedor_em(pergunta)
            yield from self._nuvem(mensagens, pesada=True, espera=True, chamado=chamado)
            return
        if comando:  # "modo jogo, e ...": switches and answers the rest
            yield self._trocar(comando, pergunta) + " "
        chamado = quem_foi_chamado(pergunta)
        anterior_local = self.origem.startswith("local")
        if self.jogo or self.modo == "nuvem":
            pesada = pede_pesado(pergunta) or bool(self._triagem(pergunta))
            yield from self._nuvem(mensagens, pesada, espera=pesada, chamado=chamado)
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
            yield from self._nuvem(mensagens, pesada=True, espera=True, chamado=chamado)
            return
        if motivo:
            self._avisar_sem_nuvem()
        escalar = self.config.roteador.escalar and self.nuvem_disponivel()
        yield from self._local(mensagens, escalar=escalar)

    def _triagem(self, pergunta: str) -> str:
        return peso_da_pergunta(pergunta) if self.config.roteador.triagem else ""

    def _avisar_sem_nuvem(self) -> None:
        """Once per conversation: the question was meant for the cloud, but none is available."""
        if self._avisou_sem_nuvem:
            return
        self._avisou_sem_nuvem = True
        faltas = "; ".join(f"{NOMES[p]}: {self._falta(p)}" for p in ("openai", "anthropic"))
        self.avisos.append(
            f"Essa pergunta era para a nuvem, mas ela não está disponível ({faltas}). "
            "Respondi pelo cérebro local."
        )

    # --- paths ------------------------------------------------------------------------------

    def _usar(self, cerebro, origem: str) -> None:
        self.ativo, self.origem = cerebro, origem

    def _anotar(self, resultado: str, inicio: float, primeiro: float | None) -> None:
        """Records how the attempt with the brain in use went (time to the first chunk)."""
        fim = primeiro if primeiro is not None else time.perf_counter()
        self.tentativas.append(
            {"motor": self.origem, "resultado": resultado, "duracao_ms": int((fim - inicio) * 1000)}
        )

    def _local(self, mensagens, escalar: bool) -> Iterator[str]:
        self._usar(self.local, f"local ({self.config.modelo_local.modelo})")
        envio = (
            mensagens + [{"role": "system", "content": INSTRUCAO_ESCALAR}] if escalar else mensagens
        )
        escreveu = (
            False  # after saying something, switching brains would stitch two answers together
        )
        subir = False
        comeco_tentativa, primeiro = time.perf_counter(), None
        try:
            fluxo = self.local.responder(envio)
            inicio = ""
            for pedaco in fluxo:
                if primeiro is None and pedaco:
                    primeiro = time.perf_counter()
                if not escalar or escreveu:
                    escreveu = escreveu or bool(pedaco)
                    yield pedaco
                    continue
                inicio += pedaco
                if ESCALAR in inicio:
                    fluxo.close()  # the question goes up to the cloud
                    subir = True
                    break
                comeco = inicio.lstrip()
                if len(comeco) >= len(ESCALAR) or not ESCALAR.startswith(comeco):
                    escreveu = True
                    yield inicio
            else:
                if inicio and not escreveu:
                    escreveu = True
                    yield inicio
        except CerebroIndisponivel as erro:
            self._anotar(
                "stream_interrompido" if escreveu else categoria_do_erro(erro),
                comeco_tentativa,
                primeiro,
            )
            if escreveu:
                self.situacao = "interrompida"
                self.avisos.append(
                    f"O cérebro local parou no meio ({erro}). A resposta ficou pela metade; "
                    "pergunte de novo se quiser a resposta inteira."
                )
                return
            if not self.nuvem_disponivel():
                raise
            self.avisos.append(f"O cérebro local não respondeu ({erro}); respondi pela nuvem.")
            yield from self._nuvem(mensagens, pesada=False, espera=False, reserva=False)
            return
        self._anotar("escalou" if subir else "resposta", comeco_tentativa, primeiro)
        if subir:
            yield from self._nuvem(mensagens, pesada=True, espera=True)

    def _ordem(self, chamado: str) -> list[str]:
        """The clouds to try, in order: the one called (or the preferred one), then the other."""
        primeira = chamado or self.provedor
        ordem = [primeira, "anthropic" if primeira == "openai" else "openai"]
        if chamado and not self.disponivel(chamado) and chamado not in self._avisou_sem:
            self._avisou_sem.add(
                chamado
            )  # that cloud was asked for by name: say why it was not used
            self.avisos.append(f"O {NOMES[chamado]} não está disponível ({self._falta(chamado)}).")
        return [p for p in ordem if self.disponivel(p)]

    def _nuvem(self, mensagens, pesada: bool, espera: bool, chamado: str = "", reserva=True):
        """Tries the clouds in order; with no answer, the local model (if `reserva`)."""
        if espera:
            yield random.choice(FRASES_DE_ESPERA) + " "
        ordem = self._ordem(chamado)
        erro: CerebroIndisponivel | None = None
        for posicao, provedor in enumerate(ordem):
            rapido, pesado = self._cerebros(provedor)
            cerebro = pesado if pesada else rapido
            self._usar(cerebro, cerebro.nome)
            escreveu = False
            comeco_tentativa, primeiro = time.perf_counter(), None
            try:
                for pedaco in cerebro.responder(mensagens):
                    if primeiro is None:
                        primeiro = time.perf_counter()
                    escreveu = True
                    yield pedaco
                self._anotar("resposta", comeco_tentativa, primeiro)
                return
            except CerebroIndisponivel as falha:
                erro = falha
                self._anotar(
                    "stream_interrompido" if escreveu else categoria_do_erro(falha),
                    comeco_tentativa,
                    primeiro,
                )
                if (
                    escreveu
                ):  # half was already spoken: switching brains now would repeat the beginning
                    self.situacao = "interrompida"
                    self.avisos.append(f"{falha} A resposta ficou pela metade.")
                    return
                if posicao + 1 < len(ordem):
                    self.avisos.append(f"{falha} Pedi ao {NOMES[ordem[posicao + 1]]}.")
        if not reserva:
            raise erro or CerebroIndisponivel("Nenhuma nuvem disponível.")
        if self.jogo:  # the local model would take up again the graphics card game mode freed
            self.situacao = "sem resposta"
            motivo = str(erro) if erro else self._sem_acesso(self.provedor).strip()
            self.avisos.append(
                f"No modo jogo não uso o cérebro local, para não ocupar a placa de vídeo. {motivo}"
            )
            self._usar(self.local, "modo jogo")
            yield FRASE_JOGO_SEM_NUVEM
            return
        if erro:
            self.avisos.append(f"{erro} Respondi pelo cérebro local.")
        elif not ordem:
            self._avisar_sem_nuvem()
        yield from self._local(mensagens, escalar=False)

    # --- commands ---------------------------------------------------------------------------

    def _trocar(self, comando: str, pergunta: str = "") -> str:
        self._usar(self.local, "comando")
        if comando == "jogo":
            self.jogo = True
            try:
                self.local.descarregar()
            except CerebroIndisponivel:
                pass  # Ollama was already down: the graphics card is already free
            resposta = "Modo jogo ligado: liberei a placa de vídeo e respondo pela nuvem."
            if not self.nuvem_disponivel():
                resposta += self._sem_acesso(self.provedor)
            return resposta
        if comando == "jogo_fim":
            self.jogo = False
            return "Modo jogo desligado. Voltei a pensar por aqui."
        if comando == "nuvem":
            self.modo = "nuvem"
            self.provedor = provedor_em(pergunta) or self.provedor
            nome = NOMES[self.provedor]
            resposta = f"Pronto, agora respondo tudo pelo {nome}."
            return resposta + ("" if self.disponivel(self.provedor) else self._sem_acesso())
        if comando == "local":
            self.modo = "local"
            return "Pronto, agora respondo só com o cérebro local."
        self.modo = "automatico"
        self.provedor = self.config.roteador.complexas
        return (
            "Pronto, modo automático: converso por aqui e chamo o "
            f"{NOMES[self.provedor]} nas perguntas difíceis."
        )

    def _sem_acesso(self, provedor: str = "") -> str:
        provedor = provedor or self.provedor
        return f" Mas ainda não tenho acesso ao {NOMES[provedor]}: {self._falta(provedor)}."

    def avisos_pendentes(self) -> list[str]:
        avisos, self.avisos = self.avisos, []
        return avisos
