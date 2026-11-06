# QA acústica da HUD (v0.4.0)

Evidências da HUD acústica, com o tipo de simulação de cada uma e o que ela **não** prova. Nenhuma delas substitui a homologação no Windows com microfone, voz e GPU AMD de verdade ([HOMOLOGACAO.md](../../HOMOLOGACAO.md)).

## Estados (`estados/`), 06/11/2026

Os quatro estados pedidos (repouso, escuta, processamento e fala), mais a fala baixa e uma pausa.

| Arquivo | Estado | Painel "Sinal de áudio" | Palavra |
|---|---|---|---|
| `estado-repouso.jpg` | Em repouso | Em silêncio | — |
| `estado-escuta-fala-baixa.jpg` | Ouvindo, fala baixa (RMS ~0,004) | 23% (antes da correção: "0%") | — |
| `estado-escuta.jpg` | Ouvindo, fala normal | 57% | — |
| `estado-processamento.jpg` | Pensando | Em silêncio (antes: o último nível da escuta) | — |
| `estado-fala.jpg` | Falando, emoção `alegre` | 71% | "Daqui" (tempo estimado no áudio) |
| `estado-fala-pausa.jpg` | Falando, 6,8 s | 61% | — |

Os valores medidos estão em `estados/resultado.json`, e o JavaScript não teve nenhum erro.

**Como foi feito.** `servidor_demo.py` sobe o servidor real da HUD (`nora.hud.ServidorHUD`) e alimenta o caminho real:
- **Microfone:** `amostrar_pcm` recebe blocos de 20 ms de um PCM sintético de 48 kHz parecido com voz, com fundamental de 140–220 Hz, harmônicos e envelope de sílabas. As medidas (RMS, pico, envelope, 6 bandas da FFT) vêm do `Medidor` de `acustica.py`, como na escuta real.
- **Voz:** `preparar_reproducao` com o PCM inteiro, `reproducao(True)` e um "callback" que entrega 20 ms por vez no ritmo do relógio. As palavras vêm do `temporizar` real, que distribui as palavras pelos trechos com som; a precisão é `estimada`.

`capturar.js` (Playwright, Chromium com WebGL por SwiftShader, 1600×900) abre o build real (`hud/dist`), manda cada estado e fotografa. Para repetir, rode `npm run build` em `hud/` e, nesta pasta, `node capturar.js`.

**O que isso não prova:**
- Não usa microfone, alto-falante ou ElevenLabs de verdade; o PCM é sintético.
- O WebGL é por software. O tempo e o FPS das fotos não valem para a GPU AMD: cada foto leva de 1 a 5 s nesse ambiente, por isso a foto da "pausa" saiu em 6,8 s, não dentro da pausa de 3,0–4,2 s.
- As palavras usam tempo estimado. Ainda não há alinhamento por caractere do ElevenLabs (`/with-timestamps`).

## Evidências anteriores (Codex, commit 73e62c8)

- `desktop-*.png` e `canvas-movimento-reduzido.png`: escuta com graves e com agudos, fala com PCM real gravado do callback, fala alegre, repouso e movimento reduzido.
- `amostras-callback-voz.json`: posições e tempos do callback de saída.
- `resultado-desempenho.json`: Canvas forçado, limite de 30/60 FPS e 8 FPS no modo jogo, página oculta sem desenho, movimento reduzido sem animação. Medido em software, não é benchmark de GPU.
- `falha-browser.json`: a rodada do QA do Codex que parou numa conferência de cor. Ela leu `#ecc67b` esperando o dourado `#F0C66A`, porque a cor ainda estava no meio da transição suave (~550 ms); a conferência era rígida demais, não é defeito da HUD. As conferências anteriores a ela (ponte Python → SSE → navegador, privacidade fechada por padrão, PCM sintético alterando as medidas) passaram. As cores agora são conferidas por teste automático (`tests/test_paleta.py` e `hud/tests/acustica.test.ts`).
