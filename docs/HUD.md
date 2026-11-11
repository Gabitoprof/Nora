# Nora HUD v0.4.0 — in development

The HUD represents the same Nora that talks in the terminal: no second microphone,
model, history or speech synthesizer. The Python core is the source of states and levels.
The browser only presents the data it receives and forwards supervised decisions.

## Official visual reference

The reference is the PNG provided by the owner in this task: black background, an organic
central crown of silver waves with an open center, fluid overlapping outlines, diagonal rivers
of particles, restrained spot lighting, calibration arcs and thin frames. The drawing is
procedural and animatable; it does not use a generic orb or another visual identity.

The PNG is available in the conversation, with no persisted local reference file in the checkout.
The visual comparison is qualitative; there is no claim of pixel-by-pixel equality. QA captures
use synthetic data only in the test harness, never as the application's real state.

The base is monochrome. Emotions gently change motion and accents: neutral silver
`#C9C9C9`, gold `#F0C66A`, pink `#E3A4BD`, turquoise `#66D4CB`, terracotta `#DF876A`, blue
`#80A8F6` and lavender `#AA9ACF`. Reduced motion, density and frame rate limit the cost.
Measuring with real Ollama/STT/TTS and AMD GPU belongs to the integrated acceptance.

## Prepare on Windows

Use the existing checkout; no worktree or second clone is needed. Requirements: Python
3.11–3.13, Node.js LTS 22.13+ or 24, as in `hud/package.json`, and the voice services already configured.
At the repository root, in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,voz,memoria]"
cd hud
npm ci
npm run lint
npm run typecheck
npm test
npm run build
cd ..
nora --verificar
```

The `nuvem` extra remains optional for ChatGPT/Claude, as do its credentials. Do not
put secrets in the front end, in Git or in the command. Installing Ollama, Whisper and TTS
is still described in [VOZ](VOZ.md), without reconfiguring the PC automatically.

## PowerShell does not run the cloud (Linux) script

`/workspace/Nora`, `.venv/bin/python`, `#!/usr/bin/env bash` and `set -euo pipefail`
belong to Codex's Linux environment. Do not copy the cloud `install_script` into
PowerShell. On Windows, use the real checkout path and `Scripts\python.exe`.

If `python3` points to Python 3.15, do not reuse that environment for voice.
List versions with `py -0p`; use Python 3.13 (or a supported 3.11/3.12) explicitly.
The example below is for the `B:\Nora` checkout, with a new environment outside it, keeping
any previous `.venv` and all data/settings:

```powershell
Set-Location 'B:\Nora' -ErrorAction Stop
py -0p
# Run the following lines when Python 3.13 is listed:
py -3.13 -m venv 'B:\Nora-venv313'
& 'B:\Nora-venv313\Scripts\python.exe' -m pip install -e ".[dev,voz,memoria]"
& 'B:\Nora-venv313\Scripts\python.exe' -m pip check
& 'B:\Nora-venv313\Scripts\python.exe' -m nora --verificar
```

There is no need to activate the environment or change the PowerShell execution policy. If 3.13
is not installed, install that version first, for example with
`winget install --exact --id Python.Python.3.13`, and confirm with `py -0p` in a new terminal.
Warnings from an old `.pth` pointing to `B:\ELLA\src` indicate an earlier editable install;
the separate environment does not inherit the global install's packages by default.

## Run

With the existing voice and model services available:

```powershell
nora ouvir --hud --hud-porta 8765
```

Open `http://127.0.0.1:8765` in the local browser and use full screen. The microphone is still
the one from `nora ouvir`; the HUD does not ask the browser for microphone permission. Spoken
model/voice/game mode commands are still interpreted and confirmed by the core.

To inspect only the visuals/server, without starting to listen:

```powershell
nora hud --porta 8765
```

That mode must stay identified as disconnected from the conversation, without making up an
active model, voice amplitude or transcription. To develop the front end:

```powershell
cd hud
npm run dev
```

Vite forwards `/api` to the local Python server on port 8765. For integrated use,
prefer the build served by Python itself, which keeps the interface and the API on the same origin.

## Contract and privacy

- Authoritative contract: `src/nora/hud_contrato.json`; the TypeScript front end consumes the same
  contract. Version, sequence and payload are validated; invalid messages do not command Nora.
  Envelope limited to 64 KiB UTF-8, text to 6000 characters, up to 8 SSE subscribers.
- SSE `GET /api/eventos`: events `{versao, sequencia, tipo, dados, instante}`. A connection/
  reconnection starts with an authoritative snapshot; it does not depend on replaying personal messages.
- `GET /api/estado`: snapshot of the current state. `nivel_audio` is a pipeline measurement, not
  a recording; it does not transmit WAV or PCM. With no data, the level is neutral.
- `GET /api/sessao`: local session token for change requests. It is not a provider
  credential; it does not go into the URL, persistent storage or logs.
- `POST /api/privacidade` with `{visivel: true|false}`: explicit opt-in for personal content.
  Hidden is the default; turning it off clears the displayed content. Do not store conversations in the browser.
- `GET /api/propostas` and `POST /api/decisao` with `{id, acao, confirmar:true}`: uses
  `Melhorias.decidir`, with confirmation in the interface and validation on the server. Approving creates
  a task; it does not modify code, publish or implement P3/P4.
- `GET /api/notas`: only notes actually used by the core, from an authorized folder.
  It does not scan the disk, open arbitrary paths or expose content without consent.
- `GET /api/relatorio`: report availability/metadata, without personal questions.
- Mutations require `X-Nora-Token`; Host/Origin and destination are local. No public CORS,
  no bind on `0.0.0.0`, no implicit remote access. Do not expose the port on the network.

The bridge is optional, with limited queues and sizes, level sampling and dropping for
slow clients. A client that disconnects must not interrupt the conversation. The snapshot
allows recovering the state after lost events. HUD failures must not stop the voice.

## Speech, emotion and content

States distinguish rest, listening, transcription, thinking, speaking, game and error. Speech
events must follow the start/end of playback, not only the synthesis. The acoustic data comes from
the same PCM captured/played by Nora. Emotions come from the tags already used by the voice engine.

Progressive text, notes and particle words require consent. The word effect can be
turned off. The sequence uses the playback clock and the sentence's intervals; state changes
do not advance words. Without timing alignment provided by the TTS, the intervals
are an **estimate grounded in the audio duration**, internally labeled
`estimada`; it is not phonetic sync. The front end does not reveal private thinking, personal
questions or keys.

## Quality and acceptance

```powershell
ruff format --check .
ruff check .
pytest
nora --verificar
cd hud
npm run lint
npm run typecheck
npm test
npm run build
```

CI includes the core on Windows/Ubuntu with Python 3.11/3.13 and the front end on Windows/Ubuntu
with Node 22. Locally, 295 Python tests passed (1 skipped for lack of a real Kokoro),
15 TypeScript tests, Ruff, lint, typecheck and build. The results of this delivery are recorded in the [cumulative checklist](HOMOLOGACAO.md).
Do not call v0.4.0 released or accepted just because CI passed.

Pending on the real computer: prolonged silence and typing while listening, alerts and
reports with self-improvement on, game mode transitions without reactivating Ollama, real voice
output and fallback, latency, fullscreen/ultrawide, CPU/GPU usage with the models loaded.
The version stays in development, with no automatic merge, tags or release.

## Entry executable blocked by Windows

If the install finishes and `pip check` says `No broken requirements found`, but
App Control blocks `nora.exe`, that does not indicate a dependency failure.
The official entry point `python -m nora` uses the same `nora.cli.main` as the installed launcher.
The application's diagnostics are still `--verificar`. Do not disable security
policies; if the policy also prevents running through Python, ask whoever manages the
computer's policy to review and allow the application.

## The HUD returns `Origem local obrigatória` when opened from a link

The browser's initial opening sends `Sec-Fetch-Site: cross-site` or `same-site` when it
comes from a link on another page. An earlier version of the bridge also rejected that legitimate
navigation, although the build was correct. The fix authorizes only `GET /` and
`GET /index.html` with `navigate` mode and `document` destination, keeping Host/Origin validated.
APIs, external data requests, iframes and mutations remain protected; do not remove
the origin or token checks to open the interface.

Stop the old server with Ctrl+C, update the `feat/v0.4.0-hud` branch, reinstall the
lockfile with `npm.cmd ci`, build and restart Python. The old process keeps the previous
rules in memory until it is restarted. A build shown as completed in the terminal is already
evidence of an approved build; the HTTP origin error is recorded separately.

The audit alerts of the development tools were also fixed through explicit,
tested updates. There is no need to run `npm audit fix --force`.
The local install-scripts warning only needs review if an install or build
fails; the screenshot provided confirms a completed build, with no need to allow extra
scripts to fix the HTTP 403.


## Acoustic and emotional resume — 06/11/2026

The central crown keeps the reference's open center and organic outlines. RMS,
peaks, envelope, the spectral distribution in six bands, centroid and flux derived from the
PCM drive the dynamics; the geometry is still an artistic interpretation, not an
oscilloscope. Listening and playback use distinct behaviors. The bottom band is
complementary and reacts only to Nora's voice. At rest the discreet breathing remains.

The analysis reuses the single audio pipeline. The browser receives only measurements and
timing metadata, never raw audio, credentials or a new capture. Limited queues,
dropping late data and a limited update rate protect the voice
pipeline; disconnecting the HUD must not interrupt it. Reduced motion, hidden page, game
mode and the Canvas quality remain available.

**HUD failures do not stop speech, but they do not disappear:** in the acoustic path (the output callback, the playback observer, the analyzer, the events), each failure is counted by place and type (`nora.falhas_hud`). The first of each type becomes a log line (`nora.hud`); the following ones are only counted. The error message and the audio are never logged.

The "Sinal de áudio" side panel shows the same signal that moves the central wave (the measurement of the source in use: microphone while listening, voice while speaking), on a decibel scale (−60 dBFS = 0%, 0 dBFS = 100%). With a signal, it never shows "0%"; while thinking or at rest, it shows "Em silêncio".

The palette lives in a single file, `src/nora/paleta.json` (inside the Python package, so it ships with the install), read by the HUD (`state.ts`) and by Python (`nora.paleta.cor("curiosa")`), so the Second Brain uses the same colors without copying them. The palette follows the approved table:

| Group | Color | Names that fall into it |
|---|---|---|
| Neutral | silver `#C9C9C9` | neutra, neutro (and any unknown name) |
| Joy and enthusiasm | gold `#F0C66A` | alegre, empolgada, risada, alegria, entusiasmo |
| Tenderness | soft pink `#E3A4BD` | carinhosa, carinho, acolhimento |
| Calm | turquoise `#66D4CB` | calma, serenidade, sussurro, suspiro |
| Seriousness | blue `#80A8F6` | séria, seriedade, confiante, confiança, preocupada, preocupação |
| Sadness | lavender `#AA9ACF` | triste, tristeza |
| Curiosity | terracotta `#DF876A` | curiosa, curiosidade |

Choices: **serenidade** (serenity) is calm. **Sussurro** (whisper) and **suspiro** (sigh) are ways of speaking, not emotions, and the HUD does not receive the sentence's underlying emotion; so they stay in calm, which fits a low voice, instead of sadness. **Preocupação** (worry) is a serious tone, so it goes to seriousness, not curiosity. The emotion names are the existing core's; there is no other classifier. The reference's yellow, purple and pink markings are not part of the interface.

The current evidence, its kinds of simulation and its limitations are in
[acoustic QA](evidencias/hud-acustica/README.md). The historical results above remain
restricted to the commits indicated. The cumulative checklist keeps the installation,
`pip check`, diagnostics and the Windows opening/connection reported by the owner.
That evidence does not accept the new acoustic reactivity, the physical voice or the
AMD GPU consumption; those scenarios remain in the integrated acceptance.
