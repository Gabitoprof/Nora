import io
import json

import pytest
from fake_ollama import OllamaFalso
from fake_servico import ServicoFalso

from nora.audio import duracao_wav, ler_wav, para_wav
from nora.cli import verificar
from nora.config import carregar
from nora.conversa_voz import conversar_por_voz
from nora.frases import SeparadorDeFrases
from nora.ouvido import OuvidoWhisper
from nora.servico import ServicoIndisponivel, responde
from nora.voz import VozElevenLabs, VozHTTP, criar_voz

UM_SEGUNDO = para_wav(b"\x00\x00" * 16_000)


def config_com(
    criar_raiz,
    ollama="http://127.0.0.1:9",
    whisper="http://127.0.0.1:9",
    piper="http://127.0.0.1:9",
    motor="piper",
    extra="",
    ambiente=None,
    reserva="",
):
    local = (
        f'[ouvido]\nurl = "{whisper}"\n[voz]\nmotor = "{motor}"\nreserva = "{reserva}"\n'
        f'[voz.piper]\nurl = "{piper}"\n[voz.kokoro]\nurl = "{piper}"\n{extra}'
    )
    return carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama, **(ambiente or {})})


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
        ("[música] Oi Nora, tudo bem?", "Oi Nora, tudo bem?"),
        ("Que horas são? (tosse)", "Que horas são?"),
        ("", ""),
    ],
)
def test_limpa_descricoes_de_som(bruto, limpo):
    from nora.ouvido import limpar_transcricao

    assert limpar_transcricao(bruto) == limpo


def test_ouvido_fora_do_ar(criar_raiz):
    with pytest.raises(ServicoIndisponivel, match="whisper-server em http://127.0.0.1:9"):
        OuvidoWhisper(config_com(criar_raiz), timeout=2).transcrever(UM_SEGUNDO)


# --- voz --------------------------------------------------------------------------------------


def test_voz_pede_o_audio_da_frase(criar_raiz):
    with ServicoFalso(lambda *_: (200, "audio/wav", UM_SEGUNDO)) as piper:
        voz = criar_voz(config_com(criar_raiz, piper=piper.url))
        assert isinstance(voz, VozHTTP) and voz.nome == "o Piper"
        assert voz.sintetizar("Olá, tudo bem?") == UM_SEGUNDO
    caminho, _, corpo = piper.pedidos[0]
    assert caminho == "/synthesize"
    assert json.loads(corpo) == {"text": "Olá, tudo bem?"}


def test_voz_repassa_erro_do_piper(criar_raiz):
    with ServicoFalso(lambda *_: (500, "text/plain", b"voz nao carregada")) as piper:
        with pytest.raises(ServicoIndisponivel, match="Piper recusou o pedido \\(500\\)"):
            criar_voz(config_com(criar_raiz, piper=piper.url)).sintetizar("oi")


def test_voz_fala_o_nome_com_a_pronuncia(criar_raiz):
    from nora.voz import aplicar_pronuncias

    assert aplicar_pronuncias("Eu sou a Nora. NORA!", {"Nora": "Nóra"}) == "Eu sou a Nóra. Nóra!"
    assert aplicar_pronuncias("Noras e Norabela", {"Nora": "Nóra"}) == "Noras e Norabela"
    with ServicoFalso(lambda *_: (200, "audio/wav", UM_SEGUNDO)) as piper:
        config = config_com(criar_raiz, piper=piper.url, extra='[assistente]\npronuncia = "Nóra"\n')
        criar_voz(config).sintetizar("Oi, eu sou a Nora.")
        criar_voz(config_com(criar_raiz, piper=piper.url)).sintetizar("Oi, eu sou a Nora.")
    assert json.loads(piper.pedidos[0][2])["text"] == "Oi, eu sou a Nóra."
    assert json.loads(piper.pedidos[1][2])["text"] == "Oi, eu sou a Nora."  # sem pronúncia


def test_kokoro_envia_voz_e_velocidade(criar_raiz):
    with ServicoFalso(lambda *_: (200, "audio/wav", UM_SEGUNDO)) as kokoro:
        config = config_com(
            criar_raiz, piper=kokoro.url, motor="kokoro", extra="velocidade = 1.1\n"
        )
        voz = criar_voz(config)
        assert voz.sintetizar("Oi!") == UM_SEGUNDO
    caminho, _, corpo = kokoro.pedidos[0]
    assert caminho == "/synthesize"
    assert json.loads(corpo) == {"text": "Oi!", "voice": "pf_dora", "speed": 1.1}


def test_elevenlabs_monta_o_pedido_e_devolve_wav(criar_raiz, monkeypatch):
    pcm = b"\x01\x00" * 22_050
    with ServicoFalso(lambda *_: (200, "audio/pcm", pcm)) as nuvem:
        monkeypatch.setattr("nora.voz.ELEVENLABS_API", f"{nuvem.url}/v1/text-to-speech")
        config = config_com(
            criar_raiz,
            motor="elevenlabs",
            extra='[voz.elevenlabs]\nvoz_id = "abc123"\n',
            ambiente={"ELEVENLABS_API_KEY": "segredo"},
        )
        voz = criar_voz(config)
        assert isinstance(voz, VozElevenLabs)
        wav = voz.sintetizar("Olá!")
    caminho, cabecalhos, corpo = nuvem.pedidos[0]
    assert caminho == "/v1/text-to-speech/abc123?output_format=pcm_22050"
    assert {nome.lower(): valor for nome, valor in cabecalhos.items()}["xi-api-key"] == "segredo"
    assert json.loads(corpo) == {
        "text": "Olá!",
        "model_id": "eleven_flash_v2_5",
        "language_code": "pt",
    }
    assert ler_wav(wav) == (pcm, 22_050, 1)
    assert "segredo" not in repr(config)
    assert "segredo" not in repr(voz)


def test_elevenlabs_sem_chave_ou_voz(criar_raiz):
    sem_nada = criar_voz(config_com(criar_raiz, motor="elevenlabs"))
    with pytest.raises(ServicoIndisponivel, match="ELEVENLABS_API_KEY"):
        sem_nada.sintetizar("oi")
    sem_voz = criar_voz(
        config_com(criar_raiz, motor="elevenlabs", ambiente={"ELEVENLABS_API_KEY": "x"})
    )
    with pytest.raises(ServicoIndisponivel, match="voz_id"):
        sem_voz.sintetizar("oi")


def test_voz_reserva_quando_a_principal_falha(criar_raiz):
    from nora.voz import VozComReserva

    with ServicoFalso(lambda *_: (200, "audio/wav", UM_SEGUNDO)) as kokoro:
        config = config_com(
            criar_raiz,
            piper=kokoro.url,
            motor="elevenlabs",
            extra='[voz.elevenlabs]\nvoz_id = "abc"\n',
            ambiente={"ELEVENLABS_API_KEY": "x"},
            reserva="kokoro",
        )
        voz = criar_voz(config)
        assert isinstance(voz, VozComReserva)
        voz.principal.timeout = 2
        import nora.voz

        original = nora.voz.ELEVENLABS_API
        nora.voz.ELEVENLABS_API = "http://127.0.0.1:9/v1/text-to-speech"  # fora do ar
        try:
            assert voz.sintetizar("Oi!") == UM_SEGUNDO
        finally:
            nora.voz.ELEVENLABS_API = original
    assert "Usei a voz reserva" in voz.aviso
    assert "Ele está aberto?" in voz.aviso  # o motivo vem no aviso


def test_sem_reserva_ou_reserva_igual_a_principal(criar_raiz):
    config = config_com(criar_raiz, motor="kokoro", reserva="kokoro")
    assert config.voz.reserva == ""
    assert isinstance(criar_voz(config), VozHTTP)


def test_erro_de_conexao_mostra_o_motivo(criar_raiz):
    with pytest.raises(ServicoIndisponivel, match=r"127\.0\.0\.1:9 \(.+\)\. Ele está aberto\?"):
        criar_voz(config_com(criar_raiz)).sintetizar("oi")


def test_motor_de_voz_invalido(criar_raiz):
    from nora.config import ConfigError

    with pytest.raises(ConfigError, match="motor deve ser um de kokoro, piper, elevenlabs"):
        config_com(criar_raiz, motor="robo")


def test_verificar_mostra_os_servicos_de_voz(criar_raiz):
    with ServicoFalso(lambda *_: (200, "text/plain", b"")) as piper:
        assert responde(piper.url)
        linhas = verificar(config_com(criar_raiz, piper=piper.url))
    assert any("Piper" in linha and linha.endswith("ok") for linha in linhas)
    assert any("whisper-server" in linha and "não respondeu" in linha for linha in linhas)
    nuvem = verificar(config_com(criar_raiz, motor="elevenlabs"))
    assert any("ElevenLabs" in linha and "falta ELEVENLABS_API_KEY" in linha for linha in nuvem)


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
    assert f"Nora: {resposta}" in texto
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
    assert "Nora: Oi! Tudo bem por aí?" in texto
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


def test_so_teclado_responde_falando_sem_microfone(criar_raiz):
    def nao_grave(_):
        raise AssertionError("não deveria usar o microfone")

    tocados = []
    with (
        OllamaFalso(["Oi! Tudo bem?"]) as ollama,
        ServicoFalso(lambda c, cab, corpo: (200, "audio/wav", corpo)) as piper,
    ):
        config = config_com(criar_raiz, ollama.host, piper=piper.url)
        comandos = iter(["", "oi", "sair"])
        saida = io.StringIO()
        conversar_por_voz(
            config,
            entrada=lambda _: next(comandos),
            saida=saida,
            gravar=nao_grave,
            tocar=tocados.append,
            so_teclado=True,
        )
    assert "digite e ela responde falando" in saida.getvalue()
    # "Oi!" é curto demais para ir sozinho e segue junto com a frase seguinte
    assert [json.loads(a)["text"] for a in tocados] == ["Oi! Tudo bem?"]
