"""Emotion in the voice: internal tags, translated per engine and invisible on screen and in
memory."""

import io
import json

import pytest
from fake_servico import ServicoFalso
from test_memoria import OllamaComMemoria
from test_voz import UM_SEGUNDO, config_com

from nora.config import ConfigError, carregar
from nora.conversa import conversar, nova_conversa
from nora.emocao import FiltroDeTela, ajustes_de_voz, emocoes_em, para_v3, sem_emocoes
from nora.persona import prompt_de_sistema
from nora.voz import criar_voz

RESPOSTA = "{alegre} Que bom te ver! {risada} Essa foi ótima. Tudo certo? {séria} Atenção ao prazo."


def test_etiquetas_saem_ou_viram_audio_tags():
    assert sem_emocoes(RESPOSTA) == (
        "Que bom te ver! Essa foi ótima. Tudo certo? Atenção ao prazo."
    )
    assert [e.nome for e in emocoes_em(RESPOSTA)] == ["alegre", "risada", "seria"]
    assert para_v3(RESPOSTA) == (
        "[happy] Que bom te ver! [laughs] Essa foi ótima. Tudo certo? [serious] Atenção ao prazo."
    )
    # low intensity: no laughs or sighs; zero: no emotion
    assert "[laughs]" not in para_v3(RESPOSTA, 0.2) and "[happy]" in para_v3(RESPOSTA, 0.2)
    assert para_v3(RESPOSTA, 0) == sem_emocoes(RESPOSTA)
    # an unknown tag disappears, without becoming an audio tag
    assert para_v3("{zangadissima} Ok.") == "Ok."


def test_ajustes_de_voz_para_quem_nao_entende_tags():
    assert ajustes_de_voz("Sem emoção.") is None
    cheio = ajustes_de_voz("{empolgada} Passei!", 0.5)
    assert cheio == {"stability": 0.3, "style": 0.5, "speed": 1.07}
    fraco = ajustes_de_voz("{empolgada} Passei!", 0.25)
    assert fraco["style"] < cheio["style"] and fraco["stability"] > cheio["stability"]
    assert ajustes_de_voz("{empolgada} Passei!", 0) is None


def test_tela_nao_mostra_etiquetas_mesmo_partidas():
    tela = FiltroDeTela()
    pedacos = ["{ale", "gre} Que ", "bom! {ri", "sada} Haha."]
    assert "".join(tela.alimentar(p) for p in pedacos) + tela.finalizar() == "Que bom! Haha."


def test_cada_motor_traduz_do_seu_jeito(criar_raiz, monkeypatch):
    pcm = b"\x01\x00" * 100
    with ServicoFalso(lambda *_: (200, "audio/pcm", pcm)) as nuvem:
        monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{nuvem.url}/v1/text-to-speech")
        for modelo in ("eleven_v3", "eleven_flash_v2_5"):
            extra = f'[voz.elevenlabs]\nvoz_id = "abc"\nmodelo = "{modelo}"\n'
            config = config_com(
                criar_raiz, motor="elevenlabs", extra=extra, ambiente={"ELEVENLABS_API_KEY": "x"}
            )
            criar_voz(config).sintetizar("{empolgada} Passei na prova!")
    v3, flash = (json.loads(corpo) for _, _, corpo in nuvem.pedidos)
    assert v3["text"] == "[excited] Passei na prova!" and "voice_settings" not in v3
    assert flash["text"] == "Passei na prova!"
    assert flash["voice_settings"] == {"stability": 0.3, "style": 0.5, "speed": 1.07}

    with ServicoFalso(lambda *_: (200, "audio/wav", UM_SEGUNDO)) as piper:
        criar_voz(config_com(criar_raiz, piper=piper.url)).sintetizar("{risada} Haha, boa!")
    assert json.loads(piper.pedidos[0][2])["text"] == "Haha, boa!"


def test_persona_pede_as_etiquetas_e_a_config_valida(criar_raiz):
    config = carregar(criar_raiz(), ambiente={})
    assert "{risada}" in prompt_de_sistema(config) and "No máximo 1" in prompt_de_sistema(config)
    sem = carregar(criar_raiz(local="[emocao]\nativa = false\n"), ambiente={})
    assert "{risada}" not in prompt_de_sistema(sem)
    with pytest.raises(ConfigError, match="intensidade"):
        carregar(criar_raiz(local="[emocao]\nintensidade = 2.0\n"), ambiente={})


def test_conversa_esconde_as_etiquetas_e_aprende_com_a_reacao(criar_raiz):
    local = '[usuario]\nnome = "Gabriel"\n[memoria]\nativa = true\n'
    with OllamaComMemoria(resposta=RESPOSTA) as ollama:
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.url})
        saida = io.StringIO()
        falas = iter(["me conta uma piada", "kkkk essa foi boa", "sair"])
        assert conversar(config, entrada=lambda _: next(falas), saida=saida) == 0

        conversa = nova_conversa(config)
        "".join(conversa.perguntar("oi"))
        conversa.encerrar()
        guardado = conversa.historico.arquivo.read_text(encoding="utf-8")
        conversa.memoria.fechar()

    texto = saida.getvalue()
    assert "Nora: Que bom te ver! Essa foi ótima." in texto and "{" not in texto
    assert "{alegre}" not in guardado and "Que bom te ver!" in guardado
    pedidos = [json.loads(c) for caminho, _, c in ollama.pedidos if caminho == "/api/chat"]
    # curations run in the background and may arrive in any order: find by content
    trocas = [p["messages"][1]["content"] for p in pedidos if p.get("format") == "json"]
    reacao = next(t for t in trocas if "kkkk essa foi boa" in t)
    # in the reaction exchange, curation sees the tone of the previous answer (with the tags)
    assert reacao.startswith("Resposta anterior da assistente: {alegre} Que bom te ver!")
    primeira = next(t for t in trocas if "me conta uma piada" in t)
    assert "Resposta anterior" not in primeira
