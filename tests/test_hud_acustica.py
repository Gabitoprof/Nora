"""Sinais sintéticos, tempo real do áudio, privacidade e limites da HUD."""

import json
import math
import queue
import threading
import time
from array import array
from types import SimpleNamespace

import pytest

from nora import acustica, audio, hud
from nora.acustica import EnvelopeTemporal, Medidor, temporizar
from nora.hud_audio import contexto_fala


def tom(hz=440, amplitude=0.5, segundos=0.1, taxa=16000, canais=1):
    return array(
        "h",
        [
            int(32767 * amplitude * math.sin(2 * math.pi * hz * i / taxa))
            for i in range(round(segundos * taxa))
            for _ in range(canais)
        ],
    ).tobytes()


def esperar(teste, prazo=2):
    fim = time.monotonic() + prazo
    while time.monotonic() < fim:
        if teste():
            return
        time.sleep(0.005)
    assert teste(), "Evento acústico não chegou no prazo"


@pytest.fixture
def ponte(monkeypatch):
    p = hud.PonteHUD()
    monkeypatch.setattr(hud, "_ponte", p)
    yield p
    if p._audio is not None:
        p._audio.encerrar()


@pytest.mark.parametrize("taxa", [16000, 22050, 44100, 48000])
@pytest.mark.parametrize(
    "hz,faixa", [(100, 0), (350, 1), (800, 2), (1800, 3), (3500, 4), (7000, 5)]
)
def test_bandas_energia_e_centroide_na_taxa_real(taxa, hz, faixa):
    dados = Medidor().medir(tom(hz, taxa=taxa), taxa)
    assert max(range(6), key=dados["bandas"].__getitem__) == faixa
    assert sum(dados["bandas"]) == pytest.approx(1, abs=1e-5)
    assert dados["rms"] == pytest.approx(0.5 / math.sqrt(2), abs=0.02)
    assert dados["centroide"] == pytest.approx(hz / (taxa / 2), abs=0.025)


def test_picos_amplitude_envelope_pausa_e_retomada():
    medidor = Medidor()
    baixo = medidor.medir(tom(amplitude=0.2), 16000)
    alto = medidor.medir(tom(amplitude=0.8), 16000)
    assert alto["rms"] == pytest.approx(baixo["rms"] * 4, abs=0.001)
    assert alto["pico"] > 0.79
    assert baixo["envelope"] < alto["envelope"] < alto["rms"]
    pausa = medidor.medir(bytes(3200), 16000)
    assert pausa["rms"] == pausa["pico"] == 0
    assert 0 < pausa["envelope"] < alto["envelope"]
    assert pausa["bandas"] == [0] * 6
    for _ in range(30):
        pausa = medidor.medir(bytes(3200), 16000)
    assert pausa["envelope"] < 0.001
    assert medidor.medir(tom(amplitude=0.8), 16000)["envelope"] > 0.3


def test_fallback_sem_numpy_e_janela_limitada(monkeypatch):
    monkeypatch.setattr(acustica, "_numpy", False)
    tamanhos, fft = [], acustica._fft

    def medir(x):
        tamanhos.append(len(x))
        return fft(x)

    monkeypatch.setattr(acustica, "_fft", medir)
    pcm = tom(800, segundos=3, taxa=48000, canais=2)
    dados = Medidor().medir(pcm, 48000, 2)
    assert len(acustica.mono(pcm, 2)) == 2048
    assert max(tamanhos) == 512
    assert dados["rms"] == pytest.approx(0.5 / math.sqrt(2), abs=0.01)
    assert max(range(6), key=dados["bandas"].__getitem__) == 2


def test_palavras_estimadas_usam_duracao_pausas_e_nao_tags():
    pcm = bytes(16000) + tom(segundos=0.4) + bytes(16000) + tom(segundos=0.4) + bytes(16000)
    dados = temporizar("{alegre} Primeiro segundo", pcm, 16000, 1)
    assert dados["duracao_ms"] == 2300 and dados["precisao"] == "estimada"
    a, b = dados["palavras"]
    assert (a["texto"], b["texto"]) == ("Primeiro", "segundo")
    assert 500 <= a["inicio_ms"] < a["fim_ms"] <= b["inicio_ms"] < b["fim_ms"] <= 1800
    assert a["destaque"] and b["destaque"]
    assert temporizar("Só silêncio", bytes(32000), 16000, 1) is None
    assert temporizar("a" * 81, tom(), 16000, 1) is None
    assert temporizar("palavra " * 257, tom(), 16000, 1) is None


def test_envelope_incremental_equivale_pcm_sem_gravacao():
    pcm = bytes(3200) + tom(segundos=0.4) + bytes(3200)
    envelope = EnvelopeTemporal(16000, 1)
    for i in range(0, len(pcm), 222):
        envelope.alimentar(pcm[i : i + 222])
        assert len(envelope.sobra) < envelope.largura
    assert envelope.finalizar("Palavras sintéticas.") == temporizar(
        "Palavras sintéticas.", pcm, 16000, 1
    )
    assert all(type(v) is float for v in envelope.rms)


def test_microfone_usa_taxa_nativa_e_preserva_saida_stt(monkeypatch):
    micro = audio.Microfone.__new__(audio.Microfone)
    micro._fila = queue.Queue()
    micro._taxa, micro._canais = 48000, 2
    pcm = tom(3500, segundos=0.06, taxa=48000, canais=2)
    micro._fila.put(pcm)
    medidas = []
    monkeypatch.setattr(hud, "amostrar_pcm", lambda *args: medidas.append(args))
    convertido = next(micro.blocos())
    assert medidas == [(pcm, "microfone", 48000, 2)]
    assert convertido == audio.reamostrar(audio._para_mono(pcm, 2), 48000)


def test_microfone_async_so_transmite_caracteristicas(ponte):
    hud.amostrar_pcm(tom(3500), "microfone")
    esperar(lambda: ponte.estado["acustica"] is not None)
    dados = ponte.snapshot()["acustica"]
    assert dados["fonte"] == "microfone"
    assert dados["posicao_ms"] == dados["duracao_ms"] == dados["reproducao_id"] == 0
    assert max(range(6), key=dados["bandas"].__getitem__) == 4
    assert all(p not in json.dumps(ponte.snapshot()) for p in ("amostras", "pcm", "WAV", "api_key"))


def iniciar(ponte, texto="{calma} Uma frase real.", pcm=None, taxa=16000):
    ponte.privacidade(True)
    pcm = pcm if pcm is not None else tom(segundos=0.5, taxa=taxa)
    with contexto_fala(texto):
        obs = hud.preparar_reproducao(pcm, taxa, 1)
    hud.reproducao(True)
    obs.entregar(0, len(pcm) // 2)
    return obs


def test_posicao_avanca_por_pcm_e_emocao_nao_adianta_proxima_frase(ponte):
    obs = iniciar(ponte, taxa=48000)
    esperar(lambda: ponte.estado["fala_temporizada"] is not None)
    esperar(lambda: ponte.estado["acustica"] and ponte.estado["acustica"]["posicao_ms"] > 100)
    assert ponte.estado["acustica"]["duracao_ms"] == 500
    assert ponte.estado["fala_temporizada"]["id"] == obs.id
    assert ponte.estado["emocao"] == "calma"
    hud.emitir("emocao", nome="triste")
    assert ponte.estado["emocao"] == "calma"
    antigo = ponte.estado["acustica"].copy()
    hud.reproducao(False)
    assert ponte.estado["fala_temporizada"] is None
    assert ponte.estado["acustica"]["ativo"] is False
    assert ponte.estado["nivel_audio"] == 0
    assert not ponte.publicar("acustica", **antigo)
    assert obs.pcm == b""


def test_dac_futuro_e_silencio_interno_nao_antecipam_som(ponte):
    pcm = bytes(3200) + tom(segundos=0.3) + bytes(3200)
    obs = hud.preparar_reproducao(pcm, 16000, 1)
    hud.reproducao(True)
    obs.entregar(0, len(pcm) // 2, SimpleNamespace(outputBufferDacTime=1.1, currentTime=1.0))
    time.sleep(0.04)
    assert ponte.estado["acustica"] is None
    esperar(lambda: ponte.estado["acustica"] is not None)
    assert ponte.estado["acustica"]["rms"] == 0 and ponte.estado["acustica"]["ativo"]
    esperar(lambda: ponte.estado["acustica"]["rms"] > 0.1)
    assert ponte.estado["acustica"]["ativo"]
    hud.reproducao(False)


def test_privacidade_epoca_nao_revela_frase_apos_reoptin(ponte):
    ponte.privacidade(True)
    with contexto_fala("Conteúdo sintético privado"):
        obs = hud.preparar_reproducao(tom(segundos=0.4), 16000, 1)
    ponte.privacidade(False)
    ponte.privacidade(True)
    hud.reproducao(True)
    obs.entregar(0, 6400)
    esperar(lambda: ponte.estado["acustica"] is not None)
    assert ponte.estado["fala_temporizada"] is None
    hud.reproducao(False)
    novo = iniciar(ponte)
    esperar(lambda: ponte.estado["fala_temporizada"] is not None)
    assert novo.id > obs.id
    fila = ponte.assinar()
    ponte.privacidade(False)
    assert ponte.estado["fala_temporizada"] is None and fila.qsize() == 1
    hud.reproducao(False)


def test_callback_limitado_sem_fft_e_publicacao_20hz(ponte, monkeypatch):
    chamadas, medir = [], Medidor.medir

    def medir_fora(self, *args, **kwargs):
        chamadas.append(threading.current_thread().name)
        return medir(self, *args, **kwargs)

    monkeypatch.setattr(Medidor, "medir", medir_fora)
    obs = hud.preparar_reproducao(tom(segundos=0.6), 16000, 1)
    hud.reproducao(True)
    futuro = SimpleNamespace(outputBufferDacTime=2, currentTime=1)
    for i in range(100):
        obs.entregar(i, 9600, futuro)
    assert len(obs.entregas) <= 4 and not chamadas
    obs.entregas.clear()
    fila = ponte.assinar()
    obs.entregar(0, 9600)
    time.sleep(0.26)
    assert set(chamadas) == {"nora-hud-acustica"}
    assert 1 <= sum(e["tipo"] == "acustica" for e in list(fila.queue)) <= 6
    hud.reproducao(False)
    assert not ponte.estado["acustica"]["ativo"]


def test_erro_saida_limpa_estado_e_buffer(ponte):
    def falhar(**_):
        raise RuntimeError("saída sintética indisponível")

    with pytest.raises(RuntimeError, match="sintética"):
        audio._tocar(SimpleNamespace(RawOutputStream=falhar), tom(), 16000, 1, None)
    assert not ponte._reproduzindo and ponte._audio.reproducao.pcm == b""


def test_silencio_inicial_e_taxa_final_constam_na_estimativa(ponte):
    ponte.privacidade(True)
    pcm, taxa, _ = audio.ler_wav(audio.com_silencio_inicial(audio.para_wav(tom(segundos=0.3)), 200))
    pcm = audio.reamostrar(pcm, taxa, 48000)
    with contexto_fala("Uma frase."):
        obs = hud.preparar_reproducao(pcm, 48000, 1)
    esperar(lambda: obs.tempos is not None)
    assert obs.tempos["duracao_ms"] == 500
    assert obs.tempos["palavras"][0]["inicio_ms"] >= 200


def _dados(ponte):
    return dict(
        fonte="voz",
        ativo=True,
        reproducao_id=ponte._id_reproducao,
        posicao_ms=100,
        duracao_ms=1000,
        rms=0.3,
        pico=0.5,
        envelope=0.2,
        bandas=[0, 0, 1, 0, 0, 0],
        centroide=0.1,
        fluxo=0.4,
    )


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("rms", float("nan")),
        ("pico", True),
        ("envelope", -1),
        ("bandas", [0.2] * 7),
        ("bandas", [0.2] * 5 + [float("inf")]),
        ("ativo", 1),
        ("posicao_ms", 1001),
        ("duracao_ms", 600001),
        ("reproducao_id", True),
        ("fonte", "arquivo"),
    ],
)
def test_contrato_acustico_rejeita_invalido(ponte, campo, valor):
    iniciar(ponte)
    assert not ponte.publicar("acustica", **{**_dados(ponte), campo: valor})
    hud.reproducao(False)


def test_contrato_temporal_privacidade_ordem_limite(ponte):
    obs = hud.preparar_reproducao(tom(segundos=1), 16000, 1)
    hud.reproducao(True)
    dados = dict(
        id=obs.id,
        duracao_ms=1000,
        precisao="estimada",
        palavras=[dict(texto="Olá", inicio_ms=100, fim_ms=400, destaque=False)],
    )
    assert not ponte.publicar("fala_temporizada", **dados)
    ponte.privacidade(True)
    assert ponte.publicar("fala_temporizada", **dados)
    assert not ponte.publicar("fala_temporizada", **{**dados, "palavras": []})
    assert not ponte.publicar("fala_temporizada", **{**dados, "id": obs.id + 1})
    assert not ponte.publicar("fala_temporizada", **{**dados, "pcm": "não"})
    sobreposta = {
        **dados,
        "palavras": [
            *dados["palavras"],
            dict(texto="sobreposta", inicio_ms=300, fim_ms=500, destaque=False),
        ],
    }
    assert not ponte.publicar("fala_temporizada", **sobreposta)
    hud.reproducao(False)
    assert not ponte.publicar("fala_temporizada", **dados)


def test_jogo_persiste_durante_fala_e_sai_na_desconexao(ponte):
    ponte.conversa = SimpleNamespace(cerebro=SimpleNamespace(jogo=True), ocupada=False)
    ponte.publicar("modo_jogo")
    iniciar(ponte)
    assert ponte.estado["estado"] == "falando" and ponte.estado["jogo"] is True
    hud.reproducao(False)
    assert ponte.estado["estado"] == "modo_jogo"
    ponte.publicar("desconectado")
    assert ponte.estado["jogo"] is False


def test_snapshot_nao_reanima_pcm_antigo_e_limita_unicode(ponte):
    iniciar(ponte)
    ponte.publicar("acustica", **_dados(ponte))
    ponte.publicar("texto_visivel", texto="😀" * 6000)
    ponte.publicar("notas", notas=[dict(titulo="😀" * 200, caminho="😀" * 500) for _ in range(12)])
    palavras = [
        dict(texto="😀" * 60, inicio_ms=i * 5, fim_ms=(i + 1) * 5, destaque=False)
        for i in range(100)
    ]
    assert ponte.publicar(
        "fala_temporizada",
        id=ponte._id_reproducao,
        duracao_ms=1000,
        precisao="estimada",
        palavras=palavras,
    )
    assert ponte.snapshot()["fala_temporizada"] is None
    assert len(json.dumps(ponte.snapshot(), ensure_ascii=False).encode()) < hud.LIMITE_EVENTO
    ponte._ultimo_quadro = time.monotonic() - 1
    assert ponte.snapshot()["acustica"] is None
    hud.reproducao(False)


class SaidaFalsa:
    """sounddevice falso: chama o callback de saída em blocos, como a placa de som."""

    PortAudioError = RuntimeError

    class CallbackStop(Exception):
        pass

    def __init__(self):
        self.tocado = bytearray()

    def RawOutputStream(self, callback, finished_callback, channels, **_):  # noqa: N802
        dono = self

        class Fluxo:
            def __enter__(self):
                while True:
                    saida = bytearray(512 * 2 * channels)
                    try:
                        callback(saida, 512, None, None)
                    except dono.CallbackStop:
                        dono.tocado.extend(saida)
                        break
                    dono.tocado.extend(saida)
                finished_callback()
                return self

            def __exit__(self, *args):
                pass

        return Fluxo()


def test_falha_da_hud_e_contada_e_a_fala_continua(ponte, monkeypatch, caplog):
    from nora import falhas_hud

    falhas_hud.zerar()

    class ObservadorQuebrado:
        def entregar(self, *args):
            raise ValueError("texto pessoal que não pode ir para o log")

    monkeypatch.setattr(hud, "preparar_reproducao", lambda *a: ObservadorQuebrado())
    som = tom(segundos=0.2)
    saida = SaidaFalsa()
    with caplog.at_level("WARNING", logger="nora.hud"):
        audio._tocar(saida, som, 16000, 1, None)
        audio._tocar(saida, som, 16000, 1, None)
    # o áudio inteiro foi para o alto-falante, nas duas vezes, apesar da HUD quebrada
    assert bytes(saida.tocado[: len(som)]) == som
    contagem = falhas_hud.contagem()
    assert contagem["audio.entregar: ValueError"] >= 2
    linhas = [r.getMessage() for r in caplog.records if "audio.entregar" in r.getMessage()]
    assert len(linhas) == 1  # uma linha por tipo; as próximas só contam
    assert "texto pessoal" not in caplog.text  # nunca a mensagem do erro


def test_falha_no_observador_em_streaming_e_contada(ponte, monkeypatch):
    from nora import falhas_hud

    falhas_hud.zerar()

    class Quebrado:
        def __getattr__(self, nome):
            def falhar(*args):
                raise KeyError(nome)

            return falhar

    monkeypatch.setattr(hud, "preparar_reproducao", lambda *a: Quebrado())
    som = tom(segundos=0.1)
    saida = SaidaFalsa()
    audio._tocar_partes(saida, audio.AudioEmPartes(iter([som]), 16000), 0, None)
    assert bytes(saida.tocado).startswith(som)
    assert any(k.startswith("audio.") for k in falhas_hud.contagem())


def test_registro_de_falha_nunca_levanta(monkeypatch):
    from nora import falhas_hud

    monkeypatch.setattr(falhas_hud, "_contagem", None)  # até o contador quebrado
    falhas_hud.registrar("qualquer", RuntimeError("x"))


# --- end of playback (reproducao_encerrada) -----------------------------------------------------


def _eventos(fila, tipo):
    return [e["dados"] for e in list(fila.queue) if e["tipo"] == tipo]


def test_fim_natural_avisa_a_hud_com_posicao_igual_a_duracao(ponte):
    fila = ponte.assinar()
    som = tom(segundos=0.2)
    audio._tocar_partes(SaidaFalsa(), audio.AudioEmPartes(iter([som]), 16000), 0, None)
    fim = _eventos(fila, "reproducao_encerrada")
    assert len(fim) == 1 and fim[0]["interrompida"] is False
    assert fim[0]["posicao_ms"] == fim[0]["duracao_ms"] == pytest.approx(200, abs=1)
    assert fim[0]["id"] == ponte._id_reproducao
    assert set(fim[0]) == {"id", "posicao_ms", "duracao_ms", "interrompida"}  # sem texto


def test_barge_in_avisa_interrompida_antes_do_fim(ponte):
    fila = ponte.assinar()
    som, por, fechar = audio.AudioEmPartes.de_fila(16000)
    por(tom(segundos=0.3))

    class Cortar(SaidaFalsa):
        def RawOutputStream(self, callback, finished_callback, channels, **_):  # noqa: N802
            chamadas = [0]

            def cortar(saida, quadros, tempo, status):
                chamadas[0] += 1
                if chamadas[0] == 3:
                    som.cancelar()
                return callback(saida, quadros, tempo, status)

            return SaidaFalsa.RawOutputStream(self, cortar, finished_callback, channels)

    threading.Timer(0.5, fechar).start()
    audio._tocar_partes(Cortar(), som, 0, None)
    fim = _eventos(fila, "reproducao_encerrada")
    assert len(fim) == 1 and fim[0]["interrompida"] is True
    assert fim[0]["posicao_ms"] < fim[0]["duracao_ms"]


def test_wav_inteiro_e_natural(ponte):
    fila = ponte.assinar()
    audio._tocar(SaidaFalsa(), tom(segundos=0.1), 16000, 1, None)
    fim = _eventos(fila, "reproducao_encerrada")
    assert len(fim) == 1 and fim[0]["interrompida"] is False
    assert fim[0]["posicao_ms"] == fim[0]["duracao_ms"]


def test_contrato_rejeita_fim_invalido_ou_antigo(ponte):
    hud.preparar_reproducao(tom(segundos=0.1), 16000, 1)
    hud.reproducao(True)
    atual = ponte._id_reproducao
    valido = {"id": atual, "posicao_ms": 10.0, "duracao_ms": 20.0, "interrompida": False}
    assert not ponte.publicar("reproducao_encerrada", **{**valido, "posicao_ms": 30.0})
    assert not ponte.publicar("reproducao_encerrada", **{**valido, "interrompida": 1})
    assert not ponte.publicar("reproducao_encerrada", **{**valido, "texto": "oi"})
    assert not ponte.publicar("reproducao_encerrada", **{**valido, "id": atual + 1})
    assert ponte.publicar("reproducao_encerrada", **valido)
    hud.reproducao(False)


def test_sem_som_nao_avisa_fim(ponte):
    fila = ponte.assinar()
    hud.reproducao(False, (0.0, 0.0, False))  # nunca começou a tocar
    assert not _eventos(fila, "reproducao_encerrada")


def test_privado_nao_guarda_palavras_alinhadas_no_backend(ponte):
    palavras = [{"texto": "segredo", "inicio_ms": 0.0, "fim_ms": 100.0, "destaque": False}]
    ponte.privacidade(False)  # Privado
    obs = hud.preparar_reproducao(None, 16000, 1)
    obs.alinhar(palavras)
    assert obs.tempos is None
    ponte.privacidade(True)  # liberou depois que a fala começou: época antiga, continua sem
    obs.alinhar(palavras)
    assert obs.tempos is None
    novo = hud.preparar_reproducao(None, 16000, 1)  # fala nova, já liberada
    novo.alinhar(palavras)
    assert novo.tempos["precisao"] == "alinhada"
