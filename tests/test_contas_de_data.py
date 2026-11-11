"""v0.3.1: the date math goes ready-made to the model, which used to get "daqui a 23 dias" wrong."""

from datetime import date

import pytest
from fake_ollama import OllamaFalso

from nora.agenda import contas_de_data
from nora.cerebro import CerebroLocal
from nora.config import carregar
from nora.conversa import Conversa
from nora.historico import Historico

HOJE = date(2026, 11, 5)  # Thursday


@pytest.mark.parametrize(
    ("pergunta", "esperado"),
    [
        ("que dia vai ser daqui a 23 dias", "- daqui a 23 dias: sábado, 28 de novembro de 2026"),
        ("e daqui a uma semana?", "- daqui a uma semana: quinta-feira, 12 de novembro de 2026"),
        ("daqui a um mês", "- daqui a um mês: sábado, 5 de dezembro de 2026"),
        ("em 2 anos", "- daqui a 2 anos: domingo, 5 de novembro de 2028"),
        ("há vinte e cinco dias", "- vinte e cinco dias atrás: domingo, 11 de outubro de 2026"),
        ("3 meses atrás", "- 3 meses atrás: quarta-feira, 5 de agosto de 2026"),
        (
            "que dia da semana cai 25/12?",
            "- 25/12/2026 cai num(a) sexta-feira, 25 de dezembro de 2026",
        ),
    ],
)
def test_contas_de_data(pergunta, esperado):
    assert contas_de_data(pergunta, HOJE) == [esperado]


def test_mes_que_nao_tem_o_dia_cai_no_ultimo():
    assert contas_de_data("daqui a 1 mes", date(2027, 1, 31)) == [
        "- daqui a 1 mês: domingo, 28 de fevereiro de 2027"
    ]


def test_pergunta_seguinte_sem_unidade_usa_a_da_anterior():
    assert contas_de_data("E daqui a 24", HOJE, "que dia vai ser daqui a 23 dias") == [
        "- daqui a 24 dias: domingo, 29 de novembro de 2026"
    ]
    assert contas_de_data("E daqui a 24?", HOJE, "bom dia") == []
    # "daqui a 22 dias" → "e daqui a 23" → "daqui a 50": the unit comes from the last one that had
    # one
    assert contas_de_data("Daqui a 50.", HOJE, ["Dia daqui a 22 dias.", "E daqui a 23."]) == [
        "- daqui a 50 dias: sexta-feira, 25 de dezembro de 2026"
    ]


@pytest.mark.parametrize("pergunta", ["em dias de chuva", "daqui a 2 horas", "tudo bem?", ""])
def test_sem_conta_de_data(pergunta):
    assert contas_de_data(pergunta, HOJE) == []


def test_conversa_manda_a_conta_pronta_ao_modelo(criar_raiz, tmp_path, monkeypatch):
    class Hoje(date):
        @classmethod
        def today(cls):
            return HOJE

    monkeypatch.setattr("nora.conversa.date", Hoje)
    with OllamaFalso(["Ok."]) as ollama:
        config = carregar(
            criar_raiz(local="[memoria]\nativa = false\n"), ambiente={"OLLAMA_HOST": ollama.host}
        )
        conversa = Conversa(config, CerebroLocal(config), Historico(tmp_path))
        list(conversa.perguntar("que dia vai ser daqui a 23 dias"))
        list(conversa.perguntar("E daqui a 24"))
    for pedido, linha in zip(
        ollama.pedidos,
        ["sábado, 28 de novembro de 2026", "domingo, 29 de novembro de 2026"],
        strict=True,
    ):
        notas = [m["content"] for m in pedido["messages"] if m["role"] == "system"]
        assert any("Contas de data" in nota and linha in nota for nota in notas)
