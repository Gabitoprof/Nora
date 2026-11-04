"""Auto-melhoria: observador, fechamento do dia, relatório, decisões e aviso."""

from datetime import date, datetime, timedelta

from test_roteador import OpenAIFalso, montar

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
    "".join(conversa.perguntar("qual o maior planeta?"))  # o local responde
    "".join(conversa.perguntar("tá errado isso"))  # reclamação da resposta do local
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
    # o texto da conversa não vai para o banco do observador
    banco = caminho_do_banco(roteador.config.pasta_dados).read_bytes()
    assert b"renomeia" not in banco and b"planeta" not in banco


def test_observador_nao_derruba_a_conversa(tmp_path):
    observador = Observador(tmp_path / "a.db")
    observador.fechar()
    observador.registrar("llm", "resposta")  # banco fechado: ignora, sem erro


def test_auto_melhoria_desligada_nao_observa(criar_raiz):
    conversa, roteador = _conversa(criar_raiz, toml="[auto_melhoria]\nativa = false\n")
    "".join(conversa.perguntar("oi"))
    assert conversa.observador is None
    assert not caminho_do_banco(roteador.config.pasta_dados).exists()


# --- fechamento do dia, relatório e decisões (P2) ------------------------------------------------


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
    _eventos(m, "resposta", "local (qwen3.5:9b)", n=3, duracao_ms=4000)  # lentas
    _eventos(m, "resposta", "local (qwen3.5:9b)", n=5, duracao_ms=500)  # rápidas: normais
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=1)  # uma vez só: não vira proposta
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
    assert "Fontes:** nenhuma" in texto  # sem internet

    # no dia seguinte, o mesmo problema atualiza a mesma proposta (sem duplicar)
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
    assert m.dia_a_fechar(DIA) is None  # primeiro uso, sem eventos: só marca o começo
    _eventos(m, n=3, quando=DIA)
    assert m.dia_a_fechar(DIA.replace(hour=19)) is None  # antes da hora: nada
    noite = DIA.replace(hour=20, minute=5)
    assert m.dia_a_fechar(noite) == DIA.date()
    m.fechar(DIA.date(), noite)
    assert m.dia_a_fechar(noite + timedelta(minutes=30)) is None  # um por dia

    # o PC ficou desligado no dia 4 às 20:00; no dia 5 de manhã, sai o relatório do dia 4
    _eventos(m, n=3, quando=DIA + timedelta(days=1))
    manha_dia_5 = DIA + timedelta(days=2, hours=-2)
    assert m.dia_a_fechar(manha_dia_5) == date(2026, 11, 4)
    perdido = m.fechar(date(2026, 11, 4), manha_dia_5)
    assert perdido.eventos == 3  # só os eventos depois do fechamento anterior
    assert m.dia_a_fechar(manha_dia_5) is None
    assert [d for d, _, _ in m.nao_mostrados()] == ["2026-11-03", "2026-11-04"]
    assert m.nao_mostrados() == []  # mostrados só uma vez


def test_agendador_espera_a_nora_desocupada_e_avisa(criar_raiz):
    m = _melhorias(criar_raiz)
    _eventos(m, n=3)
    fechados, ocupada = [], [True]
    noite = DIA.replace(hour=21)
    agendador = Agendador(m, lambda: ocupada[0], fechados.append, relogio=lambda: noite)
    assert agendador.conferir() is None and fechados == []  # respondendo ou no modo jogo
    ocupada[0] = False
    assert agendador.conferir() is not None and len(fechados) == 1
    assert agendador.conferir() is None  # não repete


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
    assert m.decidir(ids["erro_provedor"], "recusar", "teste") is None  # já decidida
    assert m.avancar(aprovada.id, "publicada", "teste") is None  # pulando etapas
    for estado in ("preparacao", "em_teste", "pronta_para_revisao"):
        assert m.avancar(aprovada.id, estado, "teste").status == estado
    assert m.avancar(aprovada.id, "publicada", "teste") is None  # sem autorização
    assert m.avancar(aprovada.id, "publicada", "teste", autorizo_publicar=True)
    assert [a for _, a, _, _ in m.decisoes(aprovada.id)][0] == "aprovar"

    m.decidir(ids["timeout"], "recusar", "teste")
    m.decidir(ids["resposta_vazia"], "adiar", "teste", dias=3)
    dia2 = DIA + timedelta(days=1)
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=4, quando=dia2)  # pouca coisa nova
    _eventos(m, "resposta_vazia", "ChatGPT (gpt-5.5)", n=3, quando=dia2)
    f2 = m.fechar(dia2.date(), dia2 + timedelta(hours=10))
    assert f2.novas == []  # recusada sem evidência nova e adiada não voltam
    dia5 = DIA + timedelta(days=5)
    _eventos(m, "timeout", "Claude Sonnet 5.5", n=8, quando=dia5)  # o dobro: evidência nova
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
    assert pedido_de_melhoria("aprova isso") is None  # sem "melhoria"

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
    assert roteador.local.pedidos == []  # nada disso passou pelo cérebro


def test_inicio_da_sessao_mostra_o_relatorio_novo(criar_raiz):
    from nora.melhorias import iniciar

    conversa, _ = _conversa(criar_raiz)
    _eventos(conversa.melhorias, n=3)
    conversa.melhorias.fechar(DIA.date(), DIA + timedelta(hours=10))
    linhas = []
    agendador = iniciar(conversa, linhas.append)
    agendador.parar()
    assert any("Relatório de 03/11: 1 proposta(s)" in linha for linha in linhas)
