# HUD acoustic QA (v0.4.0)

Evidence for the acoustic HUD, with the kind of simulation behind each one and what it does **not** prove. None of it replaces acceptance on Windows with a real microphone, voice and AMD GPU ([HOMOLOGACAO.md](../../HOMOLOGACAO.md)).

## States (`estados/`), 06/11/2026

The four requested states (rest, listening, processing and speaking), plus quiet speech and a pause.

| File | State | "Sinal de áudio" panel | Word |
|---|---|---|---|
| `estado-repouso.jpg` | At rest | Em silêncio (silent) | — |
| `estado-escuta-fala-baixa.jpg` | Listening, quiet speech (RMS ~0.004) | 23% (before the fix: "0%") | — |
| `estado-escuta.jpg` | Listening, normal speech | 57% | — |
| `estado-processamento.jpg` | Thinking | Em silêncio (before: the last listening level) | — |
| `estado-fala.jpg` | Speaking, emotion `alegre` | 71% | "Daqui" (time estimated from the audio) |
| `estado-fala-pausa.jpg` | Speaking, 6.8 s | 61% | — |

The measured values are in `estados/resultado.json`, and the JavaScript had no errors.

**How it was done.** `servidor_demo.py` starts the real HUD server (`nora.hud.ServidorHUD`) and feeds the real path:
- **Microphone:** `amostrar_pcm` receives 20 ms blocks of a synthetic voice-like 48 kHz PCM, with a 140–220 Hz fundamental, harmonics and a syllable envelope. The measurements (RMS, peak, envelope, 6 FFT bands) come from the `Medidor` in `acustica.py`, as in real listening.
- **Voice:** `preparar_reproducao` with the whole PCM, `reproducao(True)` and a "callback" that delivers 20 ms at a time at the clock's pace. The words come from the real `temporizar`, which spreads the words across the voiced stretches; the precision is `estimada`.

`capturar.js` (Playwright, Chromium with WebGL via SwiftShader, 1600×900) opens the real build (`hud/dist`), sends each state and takes a picture. To repeat it, run `npm run build` in `hud/` and, in this folder, `node capturar.js`.

**What this does not prove:**
- It does not use a real microphone, speaker or ElevenLabs; the PCM is synthetic.
- WebGL is software-rendered. The timing and FPS of the pictures do not apply to the AMD GPU: each picture takes 1 to 5 s in that environment, which is why the "pause" picture came out at 6.8 s, not inside the 3.0–4.2 s pause.
- The words use estimated timing. There is no per-character ElevenLabs alignment yet (`/with-timestamps`).

## Earlier evidence (Codex, commit 73e62c8)

- `desktop-*.png` and `canvas-movimento-reduzido.png`: listening with lows and with highs, speaking with real PCM recorded from the callback, happy speech, rest and reduced motion.
- `amostras-callback-voz.json`: positions and times of the output callback.
- `resultado-desempenho.json`: forced Canvas, 30/60 FPS limit and 8 FPS in game mode, hidden page without drawing, reduced motion without animation. Measured in software, not a GPU benchmark.
- `falha-browser.json`: the Codex QA round that stopped at a color check. It read `#ecc67b` expecting the gold `#F0C66A`, because the color was still in the middle of the smooth transition (~550 ms); the check was too strict, not a HUD defect. The checks before it (Python bridge → SSE → browser, privacy closed by default, synthetic PCM changing the measurements) passed. Colors are now checked by automated tests (`tests/test_paleta.py` and `hud/tests/acustica.test.ts`).
