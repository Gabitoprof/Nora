"""Servidor real da HUD + eventos dos 4 estados com medidas do Medidor real sobre PCM sintético."""

import json
import math
import sys
import threading
import time
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from nora import hud  # noqa: E402
from nora.hud_audio import contexto_fala  # noqa: E402

FALA = (
    "{alegre} Claro! Daqui a vinte e três dias será sábado, vinte e oito de novembro. "
    "Quer que eu anote isso na agenda?"
)

TAXA = 48000


def voz_sintetica(segundos, f0=180.0, silabas=4.5, ganho=0.25, pausas=()):
    n = int(TAXA * segundos)
    a = array("h")
    for i in range(n):
        t = i / TAXA
        env = max(0.0, math.sin(math.pi * silabas * t)) ** 0.6
        if any(p0 <= t < p1 for p0, p1 in pausas):
            env = 0.0
        f = f0 * (1 + 0.06 * math.sin(2 * math.pi * 1.3 * t))
        s = sum(math.sin(2 * math.pi * f * k * t) / k for k in (1, 2, 3, 4, 6))
        a.append(int(max(-1, min(1, ganho * env * s / 2)) * 32767))
    return a.tobytes()


ponte = hud.PonteHUD("Nora")
hud._ponte = ponte
srv = hud.ServidorHUD(ponte, 8799).iniciar()
print("URL", srv.url, flush=True)
ponte.estado.update(conectado=True)  # como anexar(conversa) faz
ponte.publicar("modelo_ativo", modelo="local (qwen3.5:9b)")
ponte.publicar("voz_ativa", motor="ElevenLabs")
ponte.publicar("ociosa")
parar_mic = threading.Event()


def microfone(ganho):
    pcm = voz_sintetica(6, f0=140, silabas=3.2, ganho=ganho)
    bloco = int(TAXA * 0.02) * 2
    pos = 0
    while not parar_mic.is_set():
        hud.amostrar_pcm(pcm[pos : pos + bloco], "microfone", TAXA, 1)
        pos = (pos + bloco) % (len(pcm) - bloco)
        time.sleep(0.02)


def falar(texto):
    pcm = voz_sintetica(9.0, f0=220, silabas=3.0, ganho=0.35, pausas=((3.0, 4.2),))
    with contexto_fala(texto):
        obs = hud.preparar_reproducao(pcm, TAXA, 1)
    hud.reproducao(True)
    quadros = len(pcm) // 2
    passo = int(TAXA * 0.02)
    pos = 0
    while pos < quadros:  # "callback" de saída: entrega 20 ms por vez, no ritmo real
        obs.entregar(pos, min(quadros, pos + passo), None)
        pos += passo
        time.sleep(0.02)
    hud.reproducao(False)


for linha in sys.stdin:
    cmd = linha.strip()
    if cmd == "ociosa":
        parar_mic.set()
        ponte.publicar("ociosa")
    elif cmd.startswith("ouvindo"):
        parar_mic.set()
        time.sleep(0.05)
        parar_mic.clear()
        ponte.publicar("ouvindo")
        threading.Thread(target=microfone, args=(float(cmd.split()[1]),), daemon=True).start()
    elif cmd == "pensando":
        parar_mic.set()
        ponte.publicar("pensando")
    elif cmd == "privacidade":
        ponte.privacidade(True)
    elif cmd == "falar":
        parar_mic.set()
        threading.Thread(
            target=falar,
            args=(FALA,),
            daemon=True,
        ).start()
    elif cmd == "estado":
        print(
            "ESTADO",
            json.dumps({k: ponte.estado[k] for k in ("estado", "nivel_audio", "emocao")}),
            flush=True,
        )
    print("OK", cmd, flush=True)
