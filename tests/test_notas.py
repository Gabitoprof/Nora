"""Obsidian notes: splitting, reading the vault, updating only what changed, searching and using
them in conversation."""

import os

import pytest
from test_memoria import EmbeddingsFalsos

from nora.config import carregar
from nora.conversa import nova_conversa
from nora.notas import IndiceDeNotas, dividir, limpar_markdown


class Embeddings(EmbeddingsFalsos):
    def __init__(self):
        self.pedidos = 0

    def vetores(self, textos):
        self.pedidos += 1
        return [self.vetor(t) for t in textos]


def escrever(caminho, texto):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8")


def criar_vault(raiz):
    vault = raiz / "vault"
    escrever(
        vault / "Faculdade/Cálculo.md",
        "---\ntags: [estudo]\n---\n# Prova de cálculo\nA prova de derivadas é no dia 21.\n\n"
        "## Material\nEstudar a lista 3 de [[Exercícios|exercícios]] e o capítulo de limites.\n",
    )
    escrever(vault / "Receitas/Bolo.md", "Bolo de cenoura: três cenouras, ovos e farinha.\n")
    escrever(vault / ".obsidian/workspace.md", "configuração do obsidian")
    escrever(vault / ".trash/velha.md", "nota apagada sobre derivadas")
    escrever(vault / "Diário/2026-11-01.md", "derivadas me deixaram cansado hoje")
    return vault


def test_limpa_e_divide_por_titulos():
    texto = "---\na: 1\n---\nVeja [[Nota#Parte|isso]] e [[Outra]]. ![[foto.png]] %%oculto%%"
    assert limpar_markdown(texto).strip() == "Veja isso e Outra."
    trechos = dividir("Cálculo", "Intro\n# Prova\nDia 21.\n## Material\nLista 3.\n```\n# não\n```")
    assert [t for t, _ in trechos] == [
        "Cálculo",
        "Cálculo > Prova",
        "Cálculo > Prova > Material",
    ]
    assert "# não" in trechos[-1][1]  # a heading inside code does not open a section
    grande = dividir("Longa", "\n\n".join(["palavra " * 60] * 5), tamanho=500)
    assert len(grande) > 1 and all(len(c) <= 500 for _, c in grande)


@pytest.mark.parametrize("vetorial", [True, False])
def test_le_o_vault_atualiza_so_o_que_mudou_e_busca(tmp_path, vetorial):
    vault = criar_vault(tmp_path)
    embeddings = Embeddings()
    indice = IndiceDeNotas(tmp_path / "notas.db", vault, embeddings, ignorar=["Diário"])
    indice.vetorial = indice.vetorial and vetorial  # with and without sqlite-vec
    resumo = indice.atualizar()
    assert resumo.lidas == 2 and resumo.notas == 2  # without .obsidian, .trash and Diário
    achados = indice.buscar("quando é a prova de derivadas?", k=2)
    assert achados[0].titulo == "Cálculo > Prova de cálculo"
    assert achados[0].caminho == "Faculdade/Cálculo.md"

    pedidos = embeddings.pedidos
    assert indice.atualizar().lidas == 0 and embeddings.pedidos == pedidos  # nothing changed

    nota = vault / "Receitas/Bolo.md"
    escrever(nota, "Bolo de chocolate: cacau, ovos e açúcar.\n")
    os.utime(nota, (1, 1))  # ensures a different modification date
    (vault / "Faculdade/Cálculo.md").unlink()
    resumo = indice.atualizar()
    assert (resumo.lidas, resumo.removidas, resumo.notas) == (1, 1, 1)
    assert "chocolate" in indice.buscar("bolo de chocolate", k=1)[0].texto
    assert all("derivadas" not in t.texto for t in indice.buscar("derivadas", k=5))


def test_conversa_le_as_notas_parecidas(criar_raiz, tmp_path):
    vault = criar_vault(tmp_path)
    raiz = criar_raiz(local=f'[notas]\npasta = "{vault.as_posix()}"\n')
    config = carregar(raiz, ambiente={})
    assert config.notas.pasta == vault
    indice = IndiceDeNotas(tmp_path / "n.db", vault, Embeddings())
    indice.atualizar()

    from nora.cerebro import Medidas

    class Cerebro:
        medidas = Medidas()

        def __init__(self):
            self.pedidos = []

        def responder(self, mensagens):
            self.pedidos.append(mensagens)
            yield "É no dia 21."

    cerebro = Cerebro()
    conversa = nova_conversa(config, cerebro, memoria=None, notas=indice)
    "".join(conversa.perguntar("quando é a prova de derivadas?"))
    notas = [m for m in cerebro.pedidos[0] if m["role"] == "system" and "Obsidian" in m["content"]]
    assert notas and "Prova de cálculo" in notas[0]["content"]
    assert conversa.trechos_de_notas[0].caminho == "Faculdade/Cálculo.md"


def test_sem_pasta_nao_ha_notas(criar_raiz):
    from nora.notas import abrir_notas

    config = carregar(criar_raiz(), ambiente={})
    assert config.notas.pasta is None and abrir_notas(config) is None
