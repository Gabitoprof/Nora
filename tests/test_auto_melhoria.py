"""Self-improvement: observer, closing the day, report, decisions and notice."""

from datetime import date, datetime, timedelta

import pytest
from test_roteador import ClienteFalso, OpenAIFalso, montar

from nora.config import carregar
from nora.conversa import nova_conversa
from nora.melhorias import Agendador, Melhorias, notificar
from nora.observador import Observador, caminho_do_banco


def _conversa(criar_raiz, local=None, openai=None, cliente=None, toml=""):
    roteador, _ = montar(criar_raiz, local=local, openai=openai, cliente=cliente, toml=toml)
    conversa = nova_conversa(roteador.config, roteador, memoria=None, notas=None)
    return conversa, roteador


def test_observador_anota_tentativas_comandos_e_reclamacoes_sem_texto(criar_raiz):
    conversa, roteador = _conversa(criar_raiz, openai=OpenAIFalso(erro=ConnectionError("rede")))
    "".join(conversa.perguntar("escreve um script python que renomeia fotos"))
    "".join(conversa.perguntar("qual o maior planeta?"))  # the local model answers
    "".join(conversa.perguntar("tá errado isso"))  # complaint about the local answer
    "".join(conversa.perguntar("modo jogo"))
    eventos = conversa.observador.eventos()
    tipos = [(e["etapa"], e["tipo"], e["motor"]) for e in eventos]
    assert ("llm", "erro_provedor", "ChatGPT (gpt-5.5)") in tipos
    assert ("llm", "resposta", "Claude Sonnet 5.5") in tipos
    assert ("llm", "feedback_negativo", "local (qwen3.5:9b)") in tipos
    assert ("roteador", "rota_suspeita", "local (qwen3.5:9b)") in tipos
    assert ("roteador", "comando", "") in tipos
    reclamacao = next(e for e in eventos if e["tipo"] == "feedback_negativo")
    assert reclamacao["correlacao"] and reclamacao["correlacao"] != reclamacao["interacao"]
    assert all(e["versao"] for e in eventos)
    # the conversation text does not go to the observer's database
    banco = caminho_do_banco(roteador.config.pasta_dados).read_bytes()
    assert b"renomeia" not in banco and b"planeta" not in banco


def test_observador_nao_derruba_a_conversa(tmp_path):
    observador = Observador(tmp_path / "a.db")
    observador.fechar()
    observador.registrar("llm", "resposta")  # database closed: ignored, no error


def test_auto_melhoria_desligada_nao_observa(criar_raiz):
    conversa, roteador = _conversa(criar_raiz, toml="[auto_melhoria]\nativa = false\n")
    "".join(conversa.perguntar("oi"))
    assert conversa.observador is None
    assert not caminho_do_banco(roteador.config.pasta_dados).exists()


# --- closing the day, report and decisions (P2) --------------------------------------------------


DIA = datetime(2026, 11, 3, 10, 0)


def _melhorias(criar_raiz, toml=""):
    config = carregar(criar_raiz(local=toml), ambiente={})
    return Melhorias(config)


def _eventos(m, tipo="erro_provedor", motor="ChatGPT (gpt-5.5)", n=4, quando=DIA, **extra):
    for i in range(n):
        m.observador.registrar(
            "llm", tipo, motor, f"int-{tipo}-{i}", quando=quando + timedelta(minutes=i), **extra
        )


def test_eventos_repetidos_viram_uma_proposta_com_evidencia(criar_raiz):
    m = _melhorias(criar_raiz)
    _eventos(m, n=6)
    _eventos(m, "resposta", "local (qwen3.5:9b)", n=3, duracao_ms=4000)  # slow
    _eventos(m, "resposta", "local (qwen3.5:9b)", n=5, duracao_ms=500)  # fast: normal
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=1)  # only once: does not become a proposal
    fechamento = m.fechar(DIA.date(), DIA + timedelta(hours=10))
    titulos = [p.titulo for p in fechamento.novas]
    assert titulos == [
        "ChatGPT (gpt-5.5) falhou 6 vezes",
        "local (qwen3.5:9b) lento para começar a responder (3 vezes)",
    ]
    evidencia = fechamento.novas[1].dados["evidencia"]
    assert evidencia["ocorrencias"] == 3 and evidencia["de_um_total_de"] == 8
    assert evidencia["mediana_ms"] == 4000 and evidencia["exemplos"]
    texto = fechamento.caminho.read_text("utf-8")
    assert (
        "Nº 1 — ChatGPT (gpt-5.5) falhou 6 vezes" in texto and "nora melhorias aprovar 1" in texto
    )
    assert "Fontes:** nenhuma" in texto  # no internet

    # the next day, the same problem updates the same proposal (without duplicating)
    _eventos(m, n=4, quando=DIA + timedelta(days=1))
    seguinte = m.fechar(DIA.date() + timedelta(days=1), DIA + timedelta(days=1, hours=10))
    assert seguinte.novas == [] and [p.id for p in seguinte.esperando] == [1]
    assert len(m.propostas()) == 2


def test_dia_sem_problemas_nao_inventa_diagnostico(criar_raiz):
    m = _melhorias(criar_raiz)
    _eventos(m, "resposta", "local (qwen3.5:9b)", n=10, duracao_ms=300)
    fechamento = m.fechar(DIA.date(), DIA + timedelta(hours=10))
    assert fechamento.novas == [] and fechamento.resumo == "sem novas melhorias relevantes"
    assert "Sem novas melhorias relevantes" in fechamento.caminho.read_text("utf-8")


def test_um_relatorio_por_dia_na_hora_marcada_e_recupera_o_dia_perdido(criar_raiz):
    m = _melhorias(criar_raiz, toml='[auto_melhoria]\nhora_relatorio = "20:00"\n')
    assert m.dia_a_fechar(DIA) is None  # first use, no events: only marks the start
    _eventos(m, n=3, quando=DIA)
    assert m.dia_a_fechar(DIA.replace(hour=19)) is None  # before the time: nothing
    noite = DIA.replace(hour=20, minute=5)
    assert m.dia_a_fechar(noite) == DIA.date()
    m.fechar(DIA.date(), noite)
    assert m.dia_a_fechar(noite + timedelta(minutes=30)) is None  # one per day

    # the PC was off on day 4 at 20:00; on the morning of day 5, day 4's report comes out
    _eventos(m, n=3, quando=DIA + timedelta(days=1))
    manha_dia_5 = DIA + timedelta(days=2, hours=-2)
    assert m.dia_a_fechar(manha_dia_5) == date(2026, 11, 4)
    perdido = m.fechar(date(2026, 11, 4), manha_dia_5)
    assert perdido.eventos == 3  # only the events after the previous closing
    assert m.dia_a_fechar(manha_dia_5) is None
    assert [d for d, _, _ in m.nao_mostrados()] == ["2026-11-03", "2026-11-04"]
    assert len(m.nao_mostrados()) == 2  # they only leave the list when they actually appear
    for data, _, _ in m.nao_mostrados():
        m.marcar_mostrado(data)
    assert m.nao_mostrados() == []


def test_agendador_espera_a_nora_desocupada_e_avisa(criar_raiz):
    m = _melhorias(criar_raiz)
    _eventos(m, n=3)
    fechados, ocupada = [], [True]
    noite = DIA.replace(hour=21)
    agendador = Agendador(m, lambda: ocupada[0], fechados.append, relogio=lambda: noite)
    assert agendador.conferir() is None and fechados == []  # answering or in game mode
    ocupada[0] = False
    assert agendador.conferir() is not None and len(fechados) == 1
    assert agendador.conferir() is None  # does not repeat


def test_decisoes_aprovar_recusar_adiar(criar_raiz):
    m = _melhorias(criar_raiz)
    _eventos(m, n=3)
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=3)
    _eventos(m, "resposta_vazia", "ChatGPT (gpt-5.5)", n=3)
    m.fechar(DIA.date(), DIA + timedelta(hours=10))
    ids = {p.categoria: p.id for p in m.propostas()}

    aprovada = m.decidir(ids["erro_provedor"], "aprovar", "teste", "vale a pena")
    assert aprovada.status == "aprovada"
    tarefa = m.pasta / "tarefas" / f"melhoria-{aprovada.id}.md"
    assert "Publicar exige nova autorização" in tarefa.read_text("utf-8")
    assert m.decidir(ids["erro_provedor"], "recusar", "teste") is None  # already decided
    assert m.avancar(aprovada.id, "publicada", "teste") is None  # skipping stages
    for estado in ("preparacao", "em_teste", "pronta_para_revisao"):
        assert m.avancar(aprovada.id, estado, "teste").status == estado
    assert m.avancar(aprovada.id, "publicada", "teste") is None  # without authorization
    assert m.avancar(aprovada.id, "publicada", "teste", autorizo_publicar=True)
    assert [a for _, a, _, _ in m.decisoes(aprovada.id)][0] == "aprovar"

    m.decidir(ids["timeout"], "recusar", "teste")
    m.decidir(ids["resposta_vazia"], "adiar", "teste", dias=3)
    dia2 = DIA + timedelta(days=1)
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=4, quando=dia2)  # little that is new
    _eventos(m, "resposta_vazia", "ChatGPT (gpt-5.5)", n=3, quando=dia2)
    f2 = m.fechar(dia2.date(), dia2 + timedelta(hours=10))
    assert f2.novas == []  # rejected without new evidence and postponed ones do not come back
    dia5 = DIA + timedelta(days=5)
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=8, quando=dia5)  # twice as many: new evidence
    _eventos(m, "resposta_vazia", "ChatGPT (gpt-5.5)", n=3, quando=dia5)
    f5 = m.fechar(dia5.date(), dia5 + timedelta(hours=10))
    assert sorted(p.categoria for p in f5.novas) == ["resposta_vazia", "timeout"]


def test_fechamento_nao_usa_a_rede(criar_raiz, monkeypatch):
    import socket

    def sem_rede(*a, **k):
        raise AssertionError("a auto-melhoria não pode usar a rede")

    monkeypatch.setattr(socket, "socket", sem_rede)
    monkeypatch.setattr(socket, "create_connection", sem_rede)
    m = _melhorias(criar_raiz)
    _eventos(m, n=3)
    assert m.fechar(DIA.date(), DIA + timedelta(hours=10)).novas


def test_notificacao_do_windows_abre_o_relatorio(tmp_path, monkeypatch):
    import subprocess
    import sys

    relatorio = tmp_path / "2026-11-03.md"
    relatorio.write_text("# oi", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "linux")
    assert notificar("t", "x", relatorio) is False
    chamadas = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **k: chamadas.append(cmd) or subprocess.CompletedProcess(cmd, 0),
    )
    assert notificar("Nora: melhorias", "2 propostas & 'teste'", relatorio)
    script = chamadas[0][-1]
    assert relatorio.resolve().as_uri() in script and "&amp;" in script and "''teste''" in script


def test_decidir_pela_conversa_pede_numero_claro_e_confirmacao(criar_raiz):
    from nora.conversa import pedido_de_melhoria

    assert pedido_de_melhoria("quais melhorias você sugeriu?") == ("listar", 0)
    assert pedido_de_melhoria("Nora, aprova a melhoria 3") == ("aprovar", 3)
    assert pedido_de_melhoria("recusa a melhoria três") == ("recusar", 3)
    assert pedido_de_melhoria("adia a melhoria número 2") == ("adiar", 2)
    assert pedido_de_melhoria("aprova isso") is None  # without "melhoria"

    conversa, roteador = _conversa(criar_raiz)
    _eventos(conversa.melhorias, n=3)
    conversa.melhorias.fechar(DIA.date(), DIA + timedelta(hours=10))
    assert "número 1" in "".join(conversa.perguntar("quais melhorias você sugeriu?"))
    assert "Não achei a melhoria 9" in "".join(conversa.perguntar("aprova a melhoria 9"))
    pergunta = "".join(conversa.perguntar("aprova a melhoria 1"))
    assert 'Diga "sim"' in pergunta and conversa.melhorias.proposta(1).status == "proposta"
    assert "Tudo bem" in "".join(conversa.perguntar("não"))
    "".join(conversa.perguntar("aprova a melhoria um"))
    assert "aprovada" in "".join(conversa.perguntar("sim"))
    assert conversa.melhorias.proposta(1).status == "aprovada"
    assert roteador.local.pedidos == []  # none of this went through the brain


def test_inicio_da_sessao_abre_o_relatorio_novo(criar_raiz, monkeypatch):
    """Audit P1: the new report appears in full without the person typing anything."""
    from nora import melhorias as modulo

    monkeypatch.setattr(
        modulo.Agendador, "start", lambda self: None
    )  # no thread: does not depend on the time

    abertos = []
    monkeypatch.setattr(modulo, "abrir_arquivo", lambda c: abertos.append(c) or True)
    conversa, _ = _conversa(criar_raiz)
    _eventos(conversa.melhorias, n=3)
    caminho = conversa.melhorias.fechar(DIA.date(), DIA + timedelta(hours=10)).caminho
    linhas = []
    modulo.iniciar(conversa, linhas.append).parar()
    assert abertos == [caminho] and any("Abri o relatório de 03/11" in x for x in linhas)
    assert conversa.melhorias.nao_mostrados() == []
    linhas.clear()
    modulo.iniciar(conversa, linhas.append).parar()
    assert abertos == [caminho] and linhas == []  # only once


def test_se_nao_abrir_mostra_o_texto_inteiro_e_registra_a_falha(criar_raiz, monkeypatch):
    from nora import melhorias as modulo

    monkeypatch.setattr(
        modulo.Agendador, "start", lambda self: None
    )  # no thread: does not depend on the time

    monkeypatch.setattr(modulo, "abrir_arquivo", lambda c: False)
    conversa, _ = _conversa(criar_raiz)
    _eventos(conversa.melhorias, n=3)
    caminho = conversa.melhorias.fechar(DIA.date(), DIA + timedelta(hours=10)).caminho
    linhas = []
    modulo.iniciar(conversa, linhas.append).parar()
    assert caminho.read_text("utf-8") in linhas  # the whole report, not a summary
    assert "não consegui abrir" in conversa.melhorias.falha_do_aviso("2026-11-03")
    assert conversa.melhorias.nao_mostrados() == []


@pytest.mark.parametrize("modo,abre", [("terminal", False), ("abrir", False), ("abrir", True)])
def test_relatorio_na_sessao_atual_sem_nova_entrada(criar_raiz, monkeypatch, modo, abre):
    import threading

    from nora import melhorias as modulo

    monkeypatch.setattr(modulo.Agendador, "start", lambda self: None)
    abertos, linhas, threads = [], [], []
    exibido = threading.Event()
    principal = threading.get_ident()

    def abrir(caminho):
        abertos.append(caminho)
        return abre

    def escrever(linha):
        linhas.append(linha)
        threads.append(threading.get_ident())
        exibido.set()

    monkeypatch.setattr(modulo, "abrir_arquivo", abrir)
    conversa, _ = _conversa(criar_raiz, toml=f'[auto_melhoria]\napresentar = "{modo}"\n')
    _eventos(conversa.melhorias, n=3)
    agendador = modulo.iniciar(conversa, escrever)
    agendador.relogio = lambda: DIA.replace(hour=21)

    def entrada(prompt):
        agendador.conferir()  # the day closes while the keyboard is waiting
        assert exibido.wait(3), "o relatório exigiu uma nova entrada"
        return "sair"

    assert modulo.ler_entrada(entrada, "", agendador) == "sair"
    caminho = conversa.melhorias.relatorio()
    if not abre:
        assert caminho.read_text("utf-8") in linhas
    assert bool(abertos) == (modo == "abrir")
    assert set(threads) == {principal}  # never writes from the scheduler
    assert conversa.melhorias.nao_mostrados() == []
    agendador.apresentar_pendentes()
    assert conversa.melhorias.dia_a_fechar(DIA.replace(hour=22)) is None
    agendador.parar()


def test_no_modo_jogo_o_relatorio_espera(criar_raiz, monkeypatch):
    from nora import melhorias as modulo

    monkeypatch.setattr(
        modulo.Agendador, "start", lambda self: None
    )  # no thread: does not depend on the time

    abertos = []
    monkeypatch.setattr(modulo, "abrir_arquivo", lambda c: abertos.append(c) or True)
    conversa, roteador = _conversa(criar_raiz)
    _eventos(conversa.melhorias, n=3)
    conversa.melhorias.fechar(DIA.date(), DIA + timedelta(hours=10))
    roteador.jogo = True
    modulo.iniciar(conversa, lambda linha: None).parar()
    assert abertos == [] and len(conversa.melhorias.nao_mostrados()) == 1


def test_retomada_marca_a_nora_ocupada_e_o_relatorio_espera(criar_raiz):
    """Audit P1: while an answer is being resumed, the scheduler does not close the day."""
    from test_memoria import EmbeddingsFalsos

    from nora.cerebro import Medidas
    from nora.melhorias import Agendador
    from nora.memoria import Memoria

    config = carregar(criar_raiz(local="[memoria]\nativa = true\ncuradoria = false\n"), ambiente={})
    m = Memoria(config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    m.marcar_pendente("x1", "s1", "qual a distância da Lua?", "São", "cancelada", "local")
    vistos = {}

    class CerebroLento:
        medidas, origem = Medidas(), "local (qwen3.5:9b)"

        def responder(self, mensagens):
            vistos["ocupada"] = conversa.ocupada
            vistos["fechou"] = agendador.conferir()
            yield "Uns 384 mil quilômetros."

    conversa = nova_conversa(config, CerebroLento(), memoria=m, notas=None)
    _eventos(conversa.melhorias, n=3)
    noite = DIA.replace(hour=21)
    agendador = Agendador(
        conversa.melhorias, lambda: conversa.ocupada, lambda f: None, relogio=lambda: noite
    )
    resposta = "".join(conversa.perguntar("termina a resposta que ficou pela metade"))
    assert resposta.endswith("quilômetros.")
    assert vistos == {"ocupada": True, "fechou": None}  # waited for the resumption to end
    assert not conversa.ocupada and agendador.conferir() is not None  # afterwards, it closes


def test_relatorio_nao_mostra_perguntas_e_limpa_os_antigos(criar_raiz):
    """Audit P1: the report does not reproduce the text of the questions (nor the ones already
    written)."""
    from nora.memoria import Pendente

    m = _melhorias(criar_raiz)
    pendente = Pendente(
        7,
        "i7",
        "s1",
        "qual o segredo do cofre (aquele)?",
        "É",
        "cancelada",
        "local",
        "2026-11-03T10:00:00",
        "pendente",
        1,
    )
    texto = m.fechar(DIA.date(), DIA + timedelta(hours=10), [pendente]).caminho.read_text("utf-8")
    assert "segredo" not in texto and "cofre" not in texto
    assert "nº 7" in texto and "cancelada" in texto and "nora pendencias" in texto

    # report written before this fix, with the question text
    antigo = m.pasta / "relatorios" / "2026-11-01.md"
    antigo.write_text(
        "## Respostas que ficaram pela metade\n\n"
        "- nº 3: meu segredo (o do cofre) (cancelada, 0 tentativa(s))\n- outra linha\n",
        encoding="utf-8",
    )
    m.fechar_banco()
    _melhorias(criar_raiz)  # on opening, it cleans up
    limpo = antigo.read_text("utf-8")
    assert "segredo" not in limpo and "- nº 3 (cancelada, 0 tentativa(s))" in limpo
    assert "- outra linha" in limpo


def test_sem_resposta_no_modo_jogo_nao_sugere_usar_o_local(criar_raiz):
    """Audit P2: the proposal does not suggest breaking game mode; when leaving it (with "sim"),
    Nora offers to resume the questions left unanswered."""
    from test_memoria import EmbeddingsFalsos

    from nora.melhorias import REGRAS
    from nora.memoria import Memoria

    regra = REGRAS[("llm", "sem_resposta")]
    texto = " ".join([regra.solucao, regra.impacto, regra.risco]).lower()
    assert "permitir o local" not in texto and "pendência" in texto

    toml = "[memoria]\nativa = true\ncuradoria = false\n"
    conversa, roteador = _conversa(
        criar_raiz, cliente=ClienteFalso(erro=ConnectionError("rede caiu")), toml=toml
    )
    conversa.memoria = Memoria(roteador.config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    "".join(conversa.perguntar("modo jogo"))
    "".join(conversa.perguntar("qual a capital da Austrália?"))
    assert [p.motivo for p in conversa.memoria.pendentes()] == ["sem_resposta"]
    conversa.avisos_pendentes()
    "".join(conversa.perguntar("sai do modo jogo"))
    assert roteador.jogo  # not yet: the "sim" is missing
    assert not any("modo jogo" in a for a in conversa.avisos_pendentes())
    "".join(conversa.perguntar("sim"))
    assert not roteador.jogo
    oferta = [a for a in conversa.avisos_pendentes() if "sem resposta no modo jogo" in a]
    assert oferta and "termina a resposta" in oferta[0]
    assert len(conversa.memoria.pendentes()) == 1  # only offers; does not answer on her own


@pytest.mark.parametrize("bloqueio", ["ocupada", "jogo"])
def test_relatorio_pendente_aparece_apos_desbloquear(criar_raiz, monkeypatch, bloqueio):
    from nora import melhorias as modulo

    monkeypatch.setattr(modulo.Agendador, "start", lambda self: None)
    conversa, roteador = _conversa(criar_raiz, toml='[auto_melhoria]\napresentar = "terminal"\n')
    fechamento = conversa.melhorias.fechar(DIA.date(), DIA.replace(hour=21))
    alvo = conversa if bloqueio == "ocupada" else roteador
    setattr(alvo, bloqueio, True)
    linhas = []
    agendador = modulo.iniciar(conversa, linhas.append)
    agendador.apresentar_pendentes()
    assert linhas == []
    setattr(alvo, bloqueio, False)
    agendador.apresentar_pendentes()
    assert fechamento.caminho.read_text("utf-8") in linhas
    assert conversa.melhorias.nao_mostrados() == []
    assert roteador.local.pedidos == []


@pytest.mark.parametrize("quebra", ["\n", "\r\n"], ids=["LF", "CRLF"])
def test_arquivo_ausente_continua_pendente_e_pode_ser_restaurado(criar_raiz, monkeypatch, quebra):
    from nora import melhorias as modulo

    monkeypatch.setattr(modulo.Agendador, "start", lambda self: None)
    conversa, _ = _conversa(criar_raiz, toml='[auto_melhoria]\napresentar = "terminal"\n')
    m = conversa.melhorias
    caminho = m.fechar(DIA.date(), DIA.replace(hour=21)).caminho
    texto = caminho.read_text(encoding="utf-8")
    caminho.write_bytes(texto.replace("\n", quebra).encode("utf-8"))
    copia = caminho.read_bytes()
    caminho.unlink()
    linhas = []
    agendador = modulo.iniciar(conversa, linhas.append)
    assert len(m.nao_mostrados()) == 1
    assert "arquivo não encontrado" in m.falha_do_aviso("2026-11-03")
    assert "Restaure" in linhas[0]
    for _ in range(5):
        agendador.apresentar_pendentes()
    assert len(linhas) == 1  # no repeated notices
    caminho.write_bytes(copia)
    modulo.iniciar(conversa, linhas.append)
    assert caminho.read_bytes() == copia  # the restoration keeps the original bytes
    assert caminho.read_text(encoding="utf-8") == texto
    assert texto in linhas  # text-mode presentation normalizes CRLF/LF
    assert m.nao_mostrados() == []


@pytest.mark.parametrize("falha", [PermissionError, UnicodeError, OSError, FileNotFoundError])
def test_falha_de_leitura_nao_derruba_conversa(criar_raiz, monkeypatch, falha):
    from pathlib import Path

    from nora import melhorias as modulo

    conversa, _ = _conversa(criar_raiz)
    m = conversa.melhorias
    caminho = m.fechar(DIA.date(), DIA.replace(hour=21)).caminho
    original = Path.read_text

    def ler(self, *args, **kwargs):
        if self == caminho:
            if falha is UnicodeError:
                return b"\xff".decode("utf-8")
            raise falha("texto pessoal que não deve ir ao diagnóstico")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", ler)
    linhas = []
    assert not modulo.apresentar(m, "2026-11-03", caminho, 0, "terminal", linhas.append)
    assert len(m.nao_mostrados()) == 1
    diagnostico = m.falha_do_aviso("2026-11-03")
    assert ("UnicodeDecodeError" if falha is UnicodeError else falha.__name__) in diagnostico
    assert "texto pessoal" not in diagnostico
    assert "continua pendente" in linhas[0]
    assert "".join(conversa.perguntar("oi"))  # the conversation keeps working
    monkeypatch.setattr(Path, "read_text", original)
    assert modulo.apresentar(m, "2026-11-03", caminho, 0, "terminal", linhas.append)
    assert m.nao_mostrados() == []


def test_agendador_registra_falha_e_continua_sem_texto_pessoal(criar_raiz, caplog):
    m = _melhorias(criar_raiz)
    agendador = Agendador(m, lambda: False, lambda f: None, intervalo=0)
    chamadas = []

    def conferir():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise OSError("pergunta pessoal")
        agendador.parar()

    agendador.conferir = conferir
    agendador.run()
    assert len(chamadas) == 2
    assert "Falha no agendador: OSError" in caplog.text
    assert "pergunta pessoal" not in caplog.text


@pytest.mark.parametrize("interface", ["texto", "voz", "ouvir"])
def test_loops_entregam_relatorio_sem_pergunta(criar_raiz, monkeypatch, interface):
    import io
    import threading

    from nora import conversa as texto
    from nora import conversa_voz as voz
    from nora import maos_livres as ouvir
    from nora import melhorias

    conversa, _ = _conversa(criar_raiz, toml='[auto_melhoria]\napresentar = "terminal"\n')
    _eventos(conversa.melhorias, n=3)
    exibido = threading.Event()

    class Saida(io.StringIO):
        def write(self, texto):
            resultado = super().write(texto)
            if "## " in texto:
                exibido.set()
            return resultado

    saida = Saida()
    iniciou = threading.Event()
    agendadores = []
    monkeypatch.setattr(melhorias.Agendador, "start", lambda self: None)

    def iniciar(c, escrever):
        agendador = melhorias.iniciar(c, escrever)
        agendador.relogio = lambda: DIA.replace(hour=21)
        agendadores.append(agendador)
        iniciou.set()
        return agendador

    modulo = {"texto": texto, "voz": voz, "ouvir": ouvir}[interface]
    monkeypatch.setattr(modulo, "nova_conversa", lambda *a: conversa)
    monkeypatch.setattr(modulo, "iniciar_melhorias", iniciar)

    def entrada(prompt):
        assert iniciou.is_set()
        agendadores[0].conferir()
        assert exibido.wait(3), "o loop não entregou o relatório enquanto esperava entrada"
        return "sair"

    if interface == "texto":
        assert texto.conversar(conversa.config, entrada=entrada, saida=saida) == 0
    elif interface == "voz":
        assert (
            voz.conversar_por_voz(
                conversa.config, entrada=entrada, saida=saida, so_teclado=True, tocar=lambda _: None
            )
            == 0
        )
    else:

        def falas():
            agendadores[0].conferir()
            yield None  # VAD break, with no speech or typing

        assert (
            ouvir.conversar_maos_livres(
                conversa.config,
                saida=saida,
                teclado=False,
                tocar=lambda _: None,
                fontes=(falas(), lambda: None, lambda: None),
            )
            == 0
        )
    assert conversa.melhorias.relatorio().read_text("utf-8") in saida.getvalue()
    assert conversa.melhorias.nao_mostrados() == []


# --- Enter regression in `nora falar` with self-improvement on ----------------------------------


class Teclado:
    """A real keyboard in miniature: each call waits for the next typed line."""

    def __init__(self):
        import queue

        self.linhas, self.prompts = queue.Queue(), []

    def digitar(self, linha=""):
        self.linhas.put(linha)

    def __call__(self, prompt=""):
        self.prompts.append(prompt)
        return self.linhas.get(timeout=5)


def test_falha_ao_apresentar_nao_deixa_leitor_orfao_que_engole_o_enter():
    """If presenting the report errors while she waits for Enter, the next Enter (the one that
    stops recording) must not go to a reading thread left behind."""
    import threading

    from nora.melhorias import ler_entrada

    teclado = Teclado()
    chamadas = []

    class AgendadorQueFalha:
        def apresentar_pendentes(self):
            chamadas.append(1)
            if len(chamadas) == 2:
                raise OSError("disco ocupado")
            return False

    def digitar_depois():
        import time

        time.sleep(0.3)
        teclado.digitar("")  # Enter to speak

    threading.Thread(target=digitar_depois, daemon=True).start()
    assert ler_entrada(teclado, "[Enter para falar] ", AgendadorQueFalha()) == ""
    teclado.digitar("")  # Enter to stop recording: it has to reach the recording
    assert teclado("  (gravando...) ") == ""
    leitores = [t for t in threading.enumerate() if t.name == "nora-entrada" and t.is_alive()]
    assert leitores == []


def test_relatorio_que_aparece_na_espera_mostra_o_prompt_de_novo():
    import threading
    import time

    from nora.melhorias import ler_entrada

    teclado, telas, vezes = Teclado(), [], []

    class AgendadorComRelatorio:
        def apresentar_pendentes(self):
            vezes.append(1)
            if len(vezes) == 3:
                telas.append("[melhorias] Relatório de 04/11 ...")
                return True
            return False

    def digitar_depois():
        time.sleep(0.5)
        teclado.digitar("oi")

    threading.Thread(target=digitar_depois, daemon=True).start()
    linha = ler_entrada(
        teclado, "\n[Enter para falar] ", AgendadorComRelatorio(), reimprimir=telas.append
    )
    assert linha == "oi"
    assert telas == ["[melhorias] Relatório de 04/11 ...", "\n[Enter para falar] "]


def test_abrir_o_relatorio_nao_rouba_o_teclado_da_sessao(tmp_path, monkeypatch):
    """On Windows it opens minimized and without focus (Enter keeps going to Nora); elsewhere, the
    program does not inherit the terminal. The notification does not use the session's
    keyboard either."""
    import os
    import subprocess
    import sys

    from nora import melhorias as modulo

    relatorio = tmp_path / "2026-11-04.md"
    relatorio.write_text("# oi", encoding="utf-8")

    chamadas = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "startfile", lambda *a, **k: chamadas.append((a, k)), raising=False)
    assert modulo.abrir_arquivo(relatorio)
    assert chamadas == [((relatorio, "open"), {"show_cmd": modulo.SW_SHOWMINNOACTIVE})]

    execucoes = []

    def rodar(cmd, **k):
        execucoes.append(k)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", rodar)
    assert modulo.notificar("Nora", "pronto", relatorio)
    assert execucoes[0]["stdin"] is subprocess.DEVNULL

    abertos = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, **k: abertos.append((cmd, k)))
    assert modulo.abrir_arquivo(relatorio)
    cmd, k = abertos[0]
    assert cmd == ["xdg-open", str(relatorio)] and k["start_new_session"]
    assert k["stdin"] is subprocess.DEVNULL and k["stdout"] is subprocess.DEVNULL
