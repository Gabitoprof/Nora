"""Switching the voice by speaking: understands the request, switches at once and keeps the
previous one if it fails."""

import io

from nora.config import carregar
from nora.conversa import conversar, nova_conversa
from nora.conversa_voz import responder_falando
from nora.servico import ServicoIndisponivel
from nora.troca_voz import PedidoDeVoz, atender_pedido, pedido_de_voz
from nora.voz import VozComReserva, VozTrocavel


def test_entende_os_pedidos_de_troca():
    assert pedido_de_voz("troque para a voz do piper") == PedidoDeVoz("trocar", "piper")
    assert pedido_de_voz("Nora, usa a voz do Kokoro!") == PedidoDeVoz("trocar", "kokoro")
    assert pedido_de_voz("volta pro ElevenLabs") == PedidoDeVoz("trocar", "elevenlabs")
    assert pedido_de_voz("volta pro Eleven Labs") == PedidoDeVoz("trocar", "elevenlabs")
    assert pedido_de_voz("fala com a voz do Piper") == PedidoDeVoz("trocar", "piper")
    assert pedido_de_voz("volta para a voz normal") == PedidoDeVoz("trocar")
    assert pedido_de_voz("qual voz você está usando?") == PedidoDeVoz("qual")
    # questions and other commands are not voice switches
    assert pedido_de_voz("fale sobre o Kokoro") is None
    assert pedido_de_voz("use o Claude") is None
    assert pedido_de_voz("fala mais devagar") is None
    assert (
        pedido_de_voz("o piper é melhor que o kokoro em quê, e por que ele tem esse nome?") is None
    )


class MotorFalso:
    def __init__(self, nome, falhar=False):
        self.nome, self.falhar, self.falas = nome, falhar, []

    def sintetizar(self, texto):
        if self.falhar:
            raise ServicoIndisponivel(f"{self.nome} fora do ar.")
        self.falas.append(texto)
        return self.nome.encode()


def trocavel(criar_raiz, monkeypatch, fora=()):
    config = carregar(
        criar_raiz(local='[voz]\nmotor = "elevenlabs"\nreserva = "piper"\n'), ambiente={}
    )
    motores = {}

    def criar(_config, motor, realce=None):
        motores[motor] = MotorFalso(motor, falhar=motor in fora)
        return motores[motor]

    monkeypatch.setattr("nora.voz._criar_motor", criar)
    return VozTrocavel(config), motores


def test_troca_e_volta(criar_raiz, monkeypatch):
    voz, motores = trocavel(criar_raiz, monkeypatch)
    assert voz.motor == "elevenlabs" and isinstance(voz.voz, VozComReserva)
    resposta, wav = atender_pedido(voz, PedidoDeVoz("trocar", "piper"), "elevenlabs")
    assert resposta == "Pronto, agora falo com a voz do Piper." and wav == b"piper"
    assert voz.motor == "piper"
    assert voz.voz.reserva.nome == "elevenlabs"  # the config's main voice becomes the fallback
    assert voz.sintetizar("oi") == b"piper"
    assert atender_pedido(voz, PedidoDeVoz("qual"), "elevenlabs")[0].endswith("do Piper.")
    assert "Já estou" in atender_pedido(voz, PedidoDeVoz("trocar", "piper"), "elevenlabs")[0]
    atender_pedido(voz, PedidoDeVoz("trocar"), "elevenlabs")  # "voz normal"
    assert voz.motor == "elevenlabs"


def test_voz_fora_do_ar_continua_a_de_antes(criar_raiz, monkeypatch):
    voz, _ = trocavel(criar_raiz, monkeypatch, fora=("kokoro",))
    resposta, wav = atender_pedido(voz, PedidoDeVoz("trocar", "kokoro"), "elevenlabs")
    assert wav is None and "kokoro fora do ar" in resposta
    assert "Continuo com a voz do ElevenLabs" in resposta and voz.motor == "elevenlabs"


def test_na_conversa_por_voz_o_pedido_nao_vai_ao_cerebro(criar_raiz, monkeypatch):
    voz, _ = trocavel(criar_raiz, monkeypatch)
    config = voz.config
    conversa = nova_conversa(config, cerebro=None, memoria=None)
    tocados, linhas = [], []

    def escrever(texto="", fim="\n"):
        linhas.append(texto)

    responder_falando(
        conversa, voz, tocados.append, "troque para a voz do piper", 0.0, 0.0, escrever, False
    )
    assert tocados == [b"piper"] and voz.motor == "piper"
    assert any("agora falo com a voz do Piper" in linha for linha in linhas)
    assert conversa.mensagens[-1]["role"] != "user"  # nothing went to the brain
    assert "comando de voz" in conversa.historico.arquivo.read_text("utf-8")


def test_confirmacao_da_troca_leva_o_texto_para_a_hud(criar_raiz, monkeypatch):
    """Regression: the confirmation ("agora falo com a voz do Piper") played without contexto_fala,
    and the HUD got neither the text nor the words on that path. It has to play inside the
    context, as Locutor does with the answer's sentences."""
    from nora import hud_audio

    voz, _ = trocavel(criar_raiz, monkeypatch)
    conversa = nova_conversa(voz.config, cerebro=None, memoria=None)
    textos = []
    responder_falando(
        conversa, voz, lambda wav: textos.append(getattr(hud_audio._contexto, "texto", "")),
        "troque para a voz do piper", 0.0, 0.0, lambda *a, **k: None, False,
    )  # fmt: skip
    assert len(textos) == 1 and "agora falo com a voz do Piper" in textos[0]
    assert getattr(hud_audio._contexto, "texto", "") == ""  # the context does not leak afterwards


def test_no_modo_texto_avisa_que_nao_tem_voz(criar_raiz):
    config = carregar(criar_raiz(), ambiente={})
    respostas = iter(["troque para a voz do piper", "sair"])
    saida = io.StringIO()

    class CerebroCalado:
        def aquecer(self):
            return 0.0

        def responder(self, mensagens):
            raise AssertionError("o pedido de voz não deve ir ao cérebro")

    conversar(config, entrada=lambda _: next(respostas), saida=saida, cerebro=CerebroCalado())
    assert "só escrevo, sem voz" in saida.getvalue()


def test_perguntas_sobre_vozes_nao_trocam_a_voz():
    """A6: only switches on a clear request; asking about an engine changes nothing."""
    for frase in [
        "qual voz é melhor, a do Piper ou a do Kokoro?",
        "o Piper é melhor que o Kokoro?",
        "compara a voz do Piper com a do ElevenLabs",
        "usa o Kokoro ou o Piper?",
        "como funciona a voz do Piper?",
        "por que a voz do Kokoro é mais rápida?",
        "o que você acha da voz do ElevenLabs?",
        "fale sobre o Kokoro",
        "a voz do piper ficou boa",
    ]:
        assert pedido_de_voz(frase) is None, frase
    # clear requests still work
    assert pedido_de_voz("pode usar a voz do Piper?") == PedidoDeVoz("trocar", "piper")
    assert pedido_de_voz("troca do Kokoro para o Piper") == PedidoDeVoz("trocar", "piper")
    assert pedido_de_voz("muda pra voz do ElevenLabs") == PedidoDeVoz("trocar", "elevenlabs")
