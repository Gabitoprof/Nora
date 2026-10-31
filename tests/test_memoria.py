import hashlib
import io
import json
import math
import re

import pytest
from fake_servico import ServicoFalso

from nora.cli import main
from nora.config import carregar
from nora.conversa import conversar, nova_conversa
from nora.curadoria import extrair_fatos
from nora.embeddings import EmbeddingsOllama
from nora.memoria import Memoria

DIMENSAO = 256


def vetor_de(texto):
    """Embedding falso: saco de palavras com hash. Textos com palavras em comum ficam perto."""
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
    """Ollama falso: /api/embed com vetores falsos, /api/chat respondendo em streaming ou,
    quando pedem JSON (curadoria), devolvendo os fatos combinados."""

    def __init__(self, resposta="Anotado!", fatos=()):
        self.conversas = []
        self.fatos = list(fatos)

        def responder(caminho, cabecalhos, corpo):
            pedido = json.loads(corpo)
            if caminho == "/api/embed":
                vetores = [vetor_de(t) for t in pedido["input"]]
                return 200, "application/json", json.dumps({"embeddings": vetores}).encode()
            if pedido.get("format") == "json":
                conteudo = json.dumps({"fatos": self.fatos})
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
    id_aniversario, novo = memoria.lembrar("Gabriel faz aniversário em 31 de outubro")
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
    with OllamaComMemoria(fatos=["Gabriel faz aniversário em 31 de outubro", "  ", 7]) as ollama:
        config = carregar(criar_raiz(), ambiente={"OLLAMA_HOST": ollama.url})
        vetores = EmbeddingsOllama(config).vetores(["oi", "tchau"])
        fatos = extrair_fatos(config, "amanhã é meu aniversário", "Parabéns!", "30/10/2026")
    assert len(vetores) == 2 and len(vetores[0]) == DIMENSAO
    assert fatos == ["Gabriel faz aniversário em 31 de outubro"]  # sem vazios nem não-texto
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
    """O critério da v0.2.0: um fato dito numa conversa é lembrado numa conversa nova."""
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
    assert len(notas) == 2  # a persona e a nota da memória
    assert fato in notas[1]
    assert enviado[-1] == {"role": "user", "content": "Quando é a minha prova de cálculo?"}
    assert [f.texto for f in segunda.lembrancas] == [fato]
    # a nota da memória não fica guardada na conversa, só é enviada
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
        conversa.memoria.contar = lambda: 1  # finge que já há fatos, para tentar buscar
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
        assert main(["memoria", "importar"]) == 0  # de novo: nada pendente
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
    assert "Página" not in texto  # só uma página
    assert "Esquecido (nº 1)." in texto


def test_persona_sabe_que_tem_memoria(criar_raiz):
    from nora.persona import prompt_de_sistema

    com = carregar(criar_raiz(local="[memoria]\nativa = true\n"), ambiente={})
    sem = carregar(criar_raiz(local="[memoria]\nativa = false\n"), ambiente={})
    assert "Você tem memória de conversas anteriores" in prompt_de_sistema(com)
    assert "Você tem memória" not in prompt_de_sistema(sem)


def test_listar_em_paginas_e_com_filtro(memoria):
    # cada fato com uma palavra própria, para nenhum ser confundido com outro e juntado
    for numero in range(25):
        assunto = "cachorro" if numero % 5 == 0 else "assunto"
        memoria.lembrar(f"Gabriel anotou item{numero:02d} sobre {assunto}")
    assert memoria.contar() == 25
    primeira = memoria.listar(limite=20)
    assert len(primeira) == 20
    assert primeira[0].texto == "Gabriel anotou item24 sobre assunto"  # o mais recente
    assert len(memoria.listar(limite=20, pular=20)) == 5
    assert len(memoria.listar()) == 25
    com_cachorro = memoria.listar(contendo="cachorro")
    assert [f.texto for f in com_cachorro][-1] == "Gabriel anotou item00 sobre cachorro"
    assert memoria.contar_contendo("cachorro") == 5
