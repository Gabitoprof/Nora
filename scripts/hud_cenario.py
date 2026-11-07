"""Cenário de inspeção da HUD sem microfone nem voz: o servidor real da HUD e uma fala sintética
com palavras alinhadas, tocada em tempo real numa saída falsa (nada sai no alto-falante).

    python scripts/hud_cenario.py [porta]      (padrão 8799)

Abra o endereço mostrado no navegador e digite no terminal:
    falar    fala a frase de teste (palavras alinhadas, ~12 s)
    ouvindo  volta ao estado de escuta
    sair     encerra

Serve para conferir a HUD (marca, faixa da fala, onda) e tirar capturas. Não usa rede nem chaves.
"""

import math
import sys
import threading
import time
from array import array

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "src"))
from nora import audio, hud

TAXA = 22050
FRASE = "você poderia analisar os dados e me mostrar um resumo"
PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 8799


def fala_sintetica(palavras, ms_por_letra=230, pausa=250):
    amostras = array("h")
    tempos = []
    t = 0.0
    for palavra in palavras:
        dur = max(220, len(palavra) * ms_por_letra)
        n = int(dur / 1000 * TAXA)
        f0 = 170 + 25 * math.sin(t / 300)
        for i in range(n):
            x = i / TAXA
            env = math.sin(math.pi * i / n) ** 0.6 * (
                0.55 + 0.45 * math.sin(2 * math.pi * 5 * x) ** 2
            )
            v = sum(math.sin(2 * math.pi * f0 * k * x) / k for k in (1, 2, 3, 5))
            amostras.append(int(9000 * env * v / 2))
        tempos.append(
            {
                "texto": palavra,
                "inicio_ms": round(t, 3),
                "fim_ms": round(t + dur, 3),
                "destaque": False,
            }
        )
        t += dur
        amostras.extend([0] * int(pausa / 1000 * TAXA))
        t += pausa
    return amostras.tobytes(), tempos


class Saida:
    PortAudioError = RuntimeError

    class CallbackStop(Exception):
        pass

    def RawOutputStream(self, callback, finished_callback, channels, samplerate, **_):
        dono = self

        class Fluxo:
            def __enter__(s):
                def rodar():
                    inicio = time.perf_counter()
                    bloco = 512
                    n = 0
                    while True:
                        buf = bytearray(bloco * 2 * channels)
                        try:
                            callback(buf, bloco, None, None)
                        except dono.CallbackStop:
                            break
                        n += 1
                        espera = inicio + n * bloco / samplerate - time.perf_counter()
                        if espera > 0:
                            time.sleep(espera)
                    finished_callback()

                threading.Thread(target=rodar, daemon=True).start()
                return s

            def __exit__(s, *a):
                return False

        return Fluxo()


def ponte_estado():
    return hud._ponte.estado["estado"] if hud._ponte else None


_PRONTA = {}


def falar():
    if "fala" not in _PRONTA:
        _PRONTA["fala"] = fala_sintetica(FRASE.split())
    pcm, palavras = _PRONTA["fala"]
    t0 = time.perf_counter()
    som, por, fechar = audio.AudioEmPartes.de_fila(TAXA)
    som.definir_palavras(palavras)

    def alimentar():
        passo = TAXA * 2 // 5  # 200 ms por pedaço, como chega da rede
        for i in range(0, len(pcm), passo):
            por(pcm[i : i + passo])
            time.sleep(0.05)
        fechar()

    threading.Thread(target=alimentar, daemon=True).start()
    hud.emitir("emocao", nome="calma")
    audio._tocar_partes(Saida(), som, 0, None)
    print(f"fim fala {time.perf_counter() - t0:.1f}s", ponte_estado(), file=sys.stderr, flush=True)


if __name__ == "__main__":
    ponte = hud.PonteHUD("Nora")
    servidor = hud.ServidorHUD(ponte, PORTA).iniciar()
    hud._ponte = ponte
    with ponte._trava:
        ponte.estado.update(conectado=True, nome="Nora")
    ponte.publicar("modelo_ativo", modelo="qwen3.5:9b")
    ponte.publicar("voz_ativa", motor="elevenlabs")
    ponte.publicar("ociosa")
    ponte.privacidade(True)
    _PRONTA["fala"] = fala_sintetica(FRASE.split())
    print("PRONTO", servidor.url, flush=True)
    for linha in iter(sys.stdin.readline, ""):
        cmd = linha.strip()
        if cmd == "falar":
            threading.Thread(target=falar, daemon=True).start()
        elif cmd == "ouvindo":
            ponte.publicar("ouvindo")
        elif cmd == "sair":
            break
        print("ok", cmd, flush=True)
    servidor.parar()
