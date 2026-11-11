"""v0.3.1: the voice neither changes tone nor pauses between the first short sentence and the
next, and the ear gets the vocabulary as a hint."""

import json
import threading
import time

import pytest
from fake_servico import ServicoFalso

from nora.config import ConfigError, carregar
from nora.conversa_voz import Locutor
from nora.ouvido import dica_do_ouvido
from nora.voz import VozElevenLabs

PCM = b"\x01\x00" * 100


class VozAnotada:
    def __init__(self):
        self.pedidos = []

    def sintetizar(self, frase):
        self.pedidos.append(frase)
        return frase.encode()


# --- joining the short sentence ---------------------------------------------------------------


def test_frase_curta_espera_a_proxima_e_vai_junto():
    voz = VozAnotada()
    locutor = Locutor(voz, lambda wav: None, 0.0, juntar=60, espera=2.0)
    locutor.falar("Hahaha, esse atchim!")
    time.sleep(0.2)  # the model is still writing the next sentence
    locutor.falar("Saúde! Espero que não seja gripe chegando, viu?")
    locutor.falar("Toma um chá quente e descansa um pouco hoje à noite.")
    locutor.terminar()
    assert voz.pedidos == [
        "Hahaha, esse atchim! Saúde! Espero que não seja gripe chegando, viu?",
        "Toma um chá quente e descansa um pouco hoje à noite.",
    ]


def test_frase_curta_nao_espera_para_sempre():
    voz = VozAnotada()
    falou = threading.Event()
    locutor = Locutor(voz, lambda wav: falou.set(), 0.0, juntar=60, espera=0.1)
    locutor.falar("Oi!")
    assert falou.wait(2)  # with no next sentence, it speaks alone after the wait
    locutor.terminar()
    assert voz.pedidos == ["Oi!"]


def test_fim_da_resposta_libera_a_frase_curta_na_hora():
    voz = VozAnotada()
    locutor = Locutor(voz, lambda wav: None, 0.0, juntar=60, espera=5.0)
    inicio = time.perf_counter()
    locutor.falar("Pronto.")
    locutor.terminar()
    assert time.perf_counter() - inicio < 2
    assert voz.pedidos == ["Pronto."]


def test_pergunta_curta_nao_espera():
    voz = VozAnotada()
    locutor = Locutor(voz, lambda wav: None, 0.0, juntar=60, espera=2.0)
    locutor.falar("Tudo bem?")
    time.sleep(0.2)
    locutor.falar("Eu estou ótima hoje, obrigada por perguntar.")
    locutor.terminar()
    assert voz.pedidos == ["Tudo bem?", "Eu estou ótima hoje, obrigada por perguntar."]


def test_juntar_zero_mantem_o_jeito_antigo():
    voz = VozAnotada()
    locutor = Locutor(voz, lambda wav: None, 0.0)
    locutor.falar("Oi!")
    time.sleep(0.2)
    locutor.falar("Tudo certo por aqui, e com você?")
    locutor.terminar()
    assert voz.pedidos == ["Oi!", "Tudo certo por aqui, e com você?"]


# --- ElevenLabs: seed and previous sentence ---------------------------------------------------


def _eleven(url, monkeypatch, **extras):
    monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{url}/v1/text-to-speech")
    return VozElevenLabs("chave", "voz1", "eleven_v3", intensidade=0.0, **extras)


def test_elevenlabs_manda_semente_e_frase_anterior(monkeypatch):
    agora = [100.0]
    with ServicoFalso(lambda *_: (200, "audio/pcm", PCM)) as nuvem:
        voz = _eleven(nuvem.url, monkeypatch, semente=42, relogio=lambda: agora[0])
        voz.sintetizar("Hahaha, esse atchim!")
        voz.sintetizar("Saúde!")
        agora[0] += 120  # much later: another conversation, without the previous sentence
        voz.sintetizar("Bom dia!")
    corpos = [json.loads(corpo) for _, _, corpo in nuvem.pedidos]
    assert [c["seed"] for c in corpos] == [42, 42, 42]
    assert "previous_text" not in corpos[0]
    assert corpos[1]["previous_text"] == "Hahaha, esse atchim!"
    assert "previous_text" not in corpos[2]


def test_elevenlabs_sem_semente_e_sem_continuidade(monkeypatch):
    with ServicoFalso(lambda *_: (200, "audio/pcm", PCM)) as nuvem:
        voz = _eleven(nuvem.url, monkeypatch, semente=-1, continuidade=False)
        voz.sintetizar("Um.")
        voz.sintetizar("Dois.")
    for _, _, corpo in nuvem.pedidos:
        assert not {"seed", "previous_text"} & set(json.loads(corpo))


def test_elevenlabs_que_recusa_frase_anterior_segue_sem_ela(monkeypatch):
    def responder(caminho, cabecalhos, corpo):
        if "previous_text" in json.loads(corpo):
            return 400, "application/json", b'{"detail": "previous_text is not supported"}'
        return 200, "audio/pcm", PCM

    with ServicoFalso(responder) as nuvem:
        voz = _eleven(nuvem.url, monkeypatch)
        voz.sintetizar("Um.")
        voz.sintetizar("Dois.")  # refused with the context, retries without it
        voz.sintetizar("Três.")  # and does not try again
    enviados = [set(json.loads(corpo)) for _, _, corpo in nuvem.pedidos]
    assert ["previous_text" in e for e in enviados] == [False, True, False, False]
    assert voz.continuidade is False


def test_outro_erro_do_elevenlabs_nao_e_engolido(monkeypatch):
    from nora.servico import ServicoIndisponivel

    with ServicoFalso(
        lambda *_: (401, "application/json", b'{"detail": "chave invalida"}')
    ) as nuvem:
        voz = _eleven(nuvem.url, monkeypatch)
        with pytest.raises(ServicoIndisponivel, match="401"):
            voz.sintetizar("Um.")
    assert len(nuvem.pedidos) == 1


# --- config and ear hint ----------------------------------------------------------------------


def test_config_da_v031(criar_raiz):
    config = carregar(
        criar_raiz(
            local='[ouvido]\nvocabulario = ["Obsidian", " Ollama ", "Obsidian", ""]\n'
            "[voz]\njuntar_curta = 80\n[voz.elevenlabs]\nsemente = 7\ncontinuidade = false\n"
        ),
        ambiente={},
    )
    assert config.ouvido.vocabulario == ("Obsidian", "Ollama")
    assert config.voz.juntar_curta == 80
    assert config.voz.elevenlabs.semente == 7
    assert config.voz.elevenlabs.continuidade is False
    assert dica_do_ouvido(config) == (
        "Conversa com a assistente Nora. Palavras que podem aparecer: Obsidian, Ollama."
    )
    padrao = carregar(criar_raiz(), ambiente={})
    assert padrao.voz.juntar_curta == 60
    assert padrao.voz.elevenlabs.semente == 42
    assert dica_do_ouvido(padrao) == "Conversa com a assistente Nora."


@pytest.mark.parametrize(
    "local",
    [
        "[voz]\njuntar_curta = -1\n",
        "[voz.elevenlabs]\nsemente = -2\n",
        "[ouvido]\nvocabulario = [1]\n",
        '[ouvido]\nvocabulario = "Obsidian"\n',
    ],
)
def test_config_da_v031_invalida(criar_raiz, local):
    with pytest.raises(ConfigError):
        carregar(criar_raiz(local=local), ambiente={})
