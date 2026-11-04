"""HUD opcional: contrato, privacidade, HTTP local e núcleo único."""

import json
from array import array
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from nora import hud
from nora.hud import PonteHUD, ServidorHUD


@pytest.fixture
def servidor(tmp_path):
    ponte = PonteHUD("Nora teste")
    pasta = tmp_path / "dist"
    pasta.mkdir()
    (pasta / "index.html").write_text("<title>Nora</title>", encoding="utf-8")
    servidor = ServidorHUD(ponte, 0, pasta).iniciar()
    try:
        yield ponte, servidor
    finally:
        servidor.parar()


def pedido(servidor, caminho, dados=None, headers=None):
    corpo = json.dumps(dados).encode() if isinstance(dados, dict) else dados
    req = Request(servidor.url + caminho, data=corpo, headers=headers or {})
    try:
        with urlopen(req, timeout=3) as resposta:
            return resposta.status, resposta.read(), dict(resposta.headers)
    except HTTPError as erro:
        return erro.code, erro.read(), dict(erro.headers)


def test_fila_limitada_e_snapshot_apos_reconectar():
    ponte = PonteHUD(capacidade=2)
    fila = ponte.assinar()
    for tipo in ("pensando", "ociosa", "ouvindo"):
        assert ponte.publicar(tipo)
    assert fila.qsize() == 2
    eventos = [fila.get_nowait(), fila.get_nowait()]
    assert [e["sequencia"] for e in eventos] == [2, 3]
    assert ponte.snapshot()["estado"] == "ouvindo"
    ponte.remover(fila)
    assert len(ponte._filas) == 0
    for _ in range(8):
        ponte.assinar()
    with pytest.raises(ValueError):
        ponte.assinar()


@pytest.mark.parametrize(
    "tipo,dados",
    [
        ("inexistente", {}),
        ("ouvindo", {"chave": "segredo"}),
        ("nivel_audio", {"nivel": True, "fonte": "voz"}),
        ("nivel_audio", {"nivel": float("nan"), "fonte": "voz"}),
        ("nivel_audio", {"nivel": 2, "fonte": "voz"}),
        ("nivel_audio", {"nivel": 0.4, "fonte": "arquivo"}),
        ("modelo_ativo", {"modelo": "x" * 201}),
        ("texto_visivel", {"texto": "x" * 70000}),
    ],
)
def test_contrato_rejeita_eventos_invalidos(tipo, dados):
    ponte = PonteHUD()
    assert not ponte.publicar(tipo, **dados)
    assert ponte.snapshot()["sequencia"] == 0


def test_texto_exige_consentimento_e_ocultar_limpa_filas():
    ponte = PonteHUD()
    fila = ponte.assinar()
    assert ponte.snapshot()["privacidade"]
    assert not ponte.publicar("texto_visivel", texto="conteúdo sintético")
    ponte.privacidade(True)
    assert ponte.publicar("texto_visivel", texto="conteúdo sintético")
    assert ponte.snapshot()["texto"] == "conteúdo sintético"
    ponte.privacidade(False)
    assert ponte.snapshot()["texto"] == ""
    assert fila.qsize() == 1
    evento = fila.get_nowait()
    assert evento["tipo"] == "privacidade" and evento["dados"]["privacidade"]
    assert not ponte.publicar("texto_visivel", texto="outra mensagem")
    assert PonteHUD().snapshot()["privacidade"]  # outra sessão não herda o opt-in


@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "https://hostil.example"},
        {"Host": "hostil.example"},
        {"Sec-Fetch-Site": "cross-site"},
        {"Sec-Fetch-Site": "same-site"},
    ],
)
def test_host_origem_e_dns_rebinding_rejeitados(servidor, headers):
    _, http = servidor
    assert pedido(http, "/api/sessao", headers=headers)[0] == 403


def test_mutacoes_exigem_token_e_consentimento_estrito(servidor):
    ponte, http = servidor
    assert pedido(http, "/api/privacidade", {"visivel": True})[0] == 403
    _, corpo, headers = pedido(http, "/api/sessao")
    assert headers["Cache-Control"] == "no-store"
    token = json.loads(corpo)["token"]
    cab = {"X-Nora-Token": token}
    assert pedido(http, "/api/privacidade", {"visivel": True}, cab)[0] == 200
    assert not ponte.snapshot()["privacidade"]
    assert pedido(http, "/api/privacidade", {"visivel": False}, cab)[0] == 200
    assert ponte.snapshot()["privacidade"]
    assert pedido(http, "/api/privacidade", b" " * 2049, cab)[0] == 400
    assert (
        pedido(
            http, "/api/privacidade", {"visivel": True}, {**cab, "Origin": "https://hostil.example"}
        )[0]
        == 403
    )
    assert (
        pedido(http, "/api/decisao", {"id": 1, "acao": "publicar", "confirmar": True}, cab)[0]
        == 400
    )


def test_http_loopback_estatico_sem_traversal_e_nucleo_desconectado(servidor):
    _, http = servidor
    assert http.http.server_address[0] == "127.0.0.1"
    assert pedido(http, "/")[0] == 200
    assert pedido(http, "/../../pyproject.toml")[0] == 404
    assert pedido(http, "/api/inexistente")[0] == 404
    _, corpo, _ = pedido(http, "/api/estado")
    assert json.loads(corpo)["conectado"] is False


def test_sse_inicia_com_snapshot_autoritativo_e_encerra_sem_afetar_ponte(servidor):
    ponte, http = servidor
    ponte.publicar("pensando")
    resposta = urlopen(http.url + "/api/eventos", timeout=3)
    try:
        assert resposta.headers["Content-Type"] == "text/event-stream"
        assert resposta.readline().decode().strip() == "id: 1"
        evento = json.loads(resposta.readline().decode().removeprefix("data: "))
        assert evento["tipo"] == "conectado"
        assert evento["dados"] == ponte.snapshot()
        assert evento["dados"]["conectado"] is False
    finally:
        resposta.close()
    assert ponte.publicar("ociosa")


def test_microfone_rms_real_limite_de_taxa_e_sem_wav(monkeypatch):
    ponte = PonteHUD()
    monkeypatch.setattr(hud, "_ponte", ponte)
    hud.nivel_pcm(array("h", [16384, -16384] * 40).tobytes(), "microfone")
    assert ponte.snapshot()["nivel_audio"] == pytest.approx(0.5)
    sequencia = ponte.snapshot()["sequencia"]
    for _ in range(20):
        hud.nivel_pcm(b"\0\0" * 20, "microfone")
    assert ponte.snapshot()["sequencia"] == sequencia
    assert "amostras" not in json.dumps(ponte.snapshot())


def test_publicar_nunca_espera_a_trava():
    import threading

    ponte = PonteHUD()
    pronto, liberar = threading.Event(), threading.Event()

    def segurar():
        with ponte._trava:
            pronto.set()
            liberar.wait(3)

    thread = threading.Thread(target=segurar)
    thread.start()
    assert pronto.wait(1)
    try:
        assert not ponte.publicar("ouvindo")
    finally:
        liberar.set()
        thread.join()


def test_erro_de_observador_nao_interrompe_conversa(criar_raiz, monkeypatch):
    from test_roteador import montar

    from nora.conversa import nova_conversa

    class PonteDefeituosa:
        def publicar(self, *a, **kw):
            raise RuntimeError("falha de apresentação")

        def anexar(self, *a, **kw):
            raise RuntimeError("falha de apresentação")

    monkeypatch.setattr(hud, "_ponte", PonteDefeituosa())
    roteador, _ = montar(criar_raiz)
    conversa = nova_conversa(roteador.config, roteador, memoria=None, notas=None)
    assert "Resposta local" in "".join(conversa.perguntar("oi"))
    assert not conversa.ocupada


def test_decisao_usa_dominio_e_nao_publica(criar_raiz):
    from datetime import datetime

    from nora.config import carregar
    from nora.melhorias import Melhorias

    m = Melhorias(carregar(criar_raiz(), ambiente={}))
    agora = datetime(2026, 11, 3, 21)
    for i in range(3):
        m.observador.registrar("llm", "timeout", "local", f"sintetico-{i}", quando=agora)
    m.fechar(agora.date(), agora)
    ponte = PonteHUD()
    ponte.conversa = SimpleNamespace(melhorias=m)
    id_ = ponte.propostas()[0]["id"]
    with pytest.raises(ValueError):
        ponte.decidir({"id": id_, "acao": "aprovar", "confirmar": False})
    assert ponte.decidir({"id": id_, "acao": "aprovar", "confirmar": True})["status"] == "aprovada"
    assert (m.pasta / "tarefas" / f"melhoria-{id_}.md").is_file()
    assert m.proposta(id_).status != "publicada"
    with pytest.raises(ValueError):
        ponte.decidir({"id": id_, "acao": "aprovar", "confirmar": True})


def test_notas_somente_usadas_autorizadas_e_com_consentimento(tmp_path):
    raiz = tmp_path / "notas"
    raiz.mkdir()
    ponte = PonteHUD()
    ponte.conversa = SimpleNamespace(
        config=SimpleNamespace(notas=SimpleNamespace(pasta=str(raiz))),
        trechos_de_notas=[
            SimpleNamespace(caminho="nota.md", titulo="Título"),
            SimpleNamespace(caminho="../fora.md", titulo="Fora"),
        ],
    )
    assert ponte.notas() == []
    ponte.privacidade(True)
    assert ponte.notas() == [{"titulo": "Título", "caminho": "nota.md"}]


def test_contrato_json_versionado_e_campos_publicos():
    contrato = json.loads(Path(hud.__file__).with_name("hud_contrato.json").read_text())
    assert contrato["versao"] == 1
    assert set(contrato["campos"]) == set(hud.CAMPOS)
    assert not {"api_key", "audio", "prompt", "pensamento"} & {
        campo for campos in contrato["campos"].values() for campo in campos
    }


def test_porta_ocupada_nao_interrompe_escuta(criar_raiz, monkeypatch):
    from nora import maos_livres
    from nora.config import carregar

    def indisponivel(*args):
        raise OSError("porta ocupada")

    chamadas = []
    monkeypatch.setattr(hud, "ServidorHUD", indisponivel)
    monkeypatch.setattr(
        maos_livres, "conversar_maos_livres", lambda config, **kw: chamadas.append(kw) or 0
    )
    assert hud.executar(carregar(criar_raiz(), ambiente={}), ouvir=True, medir=True) == 0
    assert chamadas == [{"medir": True}]
    assert hud.executar(carregar(criar_raiz(), ambiente={})) == 1


def test_falando_somente_no_callback_real_de_saida(monkeypatch):
    from nora import audio

    ponte = PonteHUD()
    monkeypatch.setattr(hud, "_ponte", ponte)
    estados = []

    class SaidaFalsa:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            estados.append(ponte.snapshot()["estado"])

        def __enter__(self):
            saida = bytearray(8)
            self.kwargs["callback"](saida, 4, None, None)
            estados.append(ponte.snapshot()["estado"])
            assert ponte.snapshot()["nivel_audio"] == pytest.approx(0.5)
            # O fim do LLM não pode anunciar repouso enquanto o áudio está tocando.
            assert not ponte.publicar("ociosa")
            self.kwargs["finished_callback"]()
            return self

        def __exit__(self, *args):
            return False

    sd = SimpleNamespace(RawOutputStream=SaidaFalsa)
    audio._tocar(sd, array("h", [16384] * 4).tobytes(), 16000, 1, None)
    assert estados == ["desconectado", "falando"]
    assert ponte.snapshot()["estado"] == "ouvindo"


def test_configuracao_hud_opcional_na_cli(criar_raiz, monkeypatch):
    from nora import cli
    from nora.config import carregar

    config = carregar(criar_raiz(), ambiente={})
    chamadas = []
    monkeypatch.setattr(cli, "carregar", lambda: config)
    monkeypatch.setattr(hud, "executar", lambda cfg, **kw: chamadas.append(kw) or 0)
    assert cli.main(["ouvir", "--hud", "--hud-porta", "9876"]) == 0
    assert chamadas[-1]["ouvir"] and chamadas[-1]["porta"] == 9876
    assert cli.main(["hud", "--porta", "9877"]) == 0
    assert chamadas[-1] == {"porta": 9877}


def test_texto_se_recupera_de_fila_lenta_sem_perder_pedacos():
    ponte = PonteHUD(capacidade=1)
    ponte.privacidade(True)
    fila = ponte.assinar()
    for pedaco in ("Um ", "texto ", "completo."):
        ponte.publicar("texto_visivel", texto=pedaco, acumular=True)
    evento = fila.get_nowait()
    assert evento["dados"] == {"texto": "Um texto completo.", "acumular": False}


def test_unicode_maximo_cabe_no_envelope_sse_e_snapshot(tmp_path):
    simbolo = "😀"
    ponte = PonteHUD(simbolo * 200)
    ponte.privacidade(True)
    assert ponte.publicar("texto_visivel", texto=simbolo * 6000)
    for tipo, campo in (
        ("modelo_ativo", "modelo"),
        ("origem_resposta", "origem"),
        ("voz_ativa", "motor"),
        ("emocao", "nome"),
    ):
        assert ponte.publicar(tipo, **{campo: simbolo * 200})
    notas = [{"titulo": simbolo * 200, "caminho": simbolo * 500} for _ in range(12)]
    assert ponte.publicar("notas", notas=notas)
    http = ServidorHUD(ponte, 0, tmp_path).iniciar()
    try:
        _, corpo, _ = pedido(http, "/api/estado")
        assert len(corpo) < hud.LIMITE_EVENTO
        assert json.loads(corpo)["texto"] == simbolo * 6000
        with urlopen(http.url + "/api/eventos", timeout=3) as resposta:
            resposta.readline()  # id
            linha = resposta.readline()
            assert len(linha) < hud.LIMITE_EVENTO
            evento = json.loads(linha.decode().removeprefix("data: "))
            assert evento["dados"]["texto"] == simbolo * 6000
    finally:
        http.parar()
    assert not ponte.publicar("texto_visivel", texto=simbolo * 17000)


def test_javascript_nao_depende_de_registro_mime_do_windows(servidor, monkeypatch):
    _, http = servidor
    (http.pasta / "asset.js").write_text("export {};", encoding="utf-8")
    monkeypatch.setattr(hud.mimetypes, "guess_type", lambda _: ("text/plain", None))
    status, corpo, headers = pedido(http, "/asset.js")
    assert status == 200 and corpo == b"export {};"
    assert headers["Content-Type"] == "text/javascript"
    assert headers["X-Content-Type-Options"] == "nosniff"
