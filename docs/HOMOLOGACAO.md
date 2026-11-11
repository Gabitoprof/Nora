# Nora cumulative acceptance testing

## Development and acceptance strategy

The final acceptance will be integrated, at the end of the planned implementation, on Windows
with an AMD GPU, covering all modules together. During development:

- Write and run unit, integration and regression tests suited to each change.
  Keep the tests of existing features; do not disable tests to pass CI.
- Require green CI on Windows and Linux on the evaluated commit before considering a PR ready.
  The current matrix uses Ubuntu and Windows with Python 3.11 and 3.13.
- Do one-off manual tests only when essential for hardware or external integration.
  Record the others in the final acceptance, without interrupting development.
- Update this per-module checklist with evidence, commit/environment, automated results,
  approved, failed and pending manual tests. Also record skipped or not-run tests.
- Green CI proves the checks that ran; a feature is only considered accepted
  after the applicable functional criteria and the final integrated acceptance.
- Keep manual approvals already recorded. Repeat only when a change directly affects
  the validated component, recording the change and the reason for repeating.
- Merging into `main` and publishing releases require the owner's explicit approval.
  The restrictions on not merging, creating tags or publishing automatically remain.

## Reference automated evidence

- Commit `77905e6`: [CI approved in the four environments](https://github.com/Gabitoprof/Nora/actions/runs/41758193076).
- Linux/Python 3.12.14 on the code of `71cf727` (followed by documentation in `77905e6`):
  `ruff format --check .` and `ruff check .` approved; `pytest`: **266 passed, 1 skipped**
  (real Kokoro, no model). `nora --verificar`: exit code 0, with real services absent.
- These results belong to the commits indicated, not an automatic approval of future commits.
- Detailed cases AJ-01–AJ-03 and A1–A6: [fix checklist](CHECKLIST_HOMOLOGACAO_AJ01_AJ03.md).

## Per-module checklist

The manual evidence reported by the owner is kept below. "No record" only means there is no
evidence for that module, without invalidating earlier tests.
The automated column refers to the reference suite above, not to real models or devices.

| Module | Automated result / coverage | Approved manual test recorded | Pending for integrated acceptance |
|---|---|---|---|
| Configuration and CLI | Suite approved: configuration, `.env.example`, commands and diagnostics | No record | Check diagnostics with the real services/configuration, without exposing secrets |
| Conversation and routing | Suite approved: streaming, fallbacks, errors and continuity | No record | Conversation with Ollama and external providers configured |
| Memory and pending items | Suite approved: facts, curation, agenda, forget/delete, Ctrl+C and resume | No record | Persistence across sessions, real interruption and search with bge-m3 |
| Obsidian notes | Suite approved: index and query | No record | Index and query a representative test folder on Windows |
| Input, activation and STT | Suite approved: VAD, activation, keyboard and conversation loops | No record | Microphone/whisper.cpp, long silence, keyboard during an alert, Ctrl+C, accents and consecutive inputs |
| Voice and TTS | Suite approved with simulations and audio files; real Kokoro skipped | No record | Kokoro/Piper/ElevenLabs available, pronunciation, emotions, voice switch, fallback and playback |
| Game mode and GPU | Suite approved: exit confirmation, no local fallback and resume offer | No record | VRAM release on the AMD GPU, cloud failure without reactivating Ollama and resume after confirmation |
| Supervised self-improvement | Suite approved: metrics, proposals, decisions, privacy and task generation | No record | Integrated daily cycle and decisions without automatic code change |
| Reports and notifications | Suite approved: AJ-01–AJ-03, LF/CRLF, manual recovery, reading and waiting | No record | Scheduled time with Nora idle/busy/in game, restart, opening the Markdown and real toast/click |

P3 and P4 remain out of scope. The v0.4.0 HUD was later authorized by the owner, following the
technical plan and the official PNG; it does not extend the scope to MCP, routines or distributed operation.

## Cumulative record of manual tests

When receiving or running a manual test, add a row without deleting the history.
Test data must be synthetic; do not keep personal questions, audio, keys or tokens.

| Module/case | Commit or version tested | Environment and relevant configuration | Result and evidence | Change that requires repeating |
|---|---|---|---|---|
| Installation and dependencies | HUD before the acoustic resume of 06/11/2026 | Windows, Python 3.13 | Editable install completed and `pip check` approved, per the owner's screenshots | Repeat only if dependencies/environment change |
| Official entry point and diagnostics | HUD before the acoustic resume of 06/11/2026 | Windows, `python -m nora --verificar` | Module ran; diagnostics showed Ollama and memory available, STT unavailable. Not a full approval of the diagnostics | Retest STT when its service is available |
| Opening and connecting the HUD | HUD before the acoustic resume of 06/11/2026 | Windows, browser connected to the core | A later screenshot from the owner confirms the interface open and the core connected | Acoustic changes need their own validation, without repeating the approved installation |

## Final integrated acceptance — Windows/AMD

- [ ] Define the candidate commit and confirm that commit's Windows/Linux CI.
- [ ] Gather earlier manual approvals and identify the directly affected components.
- [ ] Run the pending scenarios per module with all services integrated.
- [ ] Validate conversation, memory, voice, interruptions, game mode, reports and supervised decisions
  in the same flow; check restart and recovery after failures.
- [ ] Record real results, limitations and failures found; fix and retest the affected ones.
- [ ] Get the owner's acceptance for merging into `main` and a separate authorization to publish.

## v0.4.0 — preparing acceptance on Windows (branch `integracao/v0.4.0`)

Review fixes applied and covered by automated tests (Windows and Linux CI):
- **Palette inside the package** (`src/nora/paleta.json`): the HUD and the Second Brain read the same file; a test forbids a copy.
- **Clean install:** `scripts/testar_instalacao_limpa.py` builds the wheel, installs it in a venv outside the checkout and checks the palette, the Second Brain and the package files (`instalacao` job in CI, Linux only).
- **Single version:** `0.4.0.dev0` in Python and `0.4.0-dev.0` in the HUD, with a divergence test. `nora --verificar` (first line) and the HUD (settings) show version and commit.
- **Voice switch:** the confirmation carries its text to the HUD (regression test).
- **HUD failures:** counted and logged once per type, without text or audio; speech goes on.
- **Revised palette:** serenity, whisper and sigh in calm; worry in seriousness.

**Installed, outside the repository:** the default config comes inside the package (`src/nora/nora.toml`), and the personal config, `.env`, memory and models live in `%APPDATA%\Nora`, created on first run. The clean install test runs `nora --verificar` that way. The HUD build goes inside the `.exe`; in a wheel install the HUD still needs `NORA_HUD_DIST`.

**Particle words.** With ElevenLabs v4 (default), each word's timing comes from ElevenLabs itself (`precisao "alinhada"`). On the other voices, and if the alignment does not come, it is estimated from the audio being played, and the HUD shows "tempo estimado no áudio" (time estimated from the audio). Step 7 of the walkthrough checks v4 on your account.

**ElevenLabs v4: approved on the real PC.** The automated tests use a fake WebSocket server (streaming over one connection, alignment, `keep_alive`, barge-in, flash fallback, turn without audio, diagnostics). On Windows, on 06/11/2026, `eleven_v4_turbo` spoke through real-time dialogue: first audio in 985 ms, playing in 1555 ms, 0 ms of silence between chunks, aligned words. Gabriel's decision: use only v4, without comparing with other models.

### 1. Automated (without you): `scripts/homologacao_windows.ps1`

In the repository folder, with the `.venv` activated:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\homologacao_windows.ps1
```

It runs and writes to `data\homologacao\AAAA-MM-DD_HHMM.txt`:
- version, commit, GPU and driver;
- `pytest`, `ruff` and the clean install;
- the HUD's `npm ci`, `npm test` and `npm run build`;
- `nora --verificar`;
- 30 s of measurement with the local model loaded and the HUD open in the browser: 3D GPU usage, VRAM, total CPU, browser CPU and Python CPU (average, minimum and maximum).

It takes about 5 minutes. At the end it says "Todas as etapas passaram" (all steps passed) or lists the ones that failed. It has not run on a real Windows yet (only on PowerShell 7 for Linux): if a step errors, send the file anyway.

### Already run in the cloud, without Gabriel's PC (06/11/2026, commit `cf519fc`)

The Windows PC was not available. In the cloud (Linux x86_64, 4 cores, no GPU):

| Check | Result |
|---|---|
| `pytest` | 457 passed, 2 skipped |
| `ruff format --check` and `ruff check` | no errors |
| HUD: `npm ci`, `lint`, `typecheck`, `npm test`, `build` | ok; 36 tests |
| Clean install (wheel outside the checkout) | ok, `nora 0.4.0.dev0` |
| `nora --verificar` | first line: `Versão: 0.4.0.dev0 (commit cf519fc)` |
| CI #170 (Windows and Linux, 7 jobs) | all green |
| HUD (settings) | `Nora 0.4.0-dev.0 · commit cf519fc`, same as Python |

Performance with the HUD open (real `nora hud` + real build, headless Chromium, 1600×900, 30 s per measurement; script and numbers in [`evidencias/hud-acustica/desempenho-nuvem/`](evidencias/hud-acustica/desempenho-nuvem/)):

| Quality | Limit | FPS drawn | Browser CPU | Nora CPU |
|---|---|---|---|---|
| Detailed (WebGL) | 30 | 16.8 | 84% of the machine | 0% |
| Detailed (WebGL) | 60 | 16.7 | 85% of the machine | 0% |
| Economy (WebGL) | 30 | 23.2 | 82% of the machine | 0% |

**How to read it:** without a GPU, WebGL is computed on the CPU (SwiftShader), so FPS is CPU-bound (~17 instead of 30) and the browser takes almost the whole machine. That is the worst case, not a measurement of the RX 9060 XT. What counts as a result:
- Nora (Python) spends no CPU with the HUD open: drawing is all in the browser, another process;
- the Economy quality yields ~40% more frames on the same hardware;
- no page errors.

**Windows script checked on PowerShell 7.4 for Linux:** the syntax is ok, and the version without measurement (`-SemDesempenho`) ran end to end, with the 7 steps ok, the version and commit line and the file in UTF-8. A failing step shows as `FALHOU` (failed) and in the final summary; this was tested with a fake `ruff`. PSScriptAnalyzer is not available here (the PowerShell Gallery is blocked), so compatibility with Windows PowerShell 5.1 was reviewed by hand.

**Still pending on Gabriel's PC:** run the script on a real Windows, including the GPU counters (they only exist on Windows); real FPS, GPU and VRAM; and the whole walkthrough below, which needs a microphone, a speaker and ElevenLabs.

### 2. Walkthrough with you (~15 min)

Before: `git pull`, `.venv\Scripts\activate`, Ollama open, ElevenLabs as the main voice, Second Brain on (`[segundo_cerebro] ativo = true`) and the HUD visible (`nora ouvir --hud`, open the address that shows up).

| # | Do | Observe | Result |
|---|---|---|---|
| 0 | Note the first line of `nora --verificar` and the version in the HUD settings | Same version and same commit in both | |
| 1 | Say "Nora, que dia vai ser daqui a 23 dias?" | Answers the right date; the wave reacts to your voice (silver, "Ouvindo"), changes on "Pensando" and speaks with another shape | |
| 2 | Speak quietly and then normally | The "Sinal de áudio" panel follows, without staying at 0% while the wave moves | |
| 3 | Ask for something long ("me conta uma história curta") | Audio starts fast (streaming); the particle words follow the speech and stop at pauses, without running ahead | |
| 4 | Speak over Nora in the middle of the answer | She stops (barge-in) or, if there is no barge-in in your mode yet, note what happens | |
| 5 | "Troque para a voz do Piper" and then "volta pro ElevenLabs" | The confirmation shows in the HUD (text and words) and the voice switches | |
| 6 | "Modo jogo" → "sim, sair do modo jogo" | The HUD shows game mode; `ollama ps` with no model loaded during the game | |
| 7 | ElevenLabs v4: `nora --verificar` and one answer with `nora falar --medir` | "Modelo efetivo eleven_v4_turbo (diálogo...)", "Continuidade ElevenLabs ativa" and the `[voz: ...]` line without `[voz reserva]` | ✅ 06/11: 985 ms to the first audio, 1555 ms playing, 0 ms of silence, aligned words |
| 8 | Say a new fact ("eu estudo com a Ana às quartas") and then "mostre seu segundo cérebro" | The note appears in the vault within ~1 min, without a pause in speech; the map opens | |
| 9 | Throughout, with the HUD open | Any stutter, echo or pause in speech? FPS (Edge/Chrome: F12 → Ctrl+Shift+P → "Show frame rate") | |

Send the step 1 file and the Result column (a photo is fine). Problems become fixes with tests before approval.

## HUD v0.4.0 — current run

Branch `feat/v0.4.0-hud`, base `Pull_code` at commit `70d39b7`.
The PNG provided in the conversation is the official reference; qualitative visual comparison by
design and QA agents. No pixel-by-pixel difference measurement because the PNG file is not
available locally. A test mock does not represent the real runtime state.

| HUD module | Automated in this delivery | Approved manual test recorded | Pending Windows/AMD |
|---|---|---|---|
| Python/TypeScript contract | Shared JSON, version/order/Unicode validation; Python and TypeScript tests approved | No record | Does not require manual repetition by itself |
| Local SSE bridge, reconnection and limits | Real HTTP/SSE and reconnection approved; queues/slow client and limits tested | No record | Reconnection with real services in use |
| Host/Origin/token and privacy | 14 HTTP QA checks approved, plus persisted tests; opt-in/out end to end approved | No record | Check a shared screen and opt-in |
| WebGL and Canvas waves/particles | Desktop/ultrawide/mobile captures reviewed; automatic fallback without WebGL approved | No record | Look on the target monitor, performance with LLM/STT/TTS |
| States, voice and amplitude of the single pipeline | Playback RMS/callback, CLI and regressions approved with simulated devices | No record | Real microphone/speaker and fallback, without a second device |
| Text and estimated words | Consent, HTML escaping, end of speech and visual estimate checked in the browser | No record | Legibility and comfort; do not claim phonetic sync |
| Proposals and supervised decisions | Real Melhorias domain: cancel does not decide, confirm decides without changing code | No record | Integrated cycle with self-improvement on and the daily report |
| Used and authorized notes | Folder/consent filtering tested; the panel uses only the answer's notes | No record | Real folder explicitly configured, without unwanted exposure |
| Responsiveness, accessibility and reduced motion | Four viewports without overflow, 12px mobile fields, zero pageerrors; reduced motion and hidden page without drawing | No record | Ultrawide full screen and accessibility preferences on Windows |

Do not release v0.4.0 before the final integrated acceptance. Do not repeat earlier manual
approvals without direct impact. Opening/connecting on Windows was reported by the owner;
voice, devices and GPU have not been accepted yet.

### HUD QA evidence

- Headless Chromium browser, through Playwright, with synthetic test data; real Python server
  and real improvements domain in the end-to-end test. No real hardware or AI services.
- 13 end-to-end checks approved: SSE, state/emotion/level, escaped XSS, consent,
  estimated words, clearing on hide/end of speech, confirmation/cancellation, restart and
  reconnection with a reset sequence, no persistence in the browser or fake connected core.
- Desktop 1672×941, ultrawide 2560×1080, mobile 390×844 and reduced motion: no horizontal
  overflow, no page errors, localStorage/sessionStorage empty.
- Canvas fallback forced without WebGL: 33 draws in 1500ms (~22 FPS observed, limit 30)
  in this concurrent headless environment. Game mode: 11/1500ms (~7.3 FPS, limit 8).
  Hidden page: 0 draws/500ms; reduced motion: 0/1500ms. Do not extrapolate to the AMD GPU.
- Capture files and harness from that session in `/workspace/scratch/qa-hud/` (outside Git).
  The comparison with the PNG was qualitative, by the design/QA agents and the main review.
- Fixes during QA: a disconnected snapshot does not pretend the core is active; the privacy toggle
  uses the authoritative response without reverting a newer SSE, with two persisted regressions; mobile
  legibility; filament width/asymmetry; local development proxy; Unicode and MIME limits.
- Wheel packaging checked: `nora/hud.py` and `nora/hud_contrato.json` present.
- The new branch's CI must be confirmed on the pushed commit before declaring the PR ready.
  The old approval of `77905e6` does not validate the HUD implementation.

### Local automated result of the HUD implementation

- Python 3.12.14/Linux: **295 passed and 1 skipped** (`pytest -ra`), including 29 new tests
  for the bridge, HTTP/SSE, domain, audio, CLI, Unicode and MIME. The skipped one is still
  real Kokoro without a model; not an approval of physical TTS.
- `ruff format --check .` and `ruff check .`: approved. `nora --verificar`: exit code 0,
  with Ollama, Whisper and Kokoro unavailable; optional credentials not configured.
- Frontend: `npm ci`, lint, typecheck, **15 Vitest tests** and build approved.
  Includes the shared contract, out-of-order events, Unicode, reconnection/token and two
  race conditions between HTTP consent and newer SSE events.
- Drawing uses Three.js/WebGL, with automatic Canvas if WebGL does not exist or loses its context.
  QA captures check responsiveness and identity; the final aesthetic approval belongs
  to the owner, and integrated GPU/latency measurement remains pending.

### CI and final review of the delivery

- Implementation commit `a81065f`: six jobs approved in
  [run 41911978525](https://github.com/Gabitoprof/Nora/actions/runs/41911978525):
  Windows/Ubuntu core with Python 3.11/3.13 and Windows/Ubuntu frontend with Node 22.
- Final QA re-approved 13 end-to-end checks, the deterministic HTTP/SSE race and
  5 checks of authorized notes/latency. No page errors or personal storage.
- Last visual adjustment: mobile panel enlarged so "Conteúdo protegido" is not cut after
  adding the latency line; geometry check in the browser and capture updated.
- Vite proxy: configuration implemented; specific final smoke test not confirmed in this round.
  The main path accepted automatically uses the build served by Python on the same origin.
- PR creation still blocked externally: the GraphQL API returned `Forbidden`.
  [Form with the branches filled in](https://github.com/Gabitoprof/Nora/compare/Pull_code...feat/v0.4.0-hud?expand=1).
- This does not approve merge, tag, release or physical Windows/AMD acceptance.

### Manual evidence reported by the owner — Windows installation

- The owner's screenshots confirm creating the Python 3.13 environment and the editable
  install of the `dev,voz,memoria` extras completed successfully.
- `pip check`: **approved**, with `No broken requirements found`. Do not ask to repeat
  this check without a direct change in the environment/dependencies.
- `nora.exe --verificar`: **blocked by Windows App Control**;
  do not classify it as a Nora error nor as an approved functional diagnosis.
- Pointed to the official entry point `python -m nora --verificar`, without changing policies;
  result reported later: module ran, Ollama and memory available, STT
  unavailable. This does not accept the missing services or voice playback. The Linux
  run with exit code 0 remains separate evidence.
- An approved installation does not accept microphone, STT/TTS, GPU or full integration.

### Fix for opening from a link and HUD tooling

- Owner's evidence: `npm ci` and the HUD build completed on Windows; do not repeat the
  build investigation as if it had failed. The server started, but the browser
  got HTTP 403 `Origem local obrigatória`; opening the interface **failed in that version**.
- Reproduced before the fix: four Chromium clicks on pages of another origin
  to `/` and `/index.html` returned 403 with `Sec-Fetch-Site` cross-site/same-site,
  `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Dest: document` and no Origin.
- Only the initial public document was fixed. Four browser cases passed
  after the change, including assets/SSE/consent on the same origin and zero pageerrors.
  The state/token API, external POST, iframe and a direct link to the API remain 403.
- New HTTP regressions: 12 cases; HUD suite: **41 passed**. Full Linux/Python
  3.12 suite: **307 passed and 1 skipped** (real Kokoro). Ruff format/check approved and
  `python -m nora --verificar` ran with exit code 0, without physical services on this machine.
- QA repeated the 13 end-to-end checks and the HTTP/SSE privacy race:
  approved. Does not replace physical Windows/AMD integration.
- The initial npm audit confirmed the owner's 10 alerts (8 moderate, 2 critical).
  Vitest/ESLint updated explicitly; transitive minimatch pinned in the vulnerable
  range with tests of the consumed APIs. No `audit fix --force` or disabled tests.
- Tooling requirement updated to Node LTS 22.13+ or 24 (see the exact engines in
  package.json). Keep the Windows/Ubuntu CI matrix and confirm the pushed commit.
- Browser evidence from that session: `/workspace/scratch/qa-hud/navigation-before-results.json`,
  `navigation-fixed-results.json`, `external-link-fixed.png` and `FINAL_QA.md`.
- Manual retest needed only for the fixed opening in the owner's browser;
  earlier approvals of installation/pip check remain recorded, without repeating unaffected
  modules. Voice/GPU and the final integrated acceptance remain pending.

- Tooling after the update: `npm ci`, lint, typecheck, **19 Vitest tests** and build
  approved with both Node 24.22.1 and Node 22.23.4. Four new cases check
  the minimatch APIs consumed by ESLint/parser, including dotfiles, extensions and negation.
- Full npm audit: **0 vulnerabilities**; production-only audit: **0**.
  The earlier install warnings were not used to explain the HTTP 403: the two
  causes were investigated and fixed separately. No Windows policy was changed.

## "Imagem para as falas" roadmap: phases 0 and 1 (validate and fix)

Branch `integracao/v0.4.0`. Each item has its own commit; what depends on Gabriel's PC is marked.

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | v4 alignment offsets | Fixed and tested with a fake server (several chunks, known offsets) | `tests/test_voz_v4.py` (reference per turn, chunks, lead-in silence) |
| 2 | Fallback mid-reply | Implemented: before audio / after (continues from the boundary) / no boundary (stops and allows repeating) / no alignment (keeps playing) | `tests/test_voz_v4.py` (server dropping mid-reply, cancel and resume without repeated words) |
| 3 | Diagnostics (`--verificar`, `--medir`, log) | Effective model, continuity, reason for each fallback, generations per reply, timings (request, first PCM, playback, silence between chunks) on both paths | `tests/test_voz_v4.py` (diagnostics with mid-reply fallback, HTTP, old file; no text or key) |
| 4 | Holding through pauses | Word until the next one starts, ceiling `TETO_PAUSA_MS` = 1.5 s; disappears immediately on `reproducao_encerrada`, cancellation and Private | `hud/tests/text-particles.test.ts` |
| 5 | Speech clock | Measured and tuned: 450/400 ms and backward steps < 60 ms ignored (table below) | `hud/tests/relogio-medicao.test.ts` |
| 6 | State tests (`reproducao_encerrada`) | Order, duplicates, reconnection, privacy and a late message after Private | `hud/tests/state.test.ts` |
| 7 | Privacy in the backend | Words only published with the screen authorized; revoking invalidates the current speech (epoch) and empties the queues; Private does not even store the words. Reads without a session secret: proposal below | `tests/test_hud.py`, `tests/test_hud_acustica.py` |
| 8 | Visual QA | Long words and accents legible at 1920×1080 (1060 px band) and 1366×768 (902 px); legible in ~116 ms | `docs/evidencias/palavras-1920x1080.jpg`, `palavras-1366x768.jpg`; `hud/tests/text-particles.test.ts` |
| 9 | Measurement on the PC (prepared) | Telemetry in the HUD + `homologacao_windows.ps1` (baseline × HUD, soak) | **Pending: Gabriel runs it** |
| 10 | Speech script and video | 30 cases (short, long, pauses, interruption, privacy, failures) + 60 FPS recording | **Pending: Gabriel runs it** |

ElevenLabs' official documentation is unreachable from the cloud (domain blocked). The official SDK
(`elevenlabs` 2.77.0) documents, for the TTS WebSocket, times **relative to the returned chunk**; the
dialogue type does not describe it. The code accepts both references and pins the chosen one per turn.
**Pending on the PC:** confirm with the real v4 (the `[voz: ...]` line and the HUD show the words at
the right time in long, multi-chunk answers).

### Item 5: measuring the speech clock

Deterministic simulation (`hud/tests/relogio-medicao.test.ts`): 60 s of speech, 260 ms words
every 300 ms, backend samples every 50 ms, network delay of 5 to 45 ms, stalls (no
sample) of 150 to 450 ms in 0%, 1% or 3% of the samples, drawing at 60 FPS.

| Max age / extrapolation | Stalls | Sound→word delay p50 / p95 / worst | Words lost | Backward steps |
|---|---|---|---|---|
| 300 / 250 (before) | 3% | 33 / 50 / 217 ms | 1 | ~140 (before the tolerance) |
| **450 / 400 (now)** | 3% | 33 / 50 / 100 ms | 0 | 0 |
| 600 / 500 | 3% | 33 / 50 / 83 ms | 0 | 0 |

Choice: 450/400. Extrapolating more (600/500) gains little and shows words early when the network
really lags (the backend does not publish samples while audio is missing). The measured delay does
not include the real latency of the Windows audio output: **pending on the PC** (walkthrough below).

### Item 7: does the HUD bridge require a session secret?

**Finding:** only to **change** things (privacy, decisions): the `X-Nora-Token` header. **Reading**
(`/api/eventos`, `/api/estado`, `/api/notas`, `/api/propostas`) is protected by other barriers:
`Host` must be `127.0.0.1:port` (blocks DNS rebinding), an `Origin` from another site is refused and
`Sec-Fetch-Site` cross-site/same-site is refused. Against **web pages** this is enough (the browser
always reports the origin; tested). The weak point is another **local program** (not a browser) on
the same computer: it can read the events and even get the token from `/api/sessao`.

**Proposal (not applied: it changes how the HUD is opened):**

1. Nora generates the token and opens the HUD with it in the address **fragment**
   (`http://127.0.0.1:8765/#sessao=TOKEN`): the fragment does not go to the server or to logs.
2. The page keeps the token in `sessionStorage` and sends it on every read (`X-Nora-Token`; for
   events, in a first request that swaps the token for a single-use ticket, because
   `EventSource` does not send headers).
3. `/api/sessao` goes away. Opening `http://127.0.0.1:8765/` without the token shows only a page
   asking to open it through Nora (the Start menu shortcut or the link `nora ouvir --hud` prints).

Cost: old bookmarks to the HUD stop working; the shortcut and the terminal start showing the
link with the token. Gabriel's decision.

### Item 8: visual QA of the words

Rendered with the band's real code (`CampoParticulasTexto`), at the width the band takes at
each resolution (`min(66vw, 1060px)`), with already spoken words on the left:

| Resolution | Band | Height of the current word | 27-letter word |
|---|---|---|---|
| 1920×1080 | 1060 px | ~70 px | 54 px, legible |
| 1366×768 | 902 px | ~60 px | 46 px, legible |

Accents (ç, ã, é, ú) and punctuation show up. The already spoken words are 13 to 16 px:
legible, but deliberately discreet. **Time until legible** (90% of the points less than 3 px
from the letter, coming out of distant dust): ~380 ms before; ~116 ms now (target ≤ 150 ms).
**Pending on the PC:** the same check on the whole HUD, with real speech and on Gabriel's screen.

### Item 9: measurement on Gabriel's PC (prepared; he runs it)

All with the real Nora: Qwen, Whisper and ElevenLabs on at the same time.

1. Terminal 1 (in `B:\Nora`): `scripts\iniciar_voz_windows.ps1 -Voz nenhuma` (the ear).
2. Terminal 2, with the `.venv` activated: `nora ouvir --hud`. In the HUD: **Visível**, quality
   **Detalhada**, **60 FPS**, "Palavras em partículas" checked.
3. Terminal 3, with the `.venv` activated:
   `powershell -ExecutionPolicy Bypass -File scripts\homologacao_windows.ps1 -SoMedir -Continuo`
   - phase 1 (60 s): it asks to **close the HUD tab** (baseline);
   - phase 2 (60 s): it asks to **open the HUD and talk** using the item 10 script;
   - then the 25 min soak test: leave the HUD open and talk now and then.
4. Send the `data\homologacao\AAAA-MM-DD_HHMM.txt` file and the `..._continuo.csv` spreadsheet.

| Measure | Where it comes from | Target |
|---|---|---|
| Frame time p50 / p95 / worst | HUD (`diagnostico_hud.json`) | p95 ≤ 33.3 ms |
| Sound → word delay p50 / p95 | HUD | p95 ≤ 100 ms |
| Extra CPU from the HUD | script (with HUD − baseline) | ≤ 10 percentage points |
| Extra VRAM from the HUD | script | ≤ 256 MB |
| Memory, VRAM, frame and WebGL contexts at start × end (25 min) | script `-Continuo` | no continuous growth; stable contexts |

The same numbers show in the HUD settings (the "Quadro p50 / p95 / pior" line). The sound →
word delay is measured by the HUD itself (how much of the word's audio had already played when it
appeared); it does not include the sound card's latency.

### Item 10: speech script (30 cases) and 60 FPS video

**Before:** the HUD on **Visível**, Detalhada, 60 FPS. Record the screen at 60 FPS: on Windows, in
**Settings → Gaming → Captures**, set "Video frame rate" to **60 fps**; then
**Win+Alt+R** starts and stops the recording (the browser must be in focus). Run `nora ouvir --hud`
with `--medir` to get the `[voz: ...]` line for each answer.

For each case, mark: ✅ ok, ✂️ cut, 🔇 silent, ⏸️ empty screen in a short pause,
🔁 repeated or out-of-order word, ⏱️ word late relative to the voice.

| # | Type | What to say (start with "Nora,") | What to check |
|---|---|---|---|
| 1 | Short | "que horas são?" | full answer; the word appears with the voice |
| 2 | Short | "bom dia" | same |
| 3 | Short | "obrigado" | same; disappears at the end |
| 4 | Short | "qual é a capital da França?" | same |
| 5 | Short | "me dá um número de 1 a 10" | legible digits |
| 6 | Long | "me conta uma história curta sobre um farol" | continuous speech (silence between chunks ~0 ms); words follow until the end |
| 7 | Long | "explica como funciona um arco-íris" | same; long words legible |
| 8 | Long | "descreve o seu dia ideal em detalhes" | same |
| 9 | Long | "lista cinco frutas e uma característica de cada" | same; pauses between items without an empty screen |
| 10 | Long | "fala sobre a história do café no Brasil" | accents (ç, ã, é) legible |
| 11 | Pauses | "conta até cinco devagar, com pausa entre os números" | the word stays during the pause; disappears only if the silence exceeds ~1.5 s |
| 12 | Pauses | "fala uma frase, espera, e fala outra" | same |
| 13 | Pauses | "recita um poema curto com pausas" | same |
| 14 | Pauses | "soletra a palavra coração" | letters and accents |
| 15 | Pauses | "diz 'hum…' e depois responde se vai chover" | ellipses do not leave the screen empty |
| 16 | Interruption | Long question (#6) and speak over it midway | the voice stops; the words disappear immediately |
| 17 | Interruption | Interrupt and ask something else | the new answer starts clean, with no words from the previous one |
| 18 | Interruption | Interrupt right at the start (first word) | nothing from the old answer comes back |
| 19 | Interruption | Interrupt twice in a row | same |
| 20 | Interruption | Interrupt on the last sentence | disappears immediately; nothing gets stuck |
| 21 | Privacy | During a long answer, click **Privado** | the words disappear immediately and do not come back until the end of the answer |
| 22 | Privacy | With Private on, ask a question | the voice speaks; no words on screen |
| 23 | Privacy | Go back to Visível in the middle of an answer | only the **next** answer shows words |
| 24 | Privacy | Toggle Visível/Privado 3 times quickly | no lost word appearing afterwards |
| 25 | Privacy | Reload the page (Ctrl+F5) in the middle of an answer | the HUD comes back without old words |
| 26 | Failure | Turn the internet off **before** asking | the fallback speaks the whole answer; `[voz reserva]` shows with the reason |
| 27 | Failure | Turn the internet off **in the middle** of a long answer | the fallback continues where it stopped, without repeating; or speech stops with a warning and "repete a resposta que caiu" repeats it all |
| 28 | Failure | Close the whisper-server and speak | clear warning; the HUD does not freeze |
| 29 | Resume | After #27 with a warning, say "repete a resposta que caiu" | the whole answer comes back, without asking the model again |
| 30 | Continuous | Talk normally for 5 min | no case cut or silent; stable FPS in the settings |

**Phase targets:** 0 answers cut or silent in the 30 cases; silence between chunks with p95 ≤ 150 ms
(`[voz: ...]` line); no empty screen in pauses under 500 ms; immediate clearing in 100% of
cancellations and privacy switches; sound → word delay p95 ≤ 100 ms (settings).

**Send:** the marked table, the video (or the parts with problems) and the item 9 files.
