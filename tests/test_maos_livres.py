import io
import json

import pytest
from fake_ollama import OllamaFalso
from fake_servico import ServicoFalso

from nora.ativacao import e_despedida, extrair_pedido, normalizar
from nora.config import carregar
from nora.maos_livres import conversar_maos_livres
from nora.vad import BYTES_POR_QUADRO, DetectorDeFala, em_quadros, falas

# --- palavra de ativação ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("texto", "pedido"),
    [
        ("Nora, que horas são?", "que horas são?"),
        ("nora que horas são", "que horas são"),
        ("NORA! Liga a luz.", "Liga a luz."),
        ("Oi, Nora, tudo bem?", "tudo bem?"),
        ("Ei Norah... me lembra de beber água", "me lembra de beber água"),
        ("Nora.", ""),
        ("Nóra, bom dia", "bom dia"),
        ("Que horas são, Nora?", None),
        ("A Nora é legal", None),
        ("Noras e genros", None),
        ("Ela foi embora", None),
        ("", None),
    ],
)
def test_extrai_o_pedido_depois_do_nome(texto, pedido):
    assert extrair_pedido(texto, "Nora") == pedido


def test_palavra_de_ativacao_com_mais_de_uma_palavra():
    assert extrair_pedido("Oi Nora, abre a agenda", "Oi Nora") == "abre a agenda"
    assert extrair_pedido("Nora, abre a agenda", "Oi Nora") is None


def test_despedidas_e_normalizacao():
    assert normalizar("Até   LOGO!") == "ate logo"
    assert e_despedida("Tchau!")
    assert e_despedida("Obrigado, é só isso.")
    assert not e_despedida("tchau para quem?")


# --- detector de fala ---------------------------------------------------------------------------


def quadro(valor):
    return bytes([valor, 0]) * (BYTES_POR_QUADRO // 2)


def test_detector_junta_a_fala_com_um_pouco_de_antes_e_o_silencio_final():
    detector = DetectorDeFala(limiar=0.5, silencio_ms=96, antes_ms=64, minimo_ms=64)
    entrada = [(1, 0.1)] * 3 + [(2, 0.9)] * 4 + [(3, 0.1)] * 3 + [(4, 0.1)] * 2
    saidas = [detector.alimentar(quadro(v), chance) for v, chance in entrada]
    completas = [s for s in saidas if s]
    assert len(completas) == 1
    valores = completas[0][::BYTES_POR_QUADRO]
    assert list(valores) == [1, 1, 2, 2, 2, 2, 3, 3, 3]  # 2 quadros de antes + fala + silêncio
    assert not detector.em_fala


def test_detector_ignora_estalo_curto_e_corta_fala_longa_demais():
    curto = DetectorDeFala(silencio_ms=64, minimo_ms=128)
    entrada = [0.9, 0.1, 0.1]
    assert not any(curto.alimentar(quadro(1), c) for c in entrada)

    longo = DetectorDeFala(silencio_ms=1000, maximo_s=0.32)  # 10 quadros
    saidas = [longo.alimentar(quadro(1), 0.9) for _ in range(12)]
    assert saidas.index(next(s for s in saidas if s)) == 9


def test_quadros_e_falas_de_blocos_irregulares():
    blocos = [b"\x01\x00" * 300, b"\x01\x00" * 800, b"\x00\x00" * 2000]
    quadros = list(em_quadros(blocos))
    assert all(len(q) == BYTES_POR_QUADRO for q in quadros)
    assert len(quadros) == (300 + 800 + 2000) // 512

    class VadFalso:
        def probabilidade(self, q):
            return 0.9 if q[0] else 0.0

    detectadas = list(falas(quadros, VadFalso(), DetectorDeFala(silencio_ms=64, minimo_ms=32)))
    assert len(detectadas) == 1


# --- conversa mãos livres -----------------------------------------------------------------------


def test_conversa_maos_livres(criar_raiz):
    transcricoes = iter(
        [
            "Música alta tocando",  # ignorada: não chamou a Nora
            "Nora, qual é a capital do Brasil?",
            "E da Argentina?",  # dentro da janela: não precisa do nome
            "E do Chile?",  # fora da janela: ignorada
            "Nora",  # só o nome
            "Tchau",  # despedida dentro da janela
        ]
    )
    # cada consulta ao relógio: ignorada, fim da 1ª resposta, continuação, fim da 2ª,
    # "Chile" (janela já fechada), depois do "Nora", "Tchau"
    instantes = iter([0.0, 1.0, 2.0, 3.0, 100.0, 101.0, 102.0])

    def whisper(caminho, cabecalhos, corpo):
        assert b'name="prompt"\r\n\r\nConversa com a assistente Nora.\r\n' in corpo
        return 200, "application/json", json.dumps({"text": next(transcricoes)}).encode()

    recomecos = []
    falado = []
    with (
        OllamaFalso(["Brasília."]) as ollama,
        ServicoFalso(whisper) as servidor_whisper,
        ServicoFalso(lambda c, cab, corpo: (200, "audio/wav", corpo)) as voz,
    ):
        local = (
            f'[ouvido]\nurl = "{servidor_whisper.url}"\n[voz]\nmotor = "piper"\n'
            f'[voz.piper]\nurl = "{voz.url}"\n'
        )
        config = carregar(criar_raiz(local=local), ambiente={"OLLAMA_HOST": ollama.host})
        saida = io.StringIO()
        falas_falsas = [b"\x00\x00" * 8000] * 6
        conversar_maos_livres(
            config,
            saida=saida,
            mostrar_ignoradas=True,
            gravar_falas=True,
            tocar=falado.append,
            fontes=(falas_falsas, lambda: recomecos.append(1)),
            relogio=lambda: next(instantes),
        )
    texto = saida.getvalue()
    assert "(ignorado: Música alta tocando)" in texto
    assert "Você: Nora, qual é a capital do Brasil?" in texto
    assert "Você: E da Argentina?" in texto
    assert "(ignorado: E do Chile?)" in texto
    assert "Nora: Oi, pode falar." in texto
    assert "Nora: Até mais!" in texto
    perguntas = [p["messages"][-1]["content"] for p in ollama.pedidos if p["messages"]]
    assert perguntas == ["qual é a capital do Brasil?", "E da Argentina?"]
    assert [json.loads(a)["text"] for a in falado] == [
        "Brasília.",
        "Brasília.",
        "Oi, pode falar.",
        "Até mais!",
    ]
    assert len(recomecos) == 4  # depois de cada resposta, a escuta recomeça do zero
    gravadas = sorted((config.pasta_dados / "falas").glob("*.wav"))
    assert len(gravadas) == 6
