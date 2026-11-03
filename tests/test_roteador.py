"""Roteador de modelos: local conversa, a nuvem (ChatGPT, depois Claude) pega as difíceis."""

import re
from types import SimpleNamespace

import pytest

from nora.cerebro import CerebroIndisponivel, Medidas
from nora.cerebro_nuvem import RECUSA, CerebroNuvem, nome_do_modelo, separar_sistema
from nora.cerebro_openai import CerebroOpenAI
from nora.config import carregar
from nora.conversa import nova_conversa
from nora.roteador import (
    ESCALAR,
    FRASES_DE_ESPERA,
    Roteador,
    comando_em,
    insatisfeito,
    pede_pesado,
    peso_da_pergunta,
    quem_foi_chamado,
)


class FluxoFalso:
    def __init__(self, pedacos, parada="end_turn"):
        self.pedacos, self.parada = pedacos, parada

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    @property
    def text_stream(self):
        yield from self.pedacos

    def get_final_message(self):
        return SimpleNamespace(stop_reason=self.parada, usage=SimpleNamespace(output_tokens=5))


class ClienteFalso:
    """Imita o SDK anthropic: messages.stream e beta.messages.stream."""

    def __init__(self, resposta="Resposta do Claude.", parada="end_turn", erro=None):
        self.pedidos = []
        cliente = self

        class Mensagens:
            def __init__(self, beta):
                self.beta = beta

            def stream(self, **pedido):
                cliente.pedidos.append({"beta": self.beta, **pedido})
                if erro:
                    raise erro
                return FluxoFalso(re.findall(r"\S+\s*", resposta), parada)

        self.messages = Mensagens(beta=False)
        self.beta = SimpleNamespace(messages=Mensagens(beta=True))


class LocalFalso:
    def __init__(self, resposta="Resposta local.", falhar=False, cair_depois=0):
        self.resposta, self.falhar, self.cair_depois = resposta, falhar, cair_depois
        self.pedidos, self.descarregou = [], False
        self.medidas = Medidas()
        self.fechado = False

    def aquecer(self):
        return 0.5

    def descarregar(self):
        self.descarregou = True

    def responder(self, mensagens):
        self.pedidos.append(mensagens)
        if self.falhar:
            raise CerebroIndisponivel("Ollama fora do ar")
        try:
            for numero, i in enumerate(range(0, len(self.resposta), 3)):
                if self.cair_depois and numero == self.cair_depois:
                    raise CerebroIndisponivel("Ollama caiu no meio")
                yield self.resposta[i : i + 3]
        except GeneratorExit:
            self.fechado = True
            raise


class OpenAIFalso:
    """Imita o SDK openai: responses.create(stream=True) devolve eventos."""

    def __init__(self, resposta="Resposta do ChatGPT.", erro=None, recusa=False, quebra=False):
        self.pedidos = []
        cliente = self

        def evento(tipo, **dados):
            return SimpleNamespace(type=tipo, **dados)

        def eventos():
            if recusa:
                yield evento("response.refusal.delta", delta="não posso")
            else:
                for pedaco in re.findall(r"\S+\s*", resposta):
                    yield evento("response.output_text.delta", delta=pedaco)
            if quebra:
                yield evento("error", message="caiu no meio")
            uso = SimpleNamespace(output_tokens=4)
            yield evento("response.completed", response=SimpleNamespace(usage=uso))

        class Respostas:
            def create(self, **pedido):
                cliente.pedidos.append(pedido)
                if erro:
                    raise erro
                return eventos()

        self.responses = Respostas()


def montar(criar_raiz, local=None, cliente=None, toml="", openai=None):
    config = carregar(criar_raiz(local=toml), ambiente={"ANTHROPIC_API_KEY": "chave"})
    cliente = cliente or ClienteFalso()
    nuvem, gpt = config.modelo_nuvem, config.modelo_openai
    rapido = CerebroNuvem(config, nuvem.rapido, nuvem.esforco_rapido, cliente=cliente)
    pesado = CerebroNuvem(config, nuvem.pesado, nuvem.esforco_pesado, cliente=cliente)
    extras = {}
    if openai:  # sem cliente falso, o ChatGPT fica indisponível (sem OPENAI_API_KEY)
        extras = {
            "rapido_openai": CerebroOpenAI(config, gpt.rapido, gpt.esforco_rapido, cliente=openai),
            "pesado_openai": CerebroOpenAI(config, gpt.pesado, gpt.esforco_pesado, cliente=openai),
        }
    roteador = Roteador(config, local or LocalFalso(), rapido, pesado, **extras)
    return roteador, cliente


def falar(roteador, texto):
    mensagens = [{"role": "system", "content": "Você é a Nora."}]
    mensagens.append({"role": "user", "content": texto})
    return "".join(roteador.responder(mensagens))


def test_comandos_e_pedidos_de_pergunta_dificil():
    assert comando_em("Nora, use o cérebro local") == "local"
    assert comando_em("usa o Claude agora") == "nuvem"
    assert comando_em("modo jogo") == "jogo" and comando_em("sai do modo jogo") == "jogo_fim"
    assert comando_em("volta pro modo automático") == "automatico"
    assert comando_em("qual a capital da França?") is None
    longa = "me explica o que é o modelo local de negócios que as empresas usam hoje em dia"
    assert comando_em(longa) is None  # frase longa é pergunta
    assert pede_pesado("pensa com calma: quanto é 17 vezes 23?")
    assert pede_pesado("pergunta pro Claude como funciona um transistor")
    assert not pede_pesado("fala mais devagar, com calma")


def test_conversa_do_dia_a_dia_fica_no_local(criar_raiz):
    roteador, cliente = montar(criar_raiz)
    assert falar(roteador, "oi, tudo bem?") == "Resposta local."
    assert cliente.pedidos == [] and roteador.origem.startswith("local")
    # o local recebe a instrução de passar adiante as difíceis
    assert ESCALAR in roteador.local.pedidos[0][-1]["content"]


def test_local_passa_a_dificil_para_o_claude_com_frase_de_espera(criar_raiz):
    local = LocalFalso(resposta=f" {ESCALAR}")
    roteador, cliente = montar(criar_raiz, local=local)
    resposta = falar(roteador, "me fala sobre a vida das formigas")
    espera, resto = resposta.split(" ", 1)[0], resposta
    assert any(resto.startswith(f) for f in FRASES_DE_ESPERA), espera
    assert resposta.endswith("Resposta do Claude.") and ESCALAR not in resposta
    assert local.fechado  # parou de ouvir o local
    pedido = cliente.pedidos[0]
    assert pedido["model"] == "claude-sonnet-5-5" and pedido["system"] == "Você é a Nora."
    assert pedido["output_config"] == {"effort": "medium"}
    assert pedido["beta"] and pedido["fallbacks"] == "default"  # recusa resolvida no servidor
    assert roteador.origem == "Claude Sonnet 5.5"


def test_etiqueta_de_emocao_no_comeco_nao_e_confundida_com_escalar(criar_raiz):
    roteador, cliente = montar(criar_raiz, local=LocalFalso(resposta="{alegre} Oi!"))
    assert falar(roteador, "oi!") == "{alegre} Oi!" and cliente.pedidos == []


def test_pedido_direto_vai_para_o_claude(criar_raiz):
    roteador, cliente = montar(criar_raiz)
    resposta = falar(roteador, "pensa com calma: qual o melhor plano de estudos para cálculo?")
    assert resposta.endswith("Resposta do Claude.") and roteador.local.pedidos == []


def test_comandos_trocam_o_cerebro(criar_raiz):
    roteador, cliente = montar(criar_raiz)
    assert "só com o cérebro local" in falar(roteador, "use o cérebro local")
    falar(roteador, "pensa com calma: algo difícil")  # no modo local, nem o pedido sobe
    assert cliente.pedidos == []
    assert "tudo pelo Claude" in falar(roteador, "usa o Claude")
    assert falar(roteador, "oi") == "Resposta do Claude."
    assert cliente.pedidos[-1]["model"] == "claude-haiku-5-5"  # conversa: o rápido
    assert cliente.pedidos[-1]["output_config"] == {"effort": "low"}
    assert not cliente.pedidos[-1]["beta"]  # o Haiku não tem recusa no servidor
    assert "Modo jogo ligado" in falar(roteador, "modo jogo") and roteador.local.descarregou
    assert roteador.aquecer() == 0.0
    assert "desligado" in falar(roteador, "sai do modo jogo")
    assert "automático" in falar(roteador, "modo automático")


def test_reservas_quando_um_dos_cerebros_falha(criar_raiz):
    roteador, cliente = montar(criar_raiz, local=LocalFalso(falhar=True))
    assert falar(roteador, "oi") == "Resposta do Claude."
    assert "respondi pela nuvem" in roteador.avisos_pendentes()[0]

    sem_rede = ClienteFalso(erro=ConnectionError("rede caiu"))
    roteador, _ = montar(criar_raiz, cliente=sem_rede, toml='[roteador]\nmodo = "nuvem"\n')
    assert falar(roteador, "oi") == "Resposta local."
    assert "Respondi pelo cérebro local" in roteador.avisos_pendentes()[0]


def test_sem_chave_o_roteador_e_so_o_local(criar_raiz):
    config = carregar(criar_raiz(), ambiente={})
    local = LocalFalso()
    roteador = Roteador(config, local)
    assert not roteador.nuvem_disponivel()
    assert falar(roteador, "pensa com calma: algo difícil") == "Resposta local."
    assert ESCALAR not in local.pedidos[0][-1]["content"]  # sem Claude, nada de escalar
    assert "falta a ANTHROPIC_API_KEY" in falar(roteador, "usa o Claude")


def test_cerebro_nuvem_monta_o_pedido_e_trata_recusa(criar_raiz):
    sistema, conversa = separar_sistema(
        [
            {"role": "system", "content": "Persona."},
            {"role": "assistant", "content": "sobrou do começo"},
            {"role": "user", "content": "oi"},
            {"role": "system", "content": "Nota da memória."},
            {"role": "user", "content": "tudo bem?"},
        ]
    )
    assert sistema == "Persona.\n\nNota da memória."
    assert conversa == [{"role": "user", "content": "oi\n\ntudo bem?"}]
    assert nome_do_modelo("claude-haiku-5-5") == "Claude Haiku 5.5"

    config = carregar(criar_raiz(), ambiente={"ANTHROPIC_API_KEY": "x"})
    recusa = CerebroNuvem(config, "claude-sonnet-5-5", cliente=ClienteFalso("", parada="refusal"))
    assert "".join(recusa.responder([{"role": "user", "content": "algo"}])) == RECUSA
    sem_chave = CerebroNuvem(carregar(criar_raiz(), ambiente={}), "claude-haiku-5-5")
    with pytest.raises(CerebroIndisponivel, match="ANTHROPIC_API_KEY"):
        list(sem_chave.responder([{"role": "user", "content": "oi"}]))


def test_conversa_usa_o_roteador_e_guarda_quem_respondeu(criar_raiz):
    roteador, _ = montar(criar_raiz)
    conversa = nova_conversa(roteador.config, roteador, memoria=None)
    "".join(conversa.perguntar("pensa com calma: algo difícil"))
    assert conversa.origem == "Claude Sonnet 5.5"
    assert '"modelo": "Claude Sonnet 5.5"' in conversa.historico.arquivo.read_text("utf-8")


def test_triagem_manda_as_pesadas_direto_e_segunda_chance(criar_raiz):
    roteador, cliente = montar(criar_raiz)
    assert peso_da_pergunta("monta um plano de estudos de cálculo para 3 semanas") == "plano"
    assert peso_da_pergunta("quanto é 17 x 23?") == "conta"
    assert peso_da_pergunta("escreve um script python que renomeia fotos") == "código"
    assert peso_da_pergunta("me conta uma piada") == ""
    resposta = falar(roteador, "monta um plano de estudos de cálculo para 3 semanas")
    assert resposta.endswith("Resposta do Claude.") and roteador.local.pedidos == []

    # o local responde a conversa; a reclamação seguinte vai para o Claude
    falar(roteador, "qual o maior planeta?")
    assert roteador.origem.startswith("local")
    antes = len(cliente.pedidos)
    assert falar(roteador, "tá errado isso").endswith("Resposta do Claude.")
    assert len(cliente.pedidos) == antes + 1
    # reclamar de uma resposta que já veio do Claude não repete a subida
    assert roteador.origem.startswith("Claude")
    assert insatisfeito("não entendi") and not insatisfeito("obrigado!")


def test_triagem_desligada_e_aviso_quando_falta_o_claude(criar_raiz):
    roteador, cliente = montar(criar_raiz, toml="[roteador]\ntriagem = false\n")
    assert falar(roteador, "monta um plano de estudos") == "Resposta local."
    assert cliente.pedidos == []

    config = carregar(criar_raiz(), ambiente={})
    sem_claude = Roteador(config, LocalFalso())
    assert falar(sem_claude, "pensa com calma: monta um plano de estudos") == "Resposta local."
    falar(sem_claude, "escreve um script python")
    avisos = sem_claude.avisos_pendentes()
    assert len(avisos) == 1 and "falta a ANTHROPIC_API_KEY" in avisos[0]  # avisa uma vez só


def test_testar_conexao_diz_o_que_falta(criar_raiz, monkeypatch):
    import sys

    from nora.cerebro_nuvem import testar_conexao

    assert "ANTHROPIC_API_KEY" in testar_conexao(carregar(criar_raiz(), ambiente={}))
    monkeypatch.setitem(sys.modules, "anthropic", None)  # pacote não instalado
    config = carregar(criar_raiz(), ambiente={"ANTHROPIC_API_KEY": "x"})
    assert "pip install" in testar_conexao(config)


def test_chatgpt_e_o_padrao_das_dificeis_e_o_claude_a_reserva(criar_raiz):
    gpt = OpenAIFalso()
    roteador, claude = montar(criar_raiz, openai=gpt)
    resposta = falar(roteador, "monta um plano de estudos de cálculo para 3 semanas")
    assert resposta.endswith("Resposta do ChatGPT.") and claude.pedidos == []
    pedido = gpt.pedidos[0]
    assert pedido["model"] == "gpt-5.5" and pedido["instructions"] == "Você é a Nora."
    assert pedido["reasoning"] == {"effort": "medium"} and pedido["stream"]
    assert pedido["input"][-1]["role"] == "user"
    assert roteador.origem == "ChatGPT (gpt-5.5)" and roteador.medidas.tokens == 4
    assert falar(roteador, "oi") == "Resposta local."  # a conversa continua no local

    # o ChatGPT falha, recusa ou não responde: pede ao Claude
    for falho in (
        OpenAIFalso(erro=ConnectionError("rede")),
        OpenAIFalso(recusa=True),
        OpenAIFalso(resposta=""),
    ):
        roteador, claude = montar(criar_raiz, openai=falho)
        assert falar(roteador, "escreve um script python").endswith("Resposta do Claude.")
        assert roteador.origem == "Claude Sonnet 5.5"
        assert "Pedi ao Claude" in roteador.avisos_pendentes()[0]


def test_chatgpt_que_cai_no_meio_nao_repete_a_resposta_no_claude(criar_raiz):
    roteador, claude = montar(criar_raiz, openai=OpenAIFalso("Começo da resposta.", quebra=True))
    resposta = falar(roteador, "escreve um script python")
    assert resposta.endswith("Começo da resposta.") and claude.pedidos == []
    assert "pela metade" in roteador.avisos_pendentes()[0]


def test_escolher_a_nuvem_pelo_nome(criar_raiz):
    assert quem_foi_chamado("pergunta pro ChatGPT como funciona um motor") == "openai"
    assert quem_foi_chamado("usa o chat gpt nessa") == "openai"
    assert quem_foi_chamado("consulta o Claude sobre isso") == "anthropic"
    assert quem_foi_chamado("pensa com calma nessa") == ""
    assert comando_em("use o ChatGPT") == "nuvem"

    gpt = OpenAIFalso()
    roteador, claude = montar(criar_raiz, openai=gpt)
    assert falar(roteador, "pergunta pro Claude como funciona um motor").endswith(
        "Resposta do Claude."
    )
    assert gpt.pedidos == []
    # comando: a conversa toda vai para quem foi escolhido (o modelo rápido na conversa)
    assert "tudo pelo ChatGPT" in falar(roteador, "use o ChatGPT")
    assert falar(roteador, "oi") == "Resposta do ChatGPT."
    assert gpt.pedidos[-1]["reasoning"] == {"effort": "low"}
    assert "tudo pelo Claude" in falar(roteador, "usa o Claude")
    assert falar(roteador, "oi") == "Resposta do Claude."
    assert "chamo o ChatGPT" in falar(roteador, "modo automático")


def test_sem_chave_da_openai_o_claude_responde_calado_e_avisa_se_pedido(criar_raiz):
    roteador, claude = montar(criar_raiz)  # só o Claude configurado
    assert not roteador.disponivel("openai")
    assert falar(roteador, "escreve um script python").endswith("Resposta do Claude.")
    assert roteador.avisos_pendentes() == []  # ChatGPT só não configurado: sem aviso
    assert falar(roteador, "pergunta pro ChatGPT o que é um motor").endswith("Resposta do Claude.")
    assert "OPENAI_API_KEY" in roteador.avisos_pendentes()[0]


def test_complexas_pode_preferir_o_claude(criar_raiz):
    gpt = OpenAIFalso()
    roteador, claude = montar(criar_raiz, openai=gpt, toml='[roteador]\ncomplexas = "anthropic"\n')
    assert falar(roteador, "escreve um script python").endswith("Resposta do Claude.")
    assert gpt.pedidos == []


def test_cerebro_openai_sem_chave_e_testar_conexao(criar_raiz, monkeypatch):
    import sys

    from nora.cerebro_openai import testar_conexao

    sem_chave = CerebroOpenAI(carregar(criar_raiz(), ambiente={}), "gpt-5.5")
    with pytest.raises(CerebroIndisponivel, match="OPENAI_API_KEY"):
        list(sem_chave.responder([{"role": "user", "content": "oi"}]))
    assert "OPENAI_API_KEY" in testar_conexao(carregar(criar_raiz(), ambiente={}))
    monkeypatch.setitem(sys.modules, "openai", None)
    config = carregar(criar_raiz(), ambiente={"OPENAI_API_KEY": "x"})
    assert "pip install" in testar_conexao(config)


# --- regressões do relatório de fechamento da v0.3.0 -------------------------------------------


def test_modo_jogo_sem_nuvem_nao_reacende_o_cerebro_local(criar_raiz):
    """A1: no modo jogo, se a nuvem falhar, o local não é chamado (a placa de vídeo fica livre)."""
    sem_rede = ClienteFalso(erro=ConnectionError("rede caiu"))
    roteador, _ = montar(criar_raiz, cliente=sem_rede)
    falar(roteador, "modo jogo")
    roteador.local.pedidos.clear()
    resposta = falar(roteador, "oi, tudo bem?")
    assert roteador.local.pedidos == []
    assert "modo jogo" in resposta and "sair do modo jogo" in resposta
    assert roteador.situacao == "sem resposta"
    assert any("cérebro local" in aviso for aviso in roteador.avisos_pendentes())

    config = carregar(criar_raiz(), ambiente={})  # nenhuma nuvem configurada
    sozinho = Roteador(config, LocalFalso())
    falar(sozinho, "modo jogo")
    sozinho.local.pedidos.clear()
    assert "modo jogo" in falar(sozinho, "oi") and sozinho.local.pedidos == []
    falar(sozinho, "sai do modo jogo")
    assert falar(sozinho, "oi") == "Resposta local."  # fora do modo jogo, volta ao normal


def test_comando_com_pergunta_responde_a_pergunta(criar_raiz):
    """A3: "use o Claude para explicar X" responde X pelo Claude, sem só trocar o modo."""
    assert comando_em("use o Claude para explicar fotossíntese") is None
    assert comando_em("usa o Claude agora") == "nuvem"
    assert comando_em("Nora, use o cérebro local, por favor") == "local"
    gpt = OpenAIFalso()
    roteador, claude = montar(criar_raiz, openai=gpt)
    resposta = falar(roteador, "use o Claude para explicar fotossíntese")
    assert resposta.endswith("Resposta do Claude.") and gpt.pedidos == []
    assert roteador.modo == "automatico"  # não trocou o modo da conversa
    assert "fotossíntese" in claude.pedidos[-1]["messages"][-1]["content"]

    pedidos = len(claude.pedidos)
    resposta = falar(roteador, "use o cérebro local pra calcular 17 x 23")
    assert resposta == "Resposta local." and len(claude.pedidos) == pedidos  # só esta, no local
    assert roteador.modo == "automatico"

    resposta = falar(roteador, "modo jogo, quanto falta pro meu aniversário?")
    assert resposta.startswith("Modo jogo ligado") and resposta.endswith("Resposta do ChatGPT.")
    assert roteador.jogo


def test_falha_do_local_no_meio_nao_emenda_outra_resposta(criar_raiz):
    """A4 e A5: o local caiu depois de falar: nada de resposta da nuvem colada no fim."""
    local = LocalFalso(resposta="Uma resposta comprida do local.", cair_depois=2)
    roteador, claude = montar(criar_raiz, local=local, toml="[roteador]\nescalar = false\n")
    resposta = falar(roteador, "oi, tudo bem?")
    assert resposta == "Uma re" and claude.pedidos == []
    assert roteador.situacao == "interrompida"
    assert "pela metade" in roteador.avisos_pendentes()[0]

    # com o {pensar} ligado, o mesmo vale depois do começo já ter sido falado
    local = LocalFalso(resposta="Uma resposta comprida do local.", cair_depois=4)
    roteador, claude = montar(criar_raiz, local=local)
    assert falar(roteador, "oi") == "Uma resposta" and claude.pedidos == []
    assert roteador.situacao == "interrompida"

    # antes de falar qualquer coisa, a reserva continua valendo
    roteador, _ = montar(criar_raiz, local=LocalFalso(falhar=True))
    assert falar(roteador, "oi") == "Resposta do Claude." and roteador.situacao == "completa"


def test_falha_da_nuvem_no_meio_fica_marcada(criar_raiz):
    roteador, _ = montar(criar_raiz, openai=OpenAIFalso("Começo da resposta.", quebra=True))
    falar(roteador, "escreve um script python")
    assert roteador.situacao == "interrompida"


def test_resposta_interrompida_fica_marcada_no_historico_e_nao_vai_para_a_memoria(
    criar_raiz, monkeypatch
):
    """A5: o histórico guarda a situação real e a curadoria não recebe a resposta parcial."""
    from nora.conversa import Conversa

    curadas = []
    monkeypatch.setattr(Conversa, "_memorizar", lambda self, *a: curadas.append(a))
    monkeypatch.setattr(Conversa, "_lembrar", lambda self, texto: [])
    local = LocalFalso(resposta="Uma resposta comprida do local.", cair_depois=2)
    roteador, _ = montar(criar_raiz, local=local, toml="[roteador]\nescalar = false\n")
    conversa = nova_conversa(roteador.config, roteador, memoria=object(), notas=None)
    "".join(conversa.perguntar("oi, tudo bem?"))
    historico = conversa.historico.arquivo.read_text("utf-8")
    assert '"situacao": "interrompida"' in historico and curadas == []

    roteador.local = LocalFalso()
    "".join(conversa.perguntar("e agora?"))
    assert len(curadas) == 1  # resposta completa: segue para a memória
