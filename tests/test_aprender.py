"""Learning from conversation: corrected pronunciations and preferences about the way of
speaking."""

import json

from fake_servico import ServicoFalso
from test_memoria import EmbeddingsFalsos, OllamaComMemoria

from nora.cli import main
from nora.config import carregar
from nora.conversa import nova_conversa
from nora.curadoria import curar
from nora.memoria import Memoria
from nora.voz import com_pronuncias_aprendidas


class OllamaQueAprende(OllamaComMemoria):
    """Fake Ollama whose curation also returns pronunciations and preferences."""

    def __init__(self, pronuncias=(), preferencias=()):
        super().__init__()
        self.extras = {"pronuncias": list(pronuncias), "preferencias": list(preferencias)}


def test_curadoria_le_pronuncias_e_preferencias(criar_raiz):
    resposta = {
        "fatos": [],
        "pronuncias": [{"palavra": "hoje", "fala": "ôje"}, {"palavra": "x", "fala": "x"}, 3],
        "preferencias": ["Não repita a pergunta.", "  ", 7],
    }

    def ollama(*_):
        conteudo = json.dumps(resposta)
        return 200, "application/json", json.dumps({"message": {"content": conteudo}}).encode()

    with ServicoFalso(ollama) as servidor:
        config = carregar(criar_raiz(), ambiente={"OLLAMA_HOST": servidor.url})
        curadoria = curar(config, "você fala houje", "Desculpe!", "02/11/2026")
    assert curadoria.pronuncias == [("hoje", "ôje")]
    assert curadoria.preferencias == ["Não repita a pergunta."]
    instrucao = json.loads(servidor.pedidos[0][2])["messages"][0]["content"]
    assert '"pronuncias"' in instrucao and '"preferencias"' in instrucao
    assert "segunda" in instrucao  # weekday of 02/11/2026


def test_memoria_guarda_pronuncias_e_preferencias(tmp_path):
    memoria = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    assert memoria.ensinar_pronuncia("Hoje", "ôje")
    assert not memoria.ensinar_pronuncia("hoje", "ôji")  # updates, does not duplicate
    assert not memoria.ensinar_pronuncia("casa", "Casa")  # same: ignored
    assert memoria.pronuncias() == {"hoje": "ôji"}
    assert memoria.preferir("Seja mais direta.") == (1, True)
    assert memoria.preferir("Seja mais direta.") == (1, False)
    assert memoria.preferencias() == [(1, "Seja mais direta.")]
    assert memoria.esquecer_pronuncia("HOJE") and not memoria.esquecer_pronuncia("hoje")
    assert memoria.esquecer_preferencia(1) and not memoria.esquecer_preferencia(1)
    memoria.fechar()


def test_voz_usa_a_pronuncia_aprendida_na_hora(tmp_path):
    class VozFalsa:
        aviso = "a principal falhou"

        def __init__(self):
            self.textos = []

        def sintetizar(self, texto):
            self.textos.append(texto)
            return b"wav"

    memoria = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    interna = VozFalsa()
    voz = com_pronuncias_aprendidas(interna, memoria)
    voz.sintetizar("Hoje está bonito.")
    memoria.ensinar_pronuncia("hoje", "ôje")
    voz.sintetizar("Hoje está bonito.")
    assert interna.textos == ["Hoje está bonito.", "ôje está bonito."]
    assert voz.aviso == "a principal falhou"
    voz.aviso = ""  # the fallback notice is cleared on the inner voice
    assert interna.aviso == ""
    assert com_pronuncias_aprendidas(interna, None) is interna
    memoria.fechar()


def test_conversa_aprende_e_segue_as_preferencias(criar_raiz):
    local = '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\n'
    with OllamaQueAprende(
        pronuncias=[{"palavra": "hoje", "fala": "ôje"}],
        preferencias=["Não repita a pergunta antes de responder."],
    ) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        primeira = nova_conversa(config)
        "".join(primeira.perguntar("Não repete minha pergunta. E é ôje, não houje."))
        avisos = primeira.encerrar()
        primeira.memoria.fechar()

        ollama.extras = {}
        segunda = nova_conversa(config)
        "".join(segunda.perguntar("Que dia é hoje?"))
        segunda.encerrar()
        segunda.memoria.fechar()

    assert "aprendi a pronúncia: hoje → ôje" in avisos
    assert "vou lembrar de: Não repita a pergunta antes de responder." in avisos
    notas = [m["content"] for m in ollama.conversas[-1]["messages"] if m["role"] == "system"]
    assert any(
        "Como Gabriel pediu que você fale" in n and "Não repita a pergunta" in n for n in notas
    )


def test_comandos_de_pronuncias_e_preferencias(criar_raiz, capsys, monkeypatch):
    with OllamaComMemoria() as ollama:
        raiz = criar_raiz(local="[memoria]\nativa = true\n")
        monkeypatch.setattr(
            "nora.cli.carregar", lambda: carregar(raiz, ambiente={"OLLAMA_HOST": ollama.url})
        )
        assert main(["memoria", "pronuncias", "hoje", "ôje"]) == 0
        assert main(["memoria", "pronuncias", "casa"]) == 1  # missing how to say it
        assert main(["memoria", "pronuncias"]) == 0
        assert main(["memoria", "pronuncias", "--esquecer", "hoje"]) == 0
        assert main(["memoria", "pronuncias", "--esquecer", "hoje"]) == 1
        assert main(["memoria", "preferencias", "Seja", "mais", "direta."]) == 0
        assert main(["memoria", "preferencias"]) == 0
        assert main(["memoria", "preferencias", "--esquecer", "1"]) == 0
        assert main(["memoria", "preferencias", "--esquecer", "1"]) == 1
    texto = capsys.readouterr().out
    assert "Guardado: hoje → ôje" in texto
    assert "1 pronúncias aprendidas" in texto and "  hoje → ôje" in texto
    assert "Guardada (nº 1)." in texto
    assert "     1  Seja mais direta." in texto


def test_apagar_e_corrigir_pela_conversa(criar_raiz):
    local = '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\nsimilaridade_minima = 0.2\n'
    errado = "Gabriel tem prova de cálculo 1 na PUCMG em 21/11/2026"
    certo = "Gabriel tem prova na PUCMG em 21/11/2026"
    with OllamaComMemoria(fatos=[errado]) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        conversa = nova_conversa(config)
        "".join(conversa.perguntar("tenho prova de cálculo 1 dia 21/11 na PUCMG"))
        conversa.esperar_memoria()
        assert [f.texto for f in conversa.memoria.listar()] == [errado]

        ollama.fatos = [certo]
        ollama.extras = {"esquecer": [errado]}
        "".join(conversa.perguntar("não é cálculo 1, a prova é de outra matéria"))
        avisos = conversa.encerrar()
        textos = [f.texto for f in conversa.memoria.listar()]
        agenda = [e.texto for e in conversa.memoria.eventos_contendo("PUCMG")]
        conversa.memoria.fechar()

    assert f"esqueci: {errado}" in avisos
    assert textos == [
        certo
    ]  # the wrong one left, the right one came in (without recording the delete request)
    assert agenda == [certo]  # and the agenda follows
