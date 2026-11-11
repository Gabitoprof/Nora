from datetime import date, timedelta

import pytest
from test_memoria import EmbeddingsFalsos, OllamaComMemoria

from nora.agenda import Evento, datas_no_texto, intervalo_da_pergunta, ler_data, ocorrencia, quando
from nora.cli import main
from nora.config import carregar
from nora.conversa import nova_conversa
from nora.memoria import Memoria

DOMINGO = date(2026, 11, 1)


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("o que tenho amanhã?", (date(2026, 11, 2), date(2026, 11, 2))),
        ("e depois de amanhã?", (date(2026, 11, 3), date(2026, 11, 3))),
        ("o que eu fiz ontem?", (date(2026, 10, 31), date(2026, 10, 31))),
        ("tenho algo semana que vem?", (date(2026, 11, 2), date(2026, 11, 8))),
        ("o que tenho na sexta?", (date(2026, 11, 6), date(2026, 11, 6))),
        ("e no próximo domingo?", (date(2026, 11, 8), date(2026, 11, 8))),
        ("o que rolou na sexta passada?", (date(2026, 10, 30), date(2026, 10, 30))),
        ("e no dia 21?", (date(2026, 11, 21), date(2026, 11, 21))),
        ("tenho prova 21/11?", (date(2026, 11, 21), date(2026, 11, 21))),
        ("o que tem em 3 de março?", (date(2027, 3, 3), date(2027, 3, 3))),
        ("o que tem em dezembro?", (date(2026, 12, 1), date(2026, 12, 31))),
        ("e mês que vem?", (date(2026, 12, 1), date(2026, 12, 31))),
        ("planos pro fim de semana?", (DOMINGO, DOMINGO)),
        ("me conta uma piada", None),
    ],
)
def test_periodo_da_pergunta(pergunta, esperado):
    assert intervalo_da_pergunta(pergunta, DOMINGO) == esperado


def test_datas_escritas_no_texto():
    assert datas_no_texto("Ana tem prova em 21/11/2026", DOMINGO) == [(date(2026, 11, 21), False)]
    assert datas_no_texto("Ana faz aniversário em 12 de março", DOMINGO) == [
        (date(2027, 3, 12), True)
    ]
    # no year: the date closest to today (an event from yesterday stays in the past)
    assert datas_no_texto("Em 31/10 o gato fugiu", DOMINGO) == [(date(2026, 10, 31), False)]
    assert datas_no_texto("Ana gosta de chá", DOMINGO) == []
    assert datas_no_texto("data inválida 31/02/2026", DOMINGO) == []
    assert ler_data("2026-11-21", DOMINGO) == date(2026, 11, 21)
    assert ler_data("21/11", DOMINGO) == date(2026, 11, 21)
    assert ler_data("qualquer coisa", DOMINGO) is None


def test_eventos_anuais_e_como_a_data_e_dita():
    aniversario = Evento(1, date(1990, 3, 12), "aniversário", anual=True)
    assert ocorrencia(aniversario, date(2027, 3, 1), date(2027, 3, 31)) == date(2027, 3, 12)
    assert ocorrencia(aniversario, date(2026, 11, 1), date(2026, 11, 30)) is None
    bissexto = Evento(2, date(2024, 2, 29), "aniversário", anual=True)
    assert ocorrencia(bissexto, date(2027, 2, 1), date(2027, 2, 28)) == date(2027, 2, 28)
    assert quando(date(2026, 11, 2), DOMINGO) == "segunda, 02/11/2026 (amanhã)"
    assert quando(date(2026, 11, 21), DOMINGO) == "sábado, 21/11/2026 (daqui a 20 dias)"
    assert quando(date(2026, 10, 30), DOMINGO) == "sexta, 30/10/2026 (há 2 dias)"


def test_agenda_na_memoria(tmp_path):
    memoria = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    fato_id, _ = memoria.lembrar("Ana tem prova em 21/11/2026")
    memoria.marcar(date(2026, 11, 21), "Ana tem prova em 21/11/2026", fato_id=fato_id)
    memoria.marcar(date(2026, 11, 20), "Ana tem prova em 20/11/2026", fato_id=fato_id)  # changed
    memoria.marcar(date(1990, 3, 12), "Ana faz aniversário em 12 de março", anual=True)
    novembro = memoria.agenda(date(2026, 11, 1), date(2026, 11, 30))
    assert [(dia, e.texto) for dia, e in novembro] == [
        (date(2026, 11, 20), "Ana tem prova em 20/11/2026")
    ]
    marco = memoria.agenda(date(2027, 3, 1), date(2027, 3, 31))
    assert [dia for dia, _ in marco] == [date(2027, 3, 12)]
    assert [e.texto for e in memoria.eventos_contendo("anivers")] == [
        "Ana faz aniversário em 12 de março"
    ]
    memoria.esquecer(fato_id)  # forgetting the fact removes it from the agenda too
    assert memoria.agenda(date(2026, 11, 1), date(2026, 11, 30)) == []
    assert memoria.contar_agenda() == 1
    assert memoria.desmarcar(marco[0][1].id) and not memoria.desmarcar(999)
    memoria.fechar()


def test_banco_antigo_ganha_a_agenda_com_os_fatos_que_tem_data(tmp_path):
    memoria = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    memoria.lembrar("Ana tem consulta no dentista em 10/11/2026")
    memoria.lembrar("Ana gosta de chá")
    memoria._db.execute("DELETE FROM agenda")
    memoria._db.execute("DELETE FROM meta WHERE chave = 'agenda_preenchida'")
    memoria._db.commit()
    memoria.fechar()
    reaberta = Memoria(tmp_path / "memoria.db", EmbeddingsFalsos())
    eventos = reaberta.agenda(date(2026, 11, 1), date(2026, 11, 30))
    assert [(dia, e.texto) for dia, e in eventos] == [
        (date(2026, 11, 10), "Ana tem consulta no dentista em 10/11/2026")
    ]
    reaberta.fechar()


def test_conversa_le_a_agenda_pelo_dia(criar_raiz):
    hoje = date.today()
    amanha = hoje + timedelta(days=1)
    longe = hoje + timedelta(days=40)
    fato = f"Gabriel tem consulta no dentista em {amanha:%d/%m/%Y}"
    local = '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\n'
    with OllamaComMemoria(fatos=[{"texto": fato, "area": "saúde"}]) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        primeira = nova_conversa(config)
        "".join(primeira.perguntar("Amanhã vou ao dentista."))
        avisos = primeira.encerrar()
        primeira.memoria.marcar(longe, "Gabriel viaja para a praia")
        primeira.memoria.fechar()
        assert avisos == [f"anotei em saúde: {fato} (agenda: {amanha:%d/%m/%Y})"]

        ollama.fatos = []
        segunda = nova_conversa(config)
        "".join(segunda.perguntar("O que eu tenho para fazer?"))
        "".join(segunda.perguntar(f"E no dia {longe:%d/%m}?"))
        "".join(segunda.perguntar(f"E em {hoje + timedelta(days=20):%d/%m/%Y}?"))
        segunda.encerrar()
        segunda.memoria.fechar()

    def nota(numero):
        mensagens = ollama.conversas[numero]["messages"]
        return "\n".join(m["content"] for m in mensagens if m["role"] == "system")

    assert "Agenda dos próximos 7 dias" in nota(-3)
    assert f"{amanha:%d/%m/%Y} (amanhã): {fato}" in nota(-3)
    assert "Gabriel viaja para a praia" in nota(-2)
    assert "Não há nada anotado na agenda para" in nota(-1)


def test_comandos_da_agenda(criar_raiz, capsys, monkeypatch):
    local = "[memoria]\nativa = true\n"
    with OllamaComMemoria() as ollama:
        raiz = criar_raiz(local=local)
        monkeypatch.setattr(
            "nora.cli.carregar", lambda: carregar(raiz, ambiente={"OLLAMA_HOST": ollama.url})
        )
        daqui = date.today() + timedelta(days=3)
        assert main(["memoria", "marcar", f"{daqui:%d/%m/%Y}", "prova", "de", "cálculo"]) == 0
        assert main(["memoria", "marcar", "amanhã?", "nada"]) == 1
        assert main(["memoria", "agenda", "--dias", "7"]) == 0
        assert main(["memoria", "listar"]) == 0
        assert main(["memoria", "desmarcar", "1"]) == 0
        assert main(["memoria", "desmarcar", "1"]) == 1
    texto = capsys.readouterr().out
    assert f"Marcado para {daqui:%d/%m/%Y} (nº 1)." in texto
    assert f"{daqui:%d/%m/%Y} (daqui a 3 dias)  prova de cálculo" in texto
    assert "prova de cálculo" in texto.split("fatos em")[1]  # it also became a fact
    assert "Tirado da agenda (nº 1)" in texto
