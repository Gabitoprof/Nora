"""Second Brain (v0.3.1): memórias consolidadas → notas do Obsidian, grafo e mapa, sempre fora
do caminho da fala. Dados fictícios."""

import json
import os
import threading
import time
from pathlib import Path

import pytest
from test_memoria import EmbeddingsFalsos, OllamaComMemoria

from nora.config import ConfigError, carregar
from nora.emocao import TONS, tom_predominante
from nora.memoria import Memoria
from nora.notas import IndiceDeNotas, pastas_da_nora
from nora.segundo_cerebro import (
    CONTRATO,
    CORES_DAS_EMOCOES,
    VERSAO_DO_CONTRATO,
    Sincronizador,
    Trabalhador,
    destino,
    escrever_atomico,
    nome_de_arquivo,
    nomes_no_texto,
)

LOCAL = '[usuario]\nnome = "Lia"\n[notas]\npasta = "vault"\n[segundo_cerebro]\nativo = true\n'


@pytest.fixture
def ambiente(criar_raiz):
    def montar(extra=""):
        raiz = criar_raiz(local=LOCAL + extra)
        (raiz / "vault").mkdir(exist_ok=True)
        config = carregar(raiz, ambiente={})
        memoria = Memoria(config.pasta_dados / "memoria.db", EmbeddingsFalsos())
        sincronizador = Sincronizador(config, *destino(config))
        return config, memoria, sincronizador, raiz / "vault" / "Nora Brain"

    return montar


def frontmatter(texto: str) -> dict:
    linhas = texto.split("---\n")[1].splitlines()
    dados, tags = {}, []
    for linha in linhas:
        if linha.startswith("  - "):
            tags.append(json.loads(linha[4:]))
        elif ": " in linha:
            chave, valor = linha.split(": ", 1)
            dados[chave] = json.loads(valor)
    dados["tags"] = tags
    return dados


def memorias_de_exemplo(memoria):
    prova, _ = memoria.lembrar(
        "Lia tem prova de Cálculo na Unifictícia em 21/11/2026", "2026-11-05_10-00-00", "estudos"
    )
    memoria.marcar(__import__("datetime").date(2026, 11, 21), "prova", False, "estudos", prova)
    estudo, _ = memoria.lembrar(
        "Lia estuda com a Bia na Unifictícia às quartas",
        "2026-11-05_10-00-00",
        "estudos",
        "curiosa",
    )
    exame, _ = memoria.lembrar("Lia faz exames de rotina no Hospital Exemplo", "manual", "saúde")
    memoria.preferir("Seja mais direta.")
    return prova, estudo, exame


# --- exportação -------------------------------------------------------------------------------


def test_exporta_memorias_com_propriedades_links_e_sem_areas_privadas(ambiente):
    config, memoria, sincronizador, pasta = ambiente()
    prova, estudo, _ = memorias_de_exemplo(memoria)
    resumo = sincronizador.sincronizar()
    assert not resumo.erro and resumo.escritas == resumo.notas
    arquivos = sorted(p.relative_to(pasta).as_posix() for p in pasta.rglob("*.md"))
    assert arquivos == [
        "Agenda/2026-11.md",
        "Memórias/Lia estuda com a Bia na Unifictícia às quartas.md",
        "Memórias/Lia tem prova de Cálculo na Unifictícia em 21∕11∕2026.md".replace("∕", " "),
        "Nomes/Unifictícia.md",
        "Nora Brain.md",
        "Preferências.md",
        "Áreas/Estudos.md",
    ]
    nota = (pasta / "Memórias/Lia estuda com a Bia na Unifictícia às quartas.md").read_text("utf-8")
    dados = frontmatter(nota)
    assert dados["nora_id"] == f"mem-{estudo:06d}"
    assert dados["nora_gerenciado"] is True
    assert dados["area"] == "estudos" and dados["camada"] == "semantica"
    assert dados["emocao"] == "curiosa" and dados["emocao_fonte"] == "tom da resposta da Nora"
    assert dados["origem"] == "conversa de 2026-11-05"
    assert "nora/emocao/curiosa" in dados["tags"] and "nora/area/estudos" in dados["tags"]
    assert "[[Nora Brain/Áreas/Estudos|Estudos]]" in nota
    assert "[[Nora Brain/Nomes/Unifictícia|Unifictícia]]" in nota
    prova_nota = frontmatter(next(pasta.glob("Memórias/Lia tem prova*")).read_text("utf-8"))
    assert prova_nota["camada"] == "episodica" and prova_nota["data"] == "2026-11-21"
    assert "emocao" not in prova_nota  # sem etiqueta de tom: não inventa emoção
    # "Lia" é a própria pessoa e "Bia" só aparece uma vez: não viram nó
    assert not (pasta / "Nomes/Lia.md").exists() and not (pasta / "Nomes/Bia.md").exists()
    assert "Hospital" not in "".join(p.read_text("utf-8") for p in pasta.rglob("*.md"))
    assert prova


def test_repetir_nao_escreve_nem_duplica(ambiente):
    _, memoria, sincronizador, pasta = ambiente()
    memorias_de_exemplo(memoria)
    sincronizador.sincronizar()
    antes = {p: p.stat().st_mtime_ns for p in pasta.rglob("*.md")}
    resumo = sincronizador.sincronizar()
    assert (resumo.escritas, resumo.removidas, resumo.conflitos) == (0, 0, 0)
    assert {p: p.stat().st_mtime_ns for p in pasta.rglob("*.md")} == antes


def test_correcao_troca_a_nota_e_esquecer_tira_do_vault_e_do_grafo(ambiente):
    config, memoria, sincronizador, pasta = ambiente()
    prova, estudo, _ = memorias_de_exemplo(memoria)
    sincronizador.sincronizar()
    # correção: o mesmo fato com texto novo (mesmo id) troca a nota, sem deixar a antiga
    memoria.lembrar(
        "Lia estuda com a Bia na Unifictícia às quartas e sextas", "2026-11-06", "estudos"
    )
    sincronizador.sincronizar()
    memorias = sorted(p.name for p in (pasta / "Memórias").glob("*.md"))
    assert memorias == [
        "Lia estuda com a Bia na Unifictícia às quartas e sextas.md",
        "Lia tem prova de Cálculo na Unifictícia em 21 11 2026.md",
    ]
    # esquecer: a nota sai, o nome que ficou com uma menção só sai, e o grafo acompanha
    memoria.esquecer(estudo)
    resumo = sincronizador.sincronizar()
    assert resumo.removidas >= 2
    assert [p.name for p in (pasta / "Memórias").glob("*.md")] == [
        "Lia tem prova de Cálculo na Unifictícia em 21 11 2026.md"
    ]
    assert not (pasta / "Nomes").exists()
    grafo = json.loads((config.pasta_dados / "segundo_cerebro/grafo.json").read_text("utf-8"))
    assert f"mem-{estudo}" not in {no["id"] for no in grafo["nos"]}
    assert "quartas" not in (config.pasta_dados / "segundo_cerebro/mapa.html").read_text("utf-8")
    assert prova


def test_nota_editada_ou_sua_nunca_e_sobrescrita_nem_apagada(ambiente):
    _, memoria, sincronizador, pasta = ambiente()
    _, estudo, _ = memorias_de_exemplo(memoria)
    (pasta / "Áreas").mkdir(parents=True)
    minha = pasta / "Áreas/Estudos.md"
    minha.write_text("minha nota", encoding="utf-8")  # já existia, não é da Nora
    sincronizador.sincronizar()
    assert minha.read_text(encoding="utf-8") == "minha nota"
    editada = next(pasta.glob("Memórias/Lia estuda*"))
    editada.write_text(editada.read_text("utf-8") + "\nobservação minha\n", encoding="utf-8")
    memoria.esquecer(estudo)
    sincronizador.sincronizar()
    assert editada.exists() and "observação minha" in editada.read_text("utf-8")
    motivos = dict(sincronizador.status()["conflitos"])
    assert "não sobrescrevi" in motivos["Áreas/Estudos.md"]
    assert "não apaguei" in motivos[editada.relative_to(pasta).as_posix()]


def test_queda_no_meio_retoma_sem_duplicar_nem_conflito(ambiente, monkeypatch):
    _, memoria, sincronizador, pasta = ambiente()
    memorias_de_exemplo(memoria)
    original = sincronizador._registrar
    quedas = iter([True, False])

    def cair_depois_de_escrever(caminho, hash_):
        if hash_ is not None and next(quedas, False):
            raise OSError("queda de energia")  # o arquivo foi escrito, o registro não
        original(caminho, hash_)

    monkeypatch.setattr(sincronizador, "_registrar", cair_depois_de_escrever)
    assert sincronizador.sincronizar().erro == "OSError"
    monkeypatch.setattr(sincronizador, "_registrar", original)
    resumo = sincronizador.sincronizar()
    assert not resumo.erro and resumo.conflitos == 0
    assert sincronizador.status()["notas"] == resumo.notas


def test_escrita_atomica_nao_deixa_arquivo_pela_metade(tmp_path, monkeypatch):
    alvo = tmp_path / "nota.md"
    alvo.write_text("versão inteira", encoding="utf-8")

    def falhar(*_):
        raise OSError("disco cheio")

    monkeypatch.setattr(os, "replace", falhar)
    with pytest.raises(OSError):
        escrever_atomico(alvo, "versão nova")
    assert alvo.read_text(encoding="utf-8") == "versão inteira"
    assert [p.name for p in tmp_path.iterdir()] == ["nota.md"]  # sem temporário perdido


def test_vault_indisponivel_registra_erro_sem_levantar(ambiente):
    config, memoria, _, _ = ambiente()
    memorias_de_exemplo(memoria)
    bloqueio = config.notas.pasta / "Nora Brain"
    bloqueio.write_text("isto é um arquivo, não uma pasta", encoding="utf-8")
    resumo = Sincronizador(config, *destino(config)).sincronizar()
    assert resumo.erro and resumo.escritas == 0


def test_notas_da_nora_nao_voltam_como_notas_suas(ambiente):
    config, memoria, sincronizador, pasta = ambiente()
    memorias_de_exemplo(memoria)
    sincronizador.sincronizar()
    (config.notas.pasta / "Minha nota.md").write_text("# Minha nota\n", encoding="utf-8")
    assert pastas_da_nora(config) == ("Nora Brain",)
    indice = IndiceDeNotas(
        config.pasta_dados / "notas.db", config.notas.pasta, EmbeddingsFalsos(),
        pastas_da_nora(config),
    )  # fmt: skip
    assert list(indice._arquivos()) == ["Minha nota.md"]


def test_nomes_de_arquivo_e_propriedades_seguros():
    assert nome_de_arquivo('a/b:c*?"<>|# d.') == "a b c d"
    assert nome_de_arquivo("x" * 100).endswith("…") and len(nome_de_arquivo("x" * 100)) <= 61
    assert nome_de_arquivo("...") == "sem título"
    assert nomes_no_texto("Lia viu a Bia e o IBGE em Belo Horizonte.", {"lia"}) == [
        "Bia",
        "IBGE",
        "Belo Horizonte",
    ]


def test_texto_com_aspas_e_quebra_vira_yaml_valido(ambiente):
    _, memoria, sincronizador, pasta = ambiente()
    memoria.lembrar('Lia disse "oi: tudo"\nnova linha', "manual", "pessoal")
    sincronizador.sincronizar()
    dados = frontmatter(next(pasta.glob("Memórias/*.md")).read_text("utf-8"))
    assert dados["area"] == "pessoal" and dados["origem"].startswith("anotado pelo terminal")


def test_sem_emocoes_quando_desligado(ambiente):
    config, memoria, sincronizador, pasta = ambiente("emocoes = false\n")
    memorias_de_exemplo(memoria)
    sincronizador.sincronizar()
    assert "emocao" not in "".join(p.read_text("utf-8") for p in pasta.rglob("*.md"))


# --- grafo, contrato e mapa -------------------------------------------------------------------


def test_grafo_segue_o_contrato_versionado(ambiente):
    config, memoria, sincronizador, _ = ambiente()
    memorias_de_exemplo(memoria)
    sincronizador.sincronizar()
    contrato = json.loads(CONTRATO.read_text(encoding="utf-8"))
    grafo = json.loads((config.pasta_dados / "segundo_cerebro/grafo.json").read_text("utf-8"))
    assert grafo["versao"] == contrato["versao"] == VERSAO_DO_CONTRATO
    assert set(grafo) == set(contrato["grafo"]["campos"])
    ids = {no["id"] for no in grafo["nos"]}
    for no in grafo["nos"]:
        assert set(contrato["grafo"]["no"]["obrigatorios"]) <= set(no)
        assert no["tipo"] in contrato["grafo"]["tipos_de_no"]
        assert no.get("emocao", "") in {"", *contrato["emocoes"]["nomes"]}
    for ligacao in grafo["ligacoes"]:
        assert {ligacao["de"], ligacao["para"]} <= ids  # nenhuma ligação solta
        assert ligacao["tipo"] in contrato["grafo"]["tipos_de_ligacao"] and ligacao["base"]
    assert set(grafo["legenda"]["emocoes"]) == set(contrato["emocoes"]["nomes"])
    assert "saúde" not in grafo["legenda"]["areas"]


def test_cores_de_emocao_sao_as_da_hud():
    # Mesma tabela de hud/src/state.ts (`cores`) da branch feat/v0.4.0-hud: um sistema só.
    da_hud = {
        "alegre": "#F0C66A", "empolgada": "#F0C66A", "carinhosa": "#E3A4BD", "calma": "#AA9ACF",
        "seria": "#80A8F6", "triste": "#DF876A", "curiosa": "#66D4CB", "neutra": "#C9C9C9",
    }  # fmt: skip
    assert CORES_DAS_EMOCOES == da_hud
    assert TONS <= set(CORES_DAS_EMOCOES)


def test_mapa_escapa_texto_e_esconde_conteudo_por_padrao(ambiente):
    config, memoria, sincronizador, _ = ambiente()
    memoria.lembrar("Lia anotou </script><script>alert(1)</script> no caderno", "manual", "pessoal")
    sincronizador.sincronizar()
    pagina = (config.pasta_dados / "segundo_cerebro/mapa.html").read_text("utf-8")
    assert "<script>alert(1)" not in pagina and "\\u003c/script>" in pagina
    assert "let mostrarTexto = false;" in pagina
    assert "cdn" not in pagina.lower() and "https://" not in pagina  # nada de internet


def test_tom_predominante_das_etiquetas():
    assert tom_predominante("{curiosa} Hum! {alegre} Boa. {curiosa} E aí?") == "curiosa"
    assert tom_predominante("{risada} Haha. {sussurro} psiu") == ""  # reações não são tom
    assert tom_predominante("sem etiqueta") == ""


def test_grafo_grande_e_incremental(ambiente):
    config, memoria, sincronizador, pasta = ambiente()
    for i in range(1500):
        memoria.lembrar(f"Lia anotou o item {i} do Projeto Exemplo{i % 50} hoje", "manual",
                        ["estudos", "trabalho", "rotina"][i % 3])  # fmt: skip
    inicio = time.perf_counter()
    primeira = sincronizador.sincronizar()
    tempo_primeira = time.perf_counter() - inicio
    inicio = time.perf_counter()
    segunda = sincronizador.sincronizar()
    tempo_segunda = time.perf_counter() - inicio
    assert not primeira.erro and primeira.escritas == primeira.notas
    assert segunda.escritas == 0 and segunda.removidas == 0
    assert tempo_segunda < tempo_primeira  # só compara; não reescreve o vault
    # a memória junta fatos quase iguais; o vault tem uma nota por fato guardado
    assert len(list((pasta / "Memórias").glob("*.md"))) == memoria.contar() > 1000


# --- fora do caminho da fala ------------------------------------------------------------------


class SincronizadorFalso:
    def __init__(self, demora=0.0):
        self.demora = demora
        self.rodadas = []
        self.fechado = False

    def sincronizar(self, pausar=lambda: False):
        from nora.segundo_cerebro import Resumo

        self.rodadas.append(threading.current_thread().name)
        time.sleep(self.demora)
        return Resumo(interrompido=pausar())

    def fechar(self):
        self.fechado = True


def test_trabalhador_espera_a_nora_ficar_livre():
    ocupada = threading.Event()
    ocupada.set()
    falso = SincronizadorFalso()
    trabalhador = Trabalhador(falso, ocupado=ocupada.is_set, intervalo=60, folga=0.02)
    trabalhador.start()
    time.sleep(0.2)
    assert falso.rodadas == []  # respondendo ou falando: não roda
    ocupada.clear()
    for _ in range(100):
        if falso.rodadas:
            break
        time.sleep(0.02)
    assert falso.rodadas == ["nora-segundo-cerebro"]  # nunca na linha da conversa
    trabalhador.avisar()
    for _ in range(100):
        if len(falso.rodadas) == 2:
            break
        time.sleep(0.02)
    assert len(falso.rodadas) == 2
    trabalhador.encerrar(espera=2)
    assert falso.fechado and len(falso.rodadas) == 3  # a última, ao fechar


def test_conversa_responde_sem_esperar_o_second_brain(criar_raiz, monkeypatch):
    """Nova memória durante a resposta: a resposta sai na hora; a exportação vem depois, na
    linha do Second Brain, mesmo com ela lenta (3 s)."""
    from nora.conversa import nova_conversa

    chamadas = []

    def sincronizar_lento(self, pausar=lambda: False):
        from nora.segundo_cerebro import Resumo

        chamadas.append(threading.current_thread().name)
        time.sleep(3)
        return Resumo()

    monkeypatch.setattr(Sincronizador, "sincronizar", sincronizar_lento)
    with OllamaComMemoria(fatos=[{"texto": "Lia gosta de chá", "area": "pessoal"}]) as ollama:
        raiz = criar_raiz(local=LOCAL + "[memoria]\nativa = true\n")
        (raiz / "vault").mkdir()
        config = carregar(raiz, ambiente={"OLLAMA_HOST": ollama.url})
        conversa = nova_conversa(config)
        assert conversa.segundo_cerebro is not None
        time.sleep(0.1)  # a rodada de abertura já começou (e demora 3 s)
        inicio = time.perf_counter()
        resposta = "".join(conversa.perguntar("eu gosto de chá"))
        assert time.perf_counter() - inicio < 1.0
        assert resposta == "Anotado!"
        conversa.esperar_memoria()
        assert set(chamadas) == {"nora-segundo-cerebro"}  # nunca na linha da conversa
        conversa.segundo_cerebro._parar.set()
        conversa.segundo_cerebro = None
        conversa.memoria.fechar()


def test_falha_do_second_brain_nao_derruba_a_conversa(criar_raiz, monkeypatch):
    from nora.conversa import nova_conversa

    def quebrar(self, pausar=lambda: False):
        raise RuntimeError("vault sumiu")

    monkeypatch.setattr(Sincronizador, "sincronizar", quebrar)
    with OllamaComMemoria() as ollama:
        raiz = criar_raiz(local=LOCAL + "[memoria]\nativa = true\n")
        (raiz / "vault").mkdir()
        conversa = nova_conversa(carregar(raiz, ambiente={"OLLAMA_HOST": ollama.url}))
        assert "".join(conversa.perguntar("oi")) == "Anotado!"
        assert "".join(conversa.perguntar("tudo bem?")) == "Anotado!"
        conversa.encerrar()
        conversa.memoria.fechar()


def test_voz_marca_falando_enquanto_toca(criar_raiz):
    from fake_ollama import OllamaFalso

    from nora.conversa import nova_conversa
    from nora.conversa_voz import responder_falando

    visto = []
    with OllamaFalso(["Oi! Tudo certo por aqui."]) as ollama:
        conversa = nova_conversa(carregar(criar_raiz(), ambiente={"OLLAMA_HOST": ollama.host}))

        class Voz:
            def sintetizar(self, frase):
                return frase.encode()

        responder_falando(
            conversa, Voz(), lambda wav: visto.append(conversa.falando), "oi", 0.0, 0.0,
            lambda *a, **k: None, False,
        )  # fmt: skip
    assert visto and all(visto) and conversa.falando is False


# --- comandos ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fala", "pede"),
    [
        ("Nora, mostre seu segundo cérebro", True),
        ("abra o mapa da memória", True),
        ("visualize suas conexões", True),
        ("quero ver seu segundo cérebro", True),
        ("o que é um segundo cérebro?", False),
        ("me mostra a previsão do tempo", False),
    ],
)
def test_pedido_do_mapa(fala, pede):
    from nora.conversa import pede_o_mapa

    assert pede_o_mapa(fala) is pede


def test_comando_de_voz_abre_o_mapa_pronto(ambiente, monkeypatch, criar_raiz):
    from fake_ollama import OllamaFalso

    from nora.conversa import nova_conversa

    config, memoria, sincronizador, _ = ambiente()
    abertos = []
    monkeypatch.setattr(
        "nora.melhorias.abrir_arquivo",
        lambda c, na_frente=False: abertos.append((c, na_frente)) or True,
    )  # noqa: E501
    with OllamaFalso(["não devia chegar aqui"]) as ollama:
        conversa = nova_conversa(config, memoria=None, notas=None, observador=None)
        assert conversa.segundo_cerebro is None  # sem memória, não liga
        assert "ainda não ficou pronto" in "".join(conversa.perguntar("mostre seu segundo cérebro"))
        memorias_de_exemplo(memoria)
        sincronizador.sincronizar()
        assert "Abrindo" in "".join(conversa.perguntar("abra o mapa da memória"))
        assert ollama.pedidos == []  # comando: não passou pelo modelo nem refez nada
    assert abertos == [(config.pasta_dados / "segundo_cerebro/mapa.html", True)]
    desligado = nova_conversa(carregar(criar_raiz(), ambiente={}), memoria=None, notas=None,
                              observador=None)  # fmt: skip
    assert "desligado" in "".join(desligado.perguntar("mostre seu segundo cérebro"))


def test_cli_do_segundo_cerebro(ambiente, capsys, monkeypatch, criar_raiz):
    from nora import cli

    config, memoria, _, pasta = ambiente()
    memorias_de_exemplo(memoria)
    memoria.fechar()
    monkeypatch.setattr(cli, "RAIZ", Path(config.pasta_dados).parent, raising=False)
    monkeypatch.setattr(cli, "carregar", lambda *a, **k: config)
    assert cli.main(["cerebro", "sincronizar"]) == 0
    assert "nota(s) escrita(s)" in capsys.readouterr().out
    assert cli.main(["cerebro", "status"]) == 0
    assert "Notas da Nora: 7" in capsys.readouterr().out
    assert cli.main(["cerebro", "mapa"]) == 0
    assert capsys.readouterr().out.strip().endswith("mapa.html")
    assert "ligado," in cli._situacao_do_segundo_cerebro(config)
    desligado = carregar(criar_raiz(), ambiente={})
    assert cli._situacao_do_segundo_cerebro(desligado).startswith("desligado")
    monkeypatch.setattr(cli, "carregar", lambda *a, **k: desligado)
    assert cli.main(["cerebro", "status"]) == 1


@pytest.mark.parametrize(
    "extra",
    ['pasta = ""\n', "intervalo_s = 1\n", "areas_privadas = [1]\n"],
)
def test_config_invalida(criar_raiz, extra):
    with pytest.raises(ConfigError):
        carregar(criar_raiz(local="[segundo_cerebro]\n" + extra), ambiente={})


def test_padrao_e_desligado_e_privado(criar_raiz):
    config = carregar(criar_raiz(), ambiente={})
    assert config.segundo_cerebro.ativo is False
    assert config.segundo_cerebro.areas_privadas == ("saúde", "finanças")
    assert config.segundo_cerebro.mostrar_texto_no_mapa is False
