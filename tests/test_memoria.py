import hashlib
import io
import json
import math
import re
from datetime import date

import pytest
from fake_servico import ServicoFalso

from nora.cli import main
from nora.config import carregar
from nora.conversa import conversar, nova_conversa
from nora.curadoria import FatoExtraido, extrair_fatos
from nora.embeddings import EmbeddingsOllama
from nora.memoria import Memoria

DIMENSAO = 256


def vetor_de(texto):
    """Fake embedding: a hashed bag of words. Texts with words in common end up close."""
    vetor = [0.0] * DIMENSAO
    for palavra in re.findall(r"\w+", texto.lower()):
        if len(palavra) > 2:
            vetor[int(hashlib.md5(palavra.encode()).hexdigest(), 16) % DIMENSAO] += 1.0
    norma = math.sqrt(sum(x * x for x in vetor)) or 1.0
    return [x / norma for x in vetor]


class EmbeddingsFalsos:
    def vetor(self, texto):
        return vetor_de(texto)


class OllamaComMemoria(ServicoFalso):
    """Fake Ollama: /api/embed with fake vectors, /api/chat answering as a stream or, when JSON is
    requested (curation), returning the agreed facts."""

    def __init__(self, resposta="Anotado!", fatos=()):
        self.conversas = []
        self.fatos = list(fatos)
        self.extras = {}  # other curation keys (pronuncias, preferencias)

        def responder(caminho, cabecalhos, corpo):
            pedido = json.loads(corpo)
            if caminho == "/api/embed":
                vetores = [vetor_de(t) for t in pedido["input"]]
                return 200, "application/json", json.dumps({"embeddings": vetores}).encode()
            if pedido.get("format") == "json":
                conteudo = json.dumps({"fatos": self.fatos, **self.extras})
                return (
                    200,
                    "application/json",
                    json.dumps({"message": {"content": conteudo}}).encode(),
                )
            self.conversas.append(pedido)
            linhas = [
                {"message": {"content": resposta}, "done": False},
                {"message": {"content": ""}, "done": True, "eval_count": 3, "eval_duration": 10**8},
            ]
            return 200, "application/x-ndjson", b"\n".join(json.dumps(x).encode() for x in linhas)

        super().__init__(responder)


@pytest.fixture(params=[True, False], ids=["sqlite-vec", "python"])
def memoria(tmp_path, request):
    m = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    if not request.param:
        m.vetorial = False
    elif not m.vetorial:
        pytest.skip("sqlite-vec não instalado")
    yield m
    m.fechar()


def test_lembra_busca_e_esquece(memoria):
    id_aniversario, novo = memoria.lembrar("Gabriel faz aniversário em 12 de março")
    assert novo
    memoria.lembrar("Gabriel tem prova de cálculo na sexta-feira")
    memoria.lembrar("Gabriel gosta de café sem açúcar")
    achados = memoria.buscar("quando é o aniversário do Gabriel?", k=2)
    assert achados[0].id == id_aniversario
    assert achados[0].similaridade > achados[1].similaridade
    assert memoria.buscar("aniversário", k=5, minimo=0.99) == []
    assert memoria.esquecer(id_aniversario)
    assert not memoria.esquecer(id_aniversario)
    assert [f.texto for f in memoria.listar()] == [
        "Gabriel gosta de café sem açúcar",
        "Gabriel tem prova de cálculo na sexta-feira",
    ]


def test_fato_repetido_atualiza_em_vez_de_duplicar(memoria):
    primeiro, _ = memoria.lembrar("Gabriel   gosta de café sem açúcar")
    segundo, novo = memoria.lembrar("Gabriel gosta de café sem açúcar")
    assert (segundo, novo) == (primeiro, False)
    assert memoria.contar() == 1
    assert memoria.listar()[0].texto == "Gabriel gosta de café sem açúcar"


def test_memoria_persiste_no_arquivo(tmp_path):
    caminho = tmp_path / "memoria.db"
    m = Memoria(caminho, EmbeddingsFalsos())
    m.lembrar("Gabriel mora em Salvador")
    m.fechar()
    reaberta = Memoria(caminho, EmbeddingsFalsos())
    assert reaberta.buscar("onde Gabriel mora?")[0].texto == "Gabriel mora em Salvador"
    reaberta.fechar()


def test_embeddings_e_curadoria_pelo_ollama(criar_raiz):
    with OllamaComMemoria(fatos=["Gabriel faz aniversário em 12 de março", "  ", 7]) as ollama:
        config = carregar(criar_raiz(), ambiente={"OLLAMA_HOST": ollama.url})
        vetores = EmbeddingsOllama(config).vetores(["oi", "tchau"])
        fatos = extrair_fatos(config, "amanhã é meu aniversário", "Parabéns!", "30/10/2026")
    assert len(vetores) == 2 and len(vetores[0]) == DIMENSAO
    # the old format (plain text) is still accepted, without an area; empty and non-text are
    # dropped; the date written in the text becomes an agenda date (birthday: every year)
    assert fatos == [
        FatoExtraido("Gabriel faz aniversário em 12 de março", "", date(2027, 3, 12), True)
    ]
    embed = json.loads(ollama.pedidos[0][2])
    assert embed["model"] == "bge-m3"
    curadoria = json.loads(ollama.pedidos[1][2])
    assert curadoria["format"] == "json" and curadoria["think"] is False
    assert "30/10/2026" in curadoria["messages"][0]["content"]


def test_curadoria_com_json_quebrado_devolve_nada(criar_raiz):
    def quebrado(*_):
        return 200, "application/json", json.dumps({"message": {"content": "{fatos:"}}).encode()

    with ServicoFalso(quebrado) as ollama:
        config = carregar(criar_raiz(), ambiente={"OLLAMA_HOST": ollama.url})
        assert extrair_fatos(config, "oi", "oi", "30/10/2026") == []


def test_lembra_entre_sessoes(criar_raiz):
    """The v0.2.0 criterion: a fact said in one conversation is remembered in a new conversation."""
    local = '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\nsimilaridade_minima = 0.2\n'
    fato = "Gabriel tem prova de cálculo na sexta-feira"
    with OllamaComMemoria(fatos=[fato]) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})

        primeira = nova_conversa(config)
        assert "".join(primeira.perguntar("Minha prova de cálculo é sexta.")) == "Anotado!"
        assert primeira.encerrar() == [f"anotei: {fato}"]
        primeira.memoria.fechar()

        segunda = nova_conversa(config)
        ollama.fatos = []
        "".join(segunda.perguntar("Quando é a minha prova de cálculo?"))
        segunda.encerrar()
        segunda.memoria.fechar()

    enviado = ollama.conversas[-1]["messages"]
    notas = [m["content"] for m in enviado if m["role"] == "system"]
    assert len(notas) == 2  # the persona and the memory note
    assert fato in notas[1]
    assert enviado[-1] == {"role": "user", "content": "Quando é a minha prova de cálculo?"}
    assert [f.texto for f in segunda.lembrancas] == [fato]
    # the memory note is not kept in the conversation, it is only sent
    assert all(fato not in m["content"] for m in segunda.mensagens)


def test_sem_modelo_de_embeddings_a_conversa_segue(criar_raiz):
    def sem_embed(caminho, cabecalhos, corpo):
        if caminho == "/api/embed":
            return 404, "application/json", b'{"error":"model \\"bge-m3\\" not found"}'
        linha = {"message": {"content": "Oi!"}, "done": True}
        return 200, "application/x-ndjson", json.dumps(linha).encode()

    local = "[memoria]\nativa = true\ncuradoria = false\n"
    with ServicoFalso(sem_embed) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        conversa = nova_conversa(config)
        conversa.memoria.lembrar = lambda *a, **k: (1, True)
        conversa.memoria.contar = lambda: 1  # pretend there are facts already, to try searching
        assert "".join(conversa.perguntar("oi")) == "Oi!"
    assert "ollama pull bge-m3" in conversa.avisos_pendentes()[0]


def test_conversar_mostra_aviso_e_contagem(criar_raiz):
    local = "[memoria]\nativa = true\nsimilaridade_minima = 0.2\n"
    with OllamaComMemoria(fatos=["Gabriel gosta de café"]) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        falas = iter(["eu gosto de café", "sair"])
        saida = io.StringIO()
        conversar(config, entrada=lambda _: next(falas), saida=saida, medir=True)
    texto = saida.getvalue()
    assert "lembrou 0 fatos" in texto
    assert "[memória] anotei: Gabriel gosta de café" in texto
    assert "(guardando o que aprendi nesta conversa...)" in texto


def test_comando_memoria_e_importar(criar_raiz, capsys, monkeypatch):
    local = '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\n'
    with OllamaComMemoria(fatos=["Gabriel vai viajar para Itaparica"]) as ollama:
        raiz = criar_raiz(local=local)
        historico = raiz / "data" / "historico"
        historico.mkdir(parents=True)
        registros = [
            {"quando": "2026-10-30T10:00:00", "papel": "usuario", "texto": "vou viajar"},
            {"quando": "2026-10-30T10:00:05", "papel": "assistente", "texto": "Boa viagem!"},
        ]
        (historico / "2026-10-30.jsonl").write_text(
            "\n".join(json.dumps(r) for r in registros) + "\nlixo\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            "nora.cli.carregar", lambda: carregar(raiz, ambiente={"OLLAMA_HOST": ollama.url})
        )
        assert main(["memoria", "importar"]) == 0
        assert main(["memoria", "importar"]) == 0  # again: nothing pending
        assert main(["memoria", "lembrar", "Gabriel", "prefere", "chá"]) == 0
        assert main(["memoria", "listar"]) == 0
        assert main(["memoria", "esquecer", "1"]) == 0
        assert main(["memoria", "esquecer", "99"]) == 1
    texto = capsys.readouterr().out
    assert "1 trocas para ler" in texto
    assert "+ Gabriel vai viajar para Itaparica" in texto
    assert "0 trocas para ler" in texto
    assert "Guardado" in texto
    assert "2 fatos em" in texto
    assert "Página" not in texto  # only one page
    assert "Esquecido (nº 1)." in texto
    assert "1 trocas guardadas" in texto


def test_persona_sabe_que_tem_memoria(criar_raiz):
    from nora.persona import prompt_de_sistema

    com = carregar(criar_raiz(local="[memoria]\nativa = true\n"), ambiente={})
    sem = carregar(criar_raiz(local="[memoria]\nativa = false\n"), ambiente={})
    assert "Você tem memória de conversas anteriores" in prompt_de_sistema(com)
    assert "Você tem memória" not in prompt_de_sistema(sem)


def test_listar_em_paginas_e_com_filtro(memoria):
    # each fact with its own word, so none is mistaken for another and merged
    for numero in range(25):
        assunto = "cachorro" if numero % 5 == 0 else "assunto"
        memoria.lembrar(f"Gabriel anotou item{numero:02d} sobre {assunto}")
    assert memoria.contar() == 25
    primeira = memoria.listar(limite=20)
    assert len(primeira) == 20
    assert primeira[0].texto == "Gabriel anotou item24 sobre assunto"  # the most recent
    assert len(memoria.listar(limite=20, pular=20)) == 5
    assert len(memoria.listar()) == 25
    com_cachorro = memoria.listar(contendo="cachorro")
    assert [f.texto for f in com_cachorro][-1] == "Gabriel anotou item00 sobre cachorro"
    assert memoria.contar_contendo("cachorro") == 5


def test_lembra_de_tudo_mesmo_sem_fato_anotado(criar_raiz):
    """Total memory: the whole exchange is kept and comes back in a new conversation, even when
    curation finds no fact to note."""
    local = (
        '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\nsimilaridade_minima = 0.2\n'
        "fatos_por_pergunta = 0\n"
    )
    with OllamaComMemoria(resposta="Que alívio que você achou!", fatos=[]) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        primeira = nova_conversa(config)
        "".join(primeira.perguntar("achei meu gato embaixo da escada"))
        primeira.encerrar()
        assert primeira.memoria.contar() == 0  # no fact noted...
        assert primeira.memoria.contar_trocas() == 1  # ...but the exchange was kept
        primeira.memoria.fechar()

        segunda = nova_conversa(config)
        "".join(segunda.perguntar("onde eu achei o meu gato?"))
        segunda.encerrar()
        segunda.memoria.fechar()

    nota = [m["content"] for m in ollama.conversas[-1]["messages"] if m["role"] == "system"][1]
    assert "Trechos dessas conversas:" in nota
    assert 'Gabriel disse: "achei meu gato embaixo da escada"' in nota
    assert 'você respondeu: "Que alívio que você achou!"' in nota
    assert len(segunda.trechos) == 1


def test_trechos_da_propria_sessao_nao_voltam(memoria):
    memoria.guardar_troca("meu cachorro fugiu", "Que susto!", "2026-10-30T10:00:00", "sessao-a")
    memoria.guardar_troca("meu cachorro voltou", "Que bom!", "2026-10-30T10:05:00", "sessao-b")
    achados = memoria.buscar_trocas("cachorro", k=5, exceto_sessao="sessao-b")
    assert [t.pergunta for t in achados] == ["meu cachorro fugiu"]
    assert achados[0].quando == "2026-10-30T10:00:00"


def test_banco_antigo_ganha_a_tabela_de_trocas(tmp_path):
    caminho = tmp_path / "memoria.db"
    antiga = Memoria(caminho, EmbeddingsFalsos())
    if not antiga.vetorial:
        pytest.skip("sqlite-vec não instalado")
    antiga.lembrar("Gabriel tem prova em 21/11")
    antiga._db.execute("DROP TABLE vec_trocas")  # as it was before this version
    antiga._db.commit()
    antiga.fechar()

    nova = Memoria(caminho, EmbeddingsFalsos())
    nova.guardar_troca("oi", "olá", "2026-10-31T09:00:00", "s")
    assert nova.buscar_trocas("oi")[0].resposta == "olá"
    assert nova.buscar("prova")[0].texto == "Gabriel tem prova em 21/11"
    nova.fechar()


def test_curadoria_com_areas(criar_raiz):
    fatos = [
        {"texto": "Gabriel toma remédio para pressão", "area": "Saúde"},
        {"texto": "Gabriel trabalha com design", "area": " trabalho "},
        {"area": "sem texto"},
    ]

    def ollama(caminho, cabecalhos, corpo):
        conteudo = json.dumps({"fatos": fatos})
        return 200, "application/json", json.dumps({"message": {"content": conteudo}}).encode()

    with ServicoFalso(ollama) as servidor:
        config = carregar(criar_raiz(), ambiente={"OLLAMA_HOST": servidor.url})
        achados = extrair_fatos(config, "oi", "oi", "31/10/2026", areas=["saúde", "estudos"])
    assert [(f.texto, f.area) for f in achados] == [
        ("Gabriel toma remédio para pressão", "Saúde"),
        ("Gabriel trabalha com design", "trabalho"),
    ]
    instrucao = json.loads(servidor.pedidos[0][2])["messages"][0]["content"]
    assert "Áreas que já existem: saúde, estudos." in instrucao


def test_areas_na_memoria(memoria):
    memoria.lembrar("Gabriel toma remédio para pressão", area="Saúde")
    memoria.lembrar("Gabriel faz fisioterapia às terças", area="saude")  # same area
    memoria.lembrar("Gabriel trabalha com design", area="trabalho")
    memoria.lembrar("Gabriel gosta de café")  # no area
    assert memoria.areas() == [("saúde", 2), ("trabalho", 1)]
    assert [f.texto for f in memoria.listar(area="SAUDE")] == [
        "Gabriel faz fisioterapia às terças",
        "Gabriel toma remédio para pressão",
    ]
    assert memoria.contar_contendo(area="trabalho") == 1
    assert memoria.buscar("design")[0].area == "trabalho"
    # updating a fact without an area does not erase the area it already had
    memoria.lembrar("Gabriel trabalha com design")
    assert memoria.areas() == [("saúde", 2), ("trabalho", 1)]


def test_banco_antigo_ganha_a_coluna_de_area(tmp_path):
    import sqlite3

    caminho = tmp_path / "memoria.db"
    banco = sqlite3.connect(caminho)
    banco.executescript(
        "CREATE TABLE fatos (id INTEGER PRIMARY KEY, texto TEXT NOT NULL, vetor BLOB NOT NULL,"
        " criado TEXT NOT NULL, atualizado TEXT NOT NULL, origem TEXT NOT NULL DEFAULT '');"
    )
    banco.close()
    memoria = Memoria(caminho, EmbeddingsFalsos())
    memoria.lembrar("Gabriel estuda na PUC Minas", area="estudos")
    assert memoria.areas() == [("estudos", 1)]
    memoria.fechar()


def test_comando_areas(criar_raiz, capsys, monkeypatch):
    with OllamaComMemoria() as ollama:
        raiz = criar_raiz(local="[memoria]\nativa = true\n")
        monkeypatch.setattr(
            "nora.cli.carregar", lambda: carregar(raiz, ambiente={"OLLAMA_HOST": ollama.url})
        )
        assert main(["memoria", "lembrar", "Gabriel", "corre", "às", "6h", "--area", "Saúde"]) == 0
        assert main(["memoria", "lembrar", "Gabriel", "gosta", "de", "chá"]) == 0
        assert main(["memoria", "areas"]) == 0
        assert main(["memoria", "listar", "--area", "saude"]) == 0
    texto = capsys.readouterr().out
    assert "1 áreas:" in texto
    assert "saúde" in texto and "(sem área)" in texto
    assert "1 fatos na área saúde" in texto
    assert "[saúde] Gabriel corre às 6h" in texto


# --- forget and delete for good (v0.3.0 closing report, A2) -------------------------------------

PROVA = "Ana tem prova de cálculo no dia 21"
PERGUNTA = "Ana tem prova de cálculo no dia 21, me ajuda?"
RESPOSTA = "Claro! A prova de cálculo do dia 21 vai dar certo."
PIZZA = ("Gosto de pizza de calabresa", "Pizza de calabresa é ótima!")


def _com_prova(m):
    m.lembrar(PROVA)
    m.guardar_troca(PERGUNTA, RESPOSTA, "2026-11-01T10:00:00", "antiga")
    m.guardar_troca(*PIZZA, "2026-11-01T10:05:00", "antiga")


def test_esquecido_nao_volta_pelas_conversas_nem_depois_de_reiniciar(memoria):
    _com_prova(memoria)
    # before: the passage comes back
    assert memoria.buscar_trocas("prova de cálculo dia 21", minimo=0.3)
    assert memoria.esquecer_parecido(PROVA)
    assert memoria.buscar("prova de cálculo dia 21", minimo=0.3) == []
    # the old passage does not come back
    assert memoria.buscar_trocas("prova de cálculo dia 21", minimo=0.3) == []
    assert memoria.buscar_trocas("pizza de calabresa", minimo=0.3)  # the rest stays

    caminho, vetorial = memoria.caminho, memoria.vetorial
    memoria.fechar()
    reaberta = Memoria(caminho, EmbeddingsFalsos())
    reaberta.vetorial = reaberta.vetorial and vetorial
    assert reaberta.buscar_trocas("prova de cálculo dia 21", minimo=0.3) == []
    # importing old conversations does not bring the fact back
    assert reaberta.lembrar(PROVA, origem="historico 2026-11-01") == (0, False)
    assert reaberta.contar() == 0
    # but if the person tells it again, in a new conversation, she remembers it again
    _, novo = reaberta.lembrar(PROVA, origem="2026-11-05_10-00-00")
    assert novo and reaberta.contar() == 1
    reaberta.fechar()


def test_apagar_de_vez_mostra_antes_e_apaga_tambem_o_historico(tmp_path):
    from nora.historico import Historico, apagar_do_historico
    from nora.importar import trocas

    historico = Historico(tmp_path, sessao="2026-11-01_10-00-00")
    for pergunta, resposta in [(PERGUNTA, RESPOSTA), PIZZA]:
        historico.registrar("usuario", pergunta)
        historico.registrar("assistente", resposta)
    m = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    _com_prova(m)

    previa = m.apagar_de_vez(PROVA, confirmar=False)  # only shows what would go
    assert [f.texto for f in previa.fatos] == [PROVA]
    assert [t.pergunta for t in previa.trocas] == [PERGUNTA]
    assert m.contar() == 1 and m.contar_trocas() == 2

    feito = m.apagar_de_vez(PROVA, confirmar=True)
    assert m.contar() == 0 and m.contar_trocas() == 1
    assert apagar_do_historico(tmp_path, feito.textos) == 2
    conteudo = historico.arquivo.read_text("utf-8")
    assert "cálculo" not in conteudo and "calabresa" in conteudo
    assert [t[2] for t in trocas(historico.arquivo)] == [PIZZA[0]]  # import skips the deleted one
    m.fechar()


def test_comando_apagar_mostra_e_so_apaga_com_confirmar(criar_raiz, capsys, monkeypatch):
    from nora import cli
    from nora.historico import Historico

    raiz = criar_raiz(local="[memoria]\nativa = true\ncuradoria = false\n")
    config = cli.carregar(raiz, ambiente={})
    historico = Historico(config.pasta_dados, sessao="2026-11-01_10-00-00")
    historico.registrar("usuario", PERGUNTA)
    historico.registrar("assistente", RESPOSTA)
    m = Memoria(config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    _com_prova(m)
    m.fechar()
    monkeypatch.setattr("nora.embeddings.EmbeddingsOllama.vetor", lambda self, t: vetor_de(t))
    monkeypatch.setattr(cli, "carregar", lambda *a, **k: config)

    assert cli.main(["memoria", "apagar", PROVA]) == 0
    saida = capsys.readouterr().out
    assert "Seria apagado" in saida and "--confirmar" in saida
    assert "cálculo" in historico.arquivo.read_text("utf-8")

    assert cli.main(["memoria", "apagar", PROVA, "--confirmar"]) == 0
    assert "Também tirei 2 fala(s)" in capsys.readouterr().out
    assert "cálculo" not in historico.arquivo.read_text("utf-8")


# --- delete for good in conversation (with confirmation) -----------------------------------------


class CerebroAnotador:
    """Fake brain that only answers normal questions (the delete request does not reach it)."""

    def __init__(self):
        from nora.cerebro import Medidas

        self.medidas, self.pedidos = Medidas(), []

    def aquecer(self):
        return 0.0

    def responder(self, mensagens):
        self.pedidos.append(mensagens[-1]["content"])
        yield "Paris."


def _conversa_com_prova(criar_raiz):
    from nora.conversa import nova_conversa
    from nora.historico import Historico

    config = carregar(criar_raiz(local="[memoria]\nativa = true\ncuradoria = false\n"), ambiente={})
    antiga = Historico(config.pasta_dados, sessao="2026-11-01_10-00-00")
    antiga.registrar("usuario", PERGUNTA)
    antiga.registrar("assistente", RESPOSTA)
    m = Memoria(config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    _com_prova(m)
    cerebro = CerebroAnotador()
    conversa = nova_conversa(config, cerebro, memoria=m, notas=None)
    return conversa, m, cerebro, antiga


def test_apagar_de_vez_pela_conversa_pede_confirmacao(criar_raiz):
    from nora.conversa import confirmacao, pedido_de_apagar

    assert pedido_de_apagar("Nora, apaga de vez a prova de cálculo") == "a prova de cálculo"
    assert pedido_de_apagar("apaga a prova de cálculo para sempre") == "a prova de cálculo"
    assert pedido_de_apagar("apaga tudo sobre a viagem") == "a viagem"
    assert pedido_de_apagar("apaga isso de vez") == ""  # no subject: she asks which
    assert pedido_de_apagar("esquece que eu falei da viagem") is None  # this is just forgetting
    assert pedido_de_apagar("apaga a luz") is None
    assert confirmacao("sim, pode apagar para sempre") == "sim"
    assert confirmacao("Nora, não!") == "nao" and confirmacao("qual a capital?") is None

    conversa, m, cerebro, antiga = _conversa_com_prova(criar_raiz)
    resposta = "".join(conversa.perguntar("Nora, apaga de vez a prova de cálculo do dia 21"))
    assert "1 fato e 1 trecho de conversa" in resposta and "sim, pode apagar" in resposta
    assert m.contar() == 1 and cerebro.pedidos == []  # nothing deleted yet; brain not called
    assert any("apagaria" in aviso for aviso in conversa.avisos_pendentes())

    resposta = "".join(conversa.perguntar("sim, pode apagar"))
    assert "apaguei de vez" in resposta.lower()
    assert m.contar() == 0 and m.contar_trocas() == 1
    assert "cálculo" not in antiga.arquivo.read_text("utf-8")
    # not even the request itself
    assert "cálculo" not in conversa.historico.arquivo.read_text("utf-8")
    assert cerebro.pedidos == []


def test_apagar_de_vez_pela_conversa_cancela_e_expira(criar_raiz):
    conversa, m, cerebro, _ = _conversa_com_prova(criar_raiz)
    "".join(conversa.perguntar("apaga de vez a prova de cálculo do dia 21"))
    assert "não apaguei" in "".join(conversa.perguntar("não, deixa")).lower()
    assert m.contar() == 1

    "".join(conversa.perguntar("apaga de vez a prova de cálculo do dia 21"))
    # changed the subject
    assert "".join(conversa.perguntar("qual a capital da França?")) == "Paris."
    assert "".join(conversa.perguntar("sim")) == "Paris."  # the request has already expired
    assert m.contar() == 1

    resposta = "".join(conversa.perguntar("apaga isso de vez"))
    assert "o quê" in resposta.lower() and m.contar() == 1
    assert "Não achei" in "".join(conversa.perguntar("apaga de vez o cachorro do vizinho"))


# --- pending answers (A5 of the consolidated review) ---------------------------------------------


def _conversa_com_roteador(criar_raiz, local, cliente=None):
    from test_roteador import montar

    from nora.conversa import nova_conversa

    toml = "[memoria]\nativa = true\ncuradoria = false\n[roteador]\nescalar = false\n"
    roteador, _ = montar(criar_raiz, local=local, cliente=cliente, toml=toml)
    m = Memoria(roteador.config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    return nova_conversa(roteador.config, roteador, memoria=m, notas=None), m, roteador


def test_resposta_interrompida_vira_pendencia_que_sobrevive_e_e_retomada(criar_raiz):
    from test_roteador import LocalFalso

    local = LocalFalso(resposta="Uma resposta comprida do local.", cair_depois=2)
    conversa, m, roteador = _conversa_com_roteador(criar_raiz, local)
    assert "".join(conversa.perguntar("me explica a fotossíntese")) == "Uma re"
    conversa.esperar_memoria()
    pendentes = m.pendentes()
    # the partial answer becomes neither an exchange nor a fact
    assert len(pendentes) == 1 and m.contar_trocas() == 0
    p = pendentes[0]
    assert (p.pergunta, p.parcial, p.motivo) == (
        "me explica a fotossíntese",
        "Uma re",
        "stream_interrompido",
    )
    assert p.provedor.startswith("local")

    # survives a restart
    caminho = m.caminho
    m.fechar()
    m = Memoria(caminho, EmbeddingsFalsos())
    assert [x.pergunta for x in m.pendentes()] == ["me explica a fotossíntese"]

    # resumption: a new whole, labeled answer that closes the pending item
    conversa.memoria = m
    roteador.local = LocalFalso(resposta="A fotossíntese transforma luz em energia.")
    resposta = "".join(conversa.perguntar("termina a resposta que ficou pela metade"))
    assert resposta.startswith("Retomando") and resposta.endswith("energia.")
    conversa.esperar_memoria()
    assert m.pendentes() == [] and m.contar_trocas() == 1
    assert "".join(conversa.perguntar("termina a resposta que ficou pela metade")).startswith(
        "Não tenho"
    )


def test_respostas_completas_e_comandos_nao_geram_pendencia(criar_raiz):
    """And curadoria = false still stores the complete exchange."""
    from test_roteador import LocalFalso

    conversa, m, _ = _conversa_com_roteador(criar_raiz, LocalFalso())
    "".join(conversa.perguntar("oi, tudo bem?"))
    "".join(conversa.perguntar("modo jogo"))
    conversa.esperar_memoria()
    assert m.pendentes() == [] and m.contar_trocas() == 1  # the command is not an exchange either
    assert '"situacao": "comando"' in conversa.historico.arquivo.read_text("utf-8")


def test_pendencia_de_cancelamento_e_de_queda_do_programa(criar_raiz):
    from test_roteador import LocalFalso

    conversa, m, _ = _conversa_com_roteador(criar_raiz, LocalFalso(resposta="Resposta bem longa."))
    fluxo = conversa.perguntar("conta uma história")
    next(fluxo)
    fluxo.close()  # the person interrupted (Ctrl+C) while she was speaking
    assert [p.motivo for p in m.pendentes()] == ["cancelada"]

    # the program crashed in the middle of an answer: next time, it becomes a pending item
    m.abrir_resposta("caiu-123", "sessao-antiga", "qual a distância da Lua?")
    assert len(m.pendentes()) == 1  # open is not pending yet
    assert m.recuperar_abertas(exceto_sessao="sessao-nova") == 1
    assert m.recuperar_abertas(exceto_sessao="sessao-nova") == 0  # without duplicating
    assert sorted(p.motivo for p in m.pendentes()) == ["cancelada", "encerramento"]

    # cancel and delete for good
    historia = next(p for p in m.pendentes() if p.pergunta == "conta uma história")
    assert m.cancelar_pendencia(historia.id) and not m.cancelar_pendencia(historia.id)
    assert len(m.pendentes()) == 1
    m.apagar_de_vez("qual a distância da Lua?", confirmar=True)
    assert m.pendentes() == []


def test_comando_pendencias_lista_e_cancela(criar_raiz, capsys, monkeypatch):
    from nora import cli

    raiz = criar_raiz(local="[memoria]\nativa = true\ncuradoria = false\n")
    config = cli.carregar(raiz, ambiente={})
    m = Memoria(config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    m.marcar_pendente(
        "x1", "s1", "qual a distância da Lua?", "São uns", "stream_interrompido", "local"
    )
    m.fechar()
    monkeypatch.setattr(cli, "carregar", lambda *a, **k: config)
    assert cli.main(["pendencias"]) == 0
    saida = capsys.readouterr().out
    assert "qual a distância da Lua?" in saida and 'saiu: "São uns"' in saida
    assert cli.main(["pendencias", "--cancelar", "1"]) == 0
    assert cli.main(["pendencias"]) == 0
    assert "Nenhuma resposta pela metade" in capsys.readouterr().out


class CerebroQueEhInterrompido:
    """Yields a chunk and then Ctrl+C arrives while she still waits for the rest (the
    KeyboardInterrupt is raised inside the generator, not outside it)."""

    def __init__(self):
        from nora.cerebro import Medidas

        self.medidas, self.origem = Medidas(), "local (qwen3.5:9b)"

    def aquecer(self):
        return 0.0

    def responder(self, mensagens):
        yield "Começo da "
        raise KeyboardInterrupt


def test_ctrl_c_no_meio_vira_pendencia_na_hora(criar_raiz):
    """Audit P0: a real Ctrl+C (KeyboardInterrupt inside the flow) stores the pending item right
    away, without waiting for another session, and nothing goes to curation."""
    from nora.conversa import nova_conversa

    config = carregar(criar_raiz(local="[memoria]\nativa = true\ncuradoria = false\n"), ambiente={})
    m = Memoria(config.pasta_dados / "memoria.db", EmbeddingsFalsos())
    conversa = nova_conversa(config, CerebroQueEhInterrompido(), memoria=m, notas=None)
    partes = []
    with pytest.raises(KeyboardInterrupt):
        for pedaco in conversa.perguntar("conta a história do Brasil"):
            partes.append(pedaco)
    assert partes == ["Começo da "]
    pendentes = m.pendentes()  # right away, in the same session
    assert [(p.pergunta, p.parcial, p.motivo) for p in pendentes] == [
        ("conta a história do Brasil", "Começo da", "cancelada")
    ]
    conversa.esperar_memoria()
    assert m.contar_trocas() == 0 and not conversa.ocupada
    historico = conversa.historico.arquivo.read_text("utf-8")
    assert historico.count('"situacao": "cancelada"') == 1  # only once, without duplicating


def test_busca_por_trecho_ignora_maiusculas_acentuadas_e_nao_usa_curingas(memoria):
    """Issue #3: LIKE only ignores ASCII case and treats _ and % as wildcards."""
    from datetime import date as Data

    memoria.marcar(Data(2026, 11, 21), "prova de álgebra", False, "estudos")
    memoria.marcar(Data(2026, 11, 22), "entregar prova 1", False, "estudos")
    memoria.marcar(Data(2026, 11, 23), "meta de 50 por cento", False, "trabalho")
    assert [e.texto for e in memoria.eventos_contendo("Álgebra")] == ["prova de álgebra"]
    assert memoria.eventos_contendo("prova_1") == []  # "_" is not a wildcard
    assert memoria.eventos_contendo("50%") == []  # neither is "%"
    memoria.lembrar("Ana estuda Álgebra Linear", area="estudos")
    memoria.lembrar("Meta de 50% no trimestre", area="trabalho")
    assert memoria.contar_contendo("álgebra") == 1
    assert [f.texto for f in memoria.listar(contendo="50%")] == ["Meta de 50% no trimestre"]
    assert memoria.contar_contendo("5_%") == 0
