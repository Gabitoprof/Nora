"""Auto-melhoria: observador, fechamento do dia, relatório, decisões e aviso."""

from test_roteador import OpenAIFalso, montar

from nora.conversa import nova_conversa
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
