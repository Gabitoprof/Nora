import io
import json

import pytest
from fake_ollama import OllamaFalso
from fake_servico import ServicoFalso

from ella.audio import duracao_wav, ler_wav, para_wav
from ella.cli import verificar
from ella.config import carregar
from ella.conversa_voz import conversar_por_voz
from ella.frases import SeparadorDeFrases
from ella.ouvido import OuvidoWhisper
from ella.servico import ServicoIndisponivel, responde
from ella.voz import VozPiper

UM_SEGUNDO = para_wav(b"\x00\x00" * 16_000)


def config_com(
    criar_raiz,
    ollama="http://127.0.0.1:9",
    whisper="http://127.0.0.1:9",
    piper="http://127.0.0.1:9",
):
    local = f'[ouvido]\nurl = "{whisper}"\n[voz]\nurl = "{piper}"\n'
    return carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama})


def picotar(texto, tamanho=3):
    return [texto[i : i + tamanho] for i in range(0, len(texto), tamanho)]


# --- frases -----------------------------------------------------------------------------------


def test_separa_frases_conforme_o_texto_chega():
    separador = SeparadorDeFrases()
    frases = []
    for pedaco in picotar("Oi, Gabriel! Tudo certo por aqui. E com você? Bora conversar"):
        frases += separador.alimentar(pedaco)
    assert frases == ["Oi, Gabriel!", "Tudo certo por aqui.", "E com você?"]
    assert separador.finalizar() == ["Bora conversar"]
    assert separador.finalizar() == []


def test_nao_corta_em_abreviacao_nem_em_frase_curta():
    separador = SeparadorDeFrases()
    frases = separador.alimentar("Sim. Falei com o Dr. Paulo hoje cedo. Ele disse que sim.\n")
    assert frases == ["Sim.", "Falei com o Dr. Paulo hoje cedo.", "Ele disse que sim."]
    assert separador.alimentar("Ok. ") == []
    assert separador.finalizar() == ["Ok."]


def test_numero_decimal_e_quebra_de_linha():
    separador = SeparadorDeFrases()
    frases = separador.alimentar(
        "O dólar está em 5.42 reais hoje\nAmanhã eu confiro de novo para você"
    )
    assert frases == ["O dólar está em 5.42 reais hoje"]
    assert separador.finalizar() == ["Amanhã eu confiro de novo para você"]


# --- áudio ------------------------------------------------------------------------------------


def test_wav_ida_e_volta():
    amostras, taxa, canais = ler_wav(UM_SEGUNDO)
    assert (len(amostras), taxa, canais) == (32_000, 16_000, 1)
    assert duracao_wav(UM_SEGUNDO) == pytest.approx(1.0)


# --- ouvido -----------------------------------------------------------------------------------


def test_ouvido_envia_o_wav_e_le_o_texto(criar_raiz):
    resposta = json.dumps({"text": "  qual é a capital\n do Brasil? "}).encode()
    with ServicoFalso(lambda *_: (200, "application/json", resposta)) as whisper:
        ouvido = OuvidoWhisper(config_com(criar_raiz, whisper=whisper.url))
        assert ouvido.transcrever(UM_SEGUNDO) == "qual é a capital do Brasil?"
    caminho, cabecalhos, corpo = whisper.pedidos[0]
    assert caminho == "/inference"
    assert cabecalhos["Content-Type"].startswith("multipart/form-data; boundary=")
    assert b'name="language"\r\n\r\npt\r\n' in corpo
    assert b'name="response_format"\r\n\r\njson\r\n' in corpo
    assert b'filename="fala.wav"' in corpo and UM_SEGUNDO in corpo
    assert ouvido.ultima_duracao > 0


@pytest.mark.parametrize(
    ("bruto", "limpo"),
    [
        ("[MÚSICA DE FUNDO]", ""),
        (" [BLANK_AUDIO] ", ""),
        ("(risos) [música]", ""),
        ("[música] Oi Ella, tudo bem?", "Oi Ella, tudo bem?"),
        ("Que horas são? (tosse)", "Que horas são?"),
        ("", ""),
    ],
)
def test_limpa_descricoes_de_som(bruto, limpo):
    from ella.ouvido import limpar_transcricao

    assert limpar_transcricao(bruto) == limpo


def test_ouvido_fora_do_ar(criar_raiz):
    with pytest.raises(ServicoIndisponivel, match="whisper-server em http://127.0.0.1:9"):
        OuvidoWhisper(config_com(criar_raiz), timeout=2).transcrever(UM_SEGUNDO)


# --- voz --------------------------------------------------------------------------------------


def test_voz_pede_o_audio_da_frase(criar_raiz):
    with ServicoFalso(lambda *_: (200, "audio/wav", UM_SEGUNDO)) as piper:
        voz = VozPiper(config_com(criar_raiz, piper=piper.url))
        assert voz.sintetizar("Olá, tudo bem?") == UM_SEGUNDO
    assert json.loads(piper.pedidos[0][2]) == {"text": "Olá, tudo bem?"}


def test_voz_repassa_erro_do_piper(criar_raiz):
    with ServicoFalso(lambda *_: (500, "text/plain", b"voz nao carregada")) as piper:
        with pytest.raises(ServicoIndisponivel, match="Piper recusou o pedido \\(500\\)"):
            VozPiper(config_com(criar_raiz, piper=piper.url)).sintetizar("oi")


def test_verificar_mostra_os_servicos_de_voz(criar_raiz):
    with ServicoFalso(lambda *_: (200, "text/plain", b"")) as piper:
        assert responde(piper.url)
        linhas = verificar(config_com(criar_raiz, piper=piper.url))
    assert any("Piper" in linha and linha.endswith("ok") for linha in linhas)
    assert any("whisper-server" in linha and "não respondeu" in linha for linha in linhas)


# --- conversa por voz -------------------------------------------------------------------------


def test_conversa_por_voz_de_ponta_a_ponta(criar_raiz):
    transcricao = json.dumps({"text": "Qual é a capital do Brasil?"}).encode()
    resposta = "A capital do Brasil é Brasília. Fica no Distrito Federal."
    tocados = []
    with (
        OllamaFalso(picotar(resposta)) as ollama,
        ServicoFalso(lambda *_: (200, "application/json", transcricao)) as whisper,
        ServicoFalso(lambda caminho, cab, corpo: (200, "audio/wav", corpo)) as piper,
    ):
        config = config_com(criar_raiz, ollama.host, whisper.url, piper.url)
        comandos = iter(["", "e você?", "sair"])
        saida = io.StringIO()
        conversar_por_voz(
            config,
            entrada=lambda _: next(comandos),
            saida=saida,
            medir=True,
            gravar=lambda entrada: UM_SEGUNDO,
            tocar=tocados.append,
        )
    texto = saida.getvalue()
    assert "Você: Qual é a capital do Brasil?" in texto
    assert f"Ella: {resposta}" in texto
    assert "começou a falar em" in texto
    falado = [json.loads(audio)["text"] for audio in tocados]
    assert falado == [
        "A capital do Brasil é Brasília.",
        "Fica no Distrito Federal.",
        "A capital do Brasil é Brasília.",
        "Fica no Distrito Federal.",
    ]
    assert len(whisper.pedidos) == 1  # a segunda pergunta foi digitada


def test_conversa_por_voz_segue_sem_os_servicos(criar_raiz):
    with OllamaFalso(["Oi! Tudo bem por aí?"]) as ollama:
        config = config_com(criar_raiz, ollama.host)
        comandos = iter(["", "oi", "sair"])
        saida = io.StringIO()
        conversar_por_voz(
            config,
            entrada=lambda _: next(comandos),
            saida=saida,
            gravar=lambda entrada: UM_SEGUNDO,
            tocar=lambda wav: None,
        )
    texto = saida.getvalue()
    assert "[erro] Não consegui falar com o whisper-server" in texto
    assert "Ella: Oi! Tudo bem por aí?" in texto
    assert "[erro na voz] Não consegui falar com o Piper" in texto


def test_gravacao_vazia_e_ignorada(criar_raiz):
    comandos = iter(["", "sair"])
    saida = io.StringIO()
    conversar_por_voz(
        config_com(criar_raiz),
        entrada=lambda _: next(comandos),
        saida=saida,
        gravar=lambda entrada: para_wav(b""),
        tocar=lambda wav: None,
    )
    assert "(não ouvi nada)" in saida.getvalue()
