import io
import json
from datetime import datetime

import pytest
from fake_ollama import OllamaFalso

from ella.cerebro import CerebroIndisponivel, CerebroLocal
from ella.config import carregar
from ella.conversa import Conversa, conversar
from ella.historico import Historico
from ella.persona import prompt_de_sistema


def config_com(criar_raiz, host="http://127.0.0.1:9", local=None):
    return carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": host})


def test_prompt_reflete_a_persona(criar_raiz):
    config = config_com(criar_raiz, local='[usuario]\nnome = "Gabriel"\n[persona]\nhumor = 0.9\n')
    prompt = prompt_de_sistema(config, agora=datetime(2026, 10, 30, 9, 5))
    assert "Você é Ella" in prompt
    assert "espirituosa" in prompt
    assert "não use markdown" in prompt
    assert "sexta-feira, 30/10/2026, 09:05" in prompt
    assert "conversando com Gabriel" in prompt
    assert "Não invente fatos" in prompt
    assert "Vá direto ao ponto" in prompt


def test_prompt_serio_e_sem_usuario(criar_raiz):
    config = config_com(criar_raiz, local="[persona]\nhumor = 0.0\nrespostas_curtas = true\n")
    prompt = prompt_de_sistema(config)
    assert "sem piadas" in prompt
    assert "curta" in prompt
    assert "conversando com" not in prompt


def test_cerebro_responde_aos_pedacos_e_envia_a_config(criar_raiz):
    with OllamaFalso(["A capital ", "é Brasília."]) as ollama:
        config = config_com(criar_raiz, ollama.host)
        cerebro = CerebroLocal(config)
        pedacos = list(cerebro.responder([{"role": "user", "content": "oi"}]))
    assert pedacos == ["A capital ", "é Brasília."]
    pedido = ollama.pedidos[0]
    assert pedido["model"] == "qwen3.5:9b"
    assert pedido["think"] is False
    assert pedido["stream"] is True
    assert pedido["keep_alive"] == "10m"
    assert pedido["options"] == {"temperature": 0.6}
    assert cerebro.medidas.tokens == 10
    assert cerebro.medidas.tokens_por_segundo == pytest.approx(50.0)
    assert cerebro.medidas.primeiro_pedaco > 0


def test_aquecer_carrega_o_modelo_sem_gerar(criar_raiz):
    with OllamaFalso([]) as ollama:
        cerebro = CerebroLocal(config_com(criar_raiz, ollama.host))
        assert cerebro.aquecer() >= 0
    assert ollama.pedidos[0]["messages"] == []
    assert ollama.pedidos[0]["model"] == "qwen3.5:9b"
    with pytest.raises(CerebroIndisponivel, match="Ele está aberto"):
        CerebroLocal(config_com(criar_raiz), timeout=2).aquecer()


def test_cerebro_sem_ollama_da_erro_claro(criar_raiz):
    cerebro = CerebroLocal(config_com(criar_raiz), timeout=2)
    with pytest.raises(CerebroIndisponivel, match="Ele está aberto"):
        list(cerebro.responder([]))


def test_cerebro_repassa_erro_do_ollama(criar_raiz):
    with OllamaFalso([], status=404) as ollama:
        with pytest.raises(CerebroIndisponivel, match="404"):
            list(CerebroLocal(config_com(criar_raiz, ollama.host)).responder([]))
    with OllamaFalso([], erro="sem memória") as ollama:
        with pytest.raises(CerebroIndisponivel, match="sem memória"):
            list(CerebroLocal(config_com(criar_raiz, ollama.host)).responder([]))


def test_conversa_guarda_contexto_e_historico(criar_raiz, tmp_path):
    with OllamaFalso(["Oi!"]) as ollama:
        config = config_com(criar_raiz, ollama.host)
        historico = Historico(tmp_path / "dados", sessao="2026-10-30_10-00-00")
        conversa = Conversa(config, CerebroLocal(config), historico)
        assert "".join(conversa.perguntar("olá")) == "Oi!"
        assert "".join(conversa.perguntar("tudo bem?")) == "Oi!"
    segundo_pedido = ollama.pedidos[1]["messages"]
    assert [m["role"] for m in segundo_pedido] == ["system", "user", "assistant", "user"]
    registros = [json.loads(linha) for linha in historico.arquivo.read_text("utf-8").splitlines()]
    assert [r["papel"] for r in registros] == ["usuario", "assistente"] * 2
    assert registros[1]["texto"] == "Oi!"
    assert registros[1]["modelo"] == "qwen3.5:9b"
    assert historico.arquivo.name == "2026-10-30.jsonl"


def test_conversa_descarta_pergunta_que_falhou(criar_raiz, tmp_path):
    config = config_com(criar_raiz)
    conversa = Conversa(config, CerebroLocal(config, timeout=2), Historico(tmp_path))
    with pytest.raises(CerebroIndisponivel):
        list(conversa.perguntar("oi"))
    assert [m["role"] for m in conversa.mensagens] == ["system"]


def test_conversar_no_terminal(criar_raiz):
    with OllamaFalso(["Brasília."]) as ollama:
        config = config_com(criar_raiz, ollama.host)
        falas = iter(["qual a capital?", "/limpar", "", "sair"])
        saida = io.StringIO()
        assert conversar(config, entrada=lambda _: next(falas), saida=saida, medir=True) == 0
    texto = saida.getvalue()
    assert "pronto em" in texto
    assert ollama.pedidos[0]["messages"] == []
    assert "Ella: Brasília." in texto
    assert "tokens/s" in texto
    assert "(conversa reiniciada)" in texto
    assert "conversa salva em" in texto
    assert (config.pasta_dados / "historico").is_dir()


def test_conversar_sem_ollama_nao_quebra(criar_raiz):
    falas = iter(["oi", "sair"])
    saida = io.StringIO()
    conversar(config_com(criar_raiz), entrada=lambda _: next(falas), saida=saida)
    assert "[erro]" in saida.getvalue()
