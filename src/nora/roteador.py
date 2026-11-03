"""Roteador de modelos (v0.3.0): decide quem responde cada pergunta.

- automático: o cérebro local (Ollama) conversa; as perguntas difíceis (triagem, {pensar} do
  local, reclamação) vão para a nuvem, com uma frase de espera na mesma voz;
- nuvem: as difíceis vão primeiro para o ChatGPT (`[roteador] complexas`); se ele falhar, recusar
  ou não responder, para o Claude; se os dois falharem, o local responde;
- "pensa com calma", "pergunta difícil", "pergunta pro ChatGPT", "usa o Claude" na pergunta:
  direto para a nuvem (e para quem foi chamado);
- comandos: "use o cérebro local", "use o ChatGPT", "use o Claude", "modo automático",
  "modo jogo" (tira o modelo local da placa de vídeo e responde tudo pela nuvem),
  "sair do modo jogo";
- reserva: sem Ollama, responde a nuvem; sem nuvem, responde o local; todos avisam.

Para a conversa, o roteador é um cérebro como outro qualquer: responder(), medidas, aquecer().
"""

from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Iterator

from nora import cerebro_nuvem, cerebro_openai
from nora.cerebro import CerebroIndisponivel, CerebroLocal, Medidas
from nora.cerebro_nuvem import CerebroNuvem
from nora.cerebro_openai import CerebroOpenAI
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
# Reação a uma resposta ruim do local: a pergunta ganha uma segunda chance na nuvem.
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


# Palavras que podem sobrar num comando puro ("Nora, usa o Claude agora, por favor").
_SOBRAS_DE_COMANDO = set(
    (
        "nora agora por favor pf pfv entao ai ok beleza bem a o e de da do partir daqui pra "
        "frente em diante sempre so somente apenas pode voce vc tudo nessa nisso mesmo isso ta "
        "certo vamos vai la modo quero que com no na pro pelo pela para usa use usar utilize "
        "utiliza troca troque mude muda passa passe volta volte liga ligue ativa ative entra "
        "entre fica fique responda responde responder seu"
    ).split()
)


def achar_comando(texto: str) -> tuple[str | None, bool]:
    """(comando, se é puro). Puro é só o comando ("use o Claude"); com conteúdo, a frase também
    pede alguma coisa ("use o Claude para explicar fotossíntese") e essa coisa deve ser feita."""
    limpo = _texto(texto)
    if len(limpo.split()) > 10:  # frase longa é pergunta, não comando
        return None, False
    for nome, padrao in _COMANDOS:
        achado = re.search(padrao, limpo)
        if achado:
            resto = re.sub(r"[^\w\s]", " ", limpo[: achado.start()] + " " + limpo[achado.end() :])
            resto = resto.split()
            return nome, all(palavra in _SOBRAS_DE_COMANDO for palavra in resto)
    return None, False


def comando_em(texto: str) -> str | None:
    """O comando de troca de cérebro na fala, se ela for só um comando."""
    nome, puro = achar_comando(texto)
    return nome if puro else None


def pede_pesado(texto: str) -> bool:
    limpo = _texto(texto)
    return bool(_PEDE_PESADO.search(limpo) or _PEDE_NUVEM.search(limpo))


def provedor_em(texto: str) -> str:
    """Qual nuvem o texto cita: "anthropic" (Claude), "openai" (ChatGPT) ou ""."""
    achou = re.search(_NUVENS, _texto(texto))
    if not achou:
        return ""
    return "anthropic" if achou.group(1) == "claude" else "openai"


def quem_foi_chamado(texto: str) -> str:
    """A nuvem pedida na pergunta ("pergunta pro ChatGPT ..."), ou "" se não pediu nenhuma."""
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
        self.provedor = config.roteador.complexas  # a nuvem que tenta primeiro
        self.jogo = False
        self.ativo = self.local  # quem respondeu por último (para as medidas)
        self.origem = ""
        self.avisos: list[str] = []
        # Como terminou a última resposta: "completa", "interrompida" (parou no meio) ou
        # "sem resposta" (ninguém pôde responder). A conversa só aprende com as completas.
        self.situacao = "completa"
        self._avisou_sem_nuvem = False
        self._avisou_sem: set[str] = set()

    # --- o que a conversa usa ---------------------------------------------------------------

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
            return True  # (testes) cliente já pronto
        return not self._falta(provedor)

    def nuvem_disponivel(self) -> bool:
        return self.disponivel("openai") or self.disponivel("anthropic")

    def _falta(self, provedor: str) -> str:
        """O que falta para usar essa nuvem ("" se nada)."""
        chave = self.config.chave_openai if provedor == "openai" else self.config.chave_anthropic
        if not chave:
            return f"falta a {CHAVES[provedor]} no .env"
        modulo = cerebro_openai if provedor == "openai" else cerebro_nuvem
        return modulo.problema_do_pacote()

    def responder(self, mensagens: list[dict[str, str]]) -> Iterator[str]:
        pergunta = next((m["content"] for m in reversed(mensagens) if m["role"] == "user"), "")
        self.situacao = "completa"
        comando, puro = achar_comando(pergunta)
        if comando and puro:
            yield self._trocar(comando, pergunta)
            return
        if comando == "local":  # "use o cérebro local para ...": só esta pergunta, no local
            yield from self._local(mensagens, escalar=False)
            return
        if comando == "nuvem":  # "use o Claude para ...": só esta pergunta, na nuvem pedida
            chamado = provedor_em(pergunta)
            yield from self._nuvem(mensagens, pesada=True, espera=True, chamado=chamado)
            return
        if comando:  # "modo jogo, e ...": troca e responde o resto
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
        """Uma vez por conversa: a pergunta era para a nuvem, mas nenhuma está disponível."""
        if self._avisou_sem_nuvem:
            return
        self._avisou_sem_nuvem = True
        faltas = "; ".join(f"{NOMES[p]}: {self._falta(p)}" for p in ("openai", "anthropic"))
        self.avisos.append(
            f"Essa pergunta era para a nuvem, mas ela não está disponível ({faltas}). "
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
        escreveu = False  # depois de falar algo, trocar de cérebro emendaria duas respostas
        subir = False
        try:
            fluxo = self.local.responder(envio)
            inicio = ""
            for pedaco in fluxo:
                if not escalar or escreveu:
                    escreveu = escreveu or bool(pedaco)
                    yield pedaco
                    continue
                inicio += pedaco
                if ESCALAR in inicio:
                    fluxo.close()  # a pergunta sobe para a nuvem
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
        if subir:
            yield from self._nuvem(mensagens, pesada=True, espera=True)

    def _ordem(self, chamado: str) -> list[str]:
        """As nuvens a tentar, na ordem: a chamada (ou a preferida), depois a outra."""
        primeira = chamado or self.provedor
        ordem = [primeira, "anthropic" if primeira == "openai" else "openai"]
        if chamado and not self.disponivel(chamado) and chamado not in self._avisou_sem:
            self._avisou_sem.add(chamado)  # pediu essa nuvem pelo nome: diz por que não foi ela
            self.avisos.append(f"O {NOMES[chamado]} não está disponível ({self._falta(chamado)}).")
        return [p for p in ordem if self.disponivel(p)]

    def _nuvem(self, mensagens, pesada: bool, espera: bool, chamado: str = "", reserva=True):
        """Tenta as nuvens na ordem; sem nenhuma resposta, o local (se `reserva`)."""
        if espera:
            yield random.choice(FRASES_DE_ESPERA) + " "
        ordem = self._ordem(chamado)
        erro: CerebroIndisponivel | None = None
        for posicao, provedor in enumerate(ordem):
            rapido, pesado = self._cerebros(provedor)
            cerebro = pesado if pesada else rapido
            self._usar(cerebro, cerebro.nome)
            escreveu = False
            try:
                for pedaco in cerebro.responder(mensagens):
                    escreveu = True
                    yield pedaco
                return
            except CerebroIndisponivel as falha:
                erro = falha
                if escreveu:  # já falou metade: trocar de cérebro agora repetiria o começo
                    self.situacao = "interrompida"
                    self.avisos.append(f"{falha} A resposta ficou pela metade.")
                    return
                if posicao + 1 < len(ordem):
                    self.avisos.append(f"{falha} Pedi ao {NOMES[ordem[posicao + 1]]}.")
        if not reserva:
            raise erro or CerebroIndisponivel("Nenhuma nuvem disponível.")
        if self.jogo:  # o local ocuparia de novo a placa de vídeo que o modo jogo liberou
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

    # --- comandos ---------------------------------------------------------------------------

    def _trocar(self, comando: str, pergunta: str = "") -> str:
        self._usar(self.local, "comando")
        if comando == "jogo":
            self.jogo = True
            try:
                self.local.descarregar()
            except CerebroIndisponivel:
                pass  # o Ollama já estava fora: a placa de vídeo já está livre
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
