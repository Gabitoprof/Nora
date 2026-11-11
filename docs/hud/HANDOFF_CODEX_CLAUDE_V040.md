# Handoff Codex → Claude Code — HUD v0.4.0

## Checkpoint A — base and scope

- Work branch: `codex/hud-v040-particles-final`.
- Confirmed remote base: `integracao/v0.4.0`, SHA `1f96bcc98efb598e1bc63e4efcb6c29f050da774`.
- The ElevenLabs v4 Turbo/alignment pipeline already belongs to the base; keep its interfaces,
  first playback, continuity and privacy. Do not make paid calls for tests.
- Last remote SHA confirmed before this checkpoint: the base SHA above.
  This document will be pushed as the first checkpoint; check `git ls-remote origin
  refs/heads/codex/hud-v040-particles-final` to confirm the current head.
- Do not change main, Pull_code or Second Brain, do not merge, release or force push.

## Available references

Dark image provided in this conversation: an asymmetric crown of filaments, outer dust,
the NORA mark and words materially made of particles; a horizontal bottom panel.
Video attached later and watched: 30.785 s, 576×288, 30 FPS. Motion reference
(dust → glyph formation → hold → dispersal); do not copy the video's colors or content. There is no licensed Nasalization font in the checkout:
use mask infrastructure with a system fallback, without downloading/redistributing a font.

## Plan and responsibility

- A: inventory and baseline (running).
- B: stable pool, real formation/hold/dispersal of the glyphs; mark and header.
- C: review alignment → PCM position; last chunk, cancellation and privacy.
- D: shared dark tokens and reactive bands; keep the layout, remove only slogans.
- E: regressions, comparable synthetic benchmarks, captures/replay, checklist and CI.

Reference tests are running; no new result counts as approved
before they finish. Windows/AMD hardware and real ElevenLabs latency are not
reachable from the cloud. The user's metrics (265–985 ms to first audio, 946–1555 ms to
playback and 0 ms between chunks) are historical, not measurements of this branch.

## Resuming

Read CLAUDE.md, docs/ANDAMENTO.md and this file; check `git status`, the log and the remote head.
Keep each slice testable, run proportionate checks, commit and push.
Confirm the SHA via `git ls-remote` after each push; local commits/ZIPs are not enough.
Do not implement new features if there is no budget left to validate and keep the checkpoint.

## Checkpoint B — particles and UI

- First confirmed remote checkpoint: `e2d7395233306912978f525f55cdca5ee8dbd937`.
- Reusable particle engine with stable IDs/pool, position/velocity and a damped spring.
  The mask provides targets; the canvas draws moving bodies, not a static image.
- The central mark uses the engine with the system Arial fallback (Nasalization absent).
  Only the accessible heading stays in HTML. Slogans/ornaments removed; functions kept.
- The header uses the media clock; reduced mode shows an authorized static alternative.
- Shared palette `src/nora/paleta.json`: aliases kept, restrained cool dark tones.
  The bottom band responds to mic/voice; a 120 FPS limit added without raising game mode (8 FPS).
- Frontend: lint/typecheck/47 tests/build approved. The Three library split into a stable
  chunk, without raising the warning limit. Python baseline: 465 passed/2 skipped;
  one of the skipped was the v4 module for missing websockets. The already declared dependency
  is being installed for final validation; CI starts installing it explicitly.
- Next checkpoint C: reproduced regressions of alignment/padding, fragments,
  final metadata and natural end vs cancellation; a benchmark found overhead in the base
  still being fixed. Do not claim the p95≤5% target until the result is measured.

## Claude Code resume — 07/11/2026

### Audit (before editing)

- `integracao/v0.4.0`: local and remote at `1f96bcc` (no Codex commits on it).
- Codex's work: branch `codex/hud-v040-particles-final`, `b5cbe44` (2 commits on top of `1f96bcc`:
  `e2d7395` handoff, `b5cbe44` particles). The recorded Git author is another identity; Codex's
  authorship comes from this document, not from Git.
- CI of `b5cbe44`: red on all 7 jobs. Reproduced causes: the emotion palette
  (`src/nora/paleta.json`) was replaced by near-white tones (breaks `test_paleta`,
  `test_segundo_cerebro` and the clean install) and a HUD test compared `undefined`.
- Codex's checkpoint C (alignment/last fragment) was not done; the front end consumed
  `reproducao_encerrada`, but the backend never sent it and the contract did not list it.
- References: approved dark image (attached in the conversation) and 30.8 s video (576×288) watched.
  They are not in the repository. No licensed Nasalization font available.

### Branch and commits of the resume

Branch `refino/hud-v040`, created from `codex/hud-v040-particles-final`. No merge into
`integracao/v0.4.0`, `main`, `Pull_code` or Second Brain.

| Commit | Batch | What changed |
|---|---|---|
| `4588d1c` | 1 | Approved palette restored; the HUD mixes each emotion at 20% into a silver-cyan (`state.ts`: `PRATA`, `misturar`, `cores`). CI green on all 7 jobs. |
| `53c29dd` | 2 | NORA mark in the own geometric alphabet (`geometric-glyphs.ts`): original code-drawn design, no font file; mask sampling without stripes; larger particles with a halo. |
| `a9ac07b` | 3 | Speech band: large current word; up to 3 already spoken words smaller and dimmer on the left, in the same cloud (never the next ones); holds 320 ms between words so it does not flicker. |
| `c39dc44` | 4 | `reproducao_encerrada` event in the contract and the backend (id, position, duration, interrupted; no text): natural end keeps the last word, barge-in clears it. |
| (this one) | 5 | Handoff, evidence, `scripts/hud_cenario.py`. |

### Status by requirement

| Requirement | Status | Where |
|---|---|---|
| Dark look, silver with restrained cyan | Done | `state.ts` (`cores`), approved palette kept |
| NORA made of real particles, geometric Nasalization-like style | Done (own design, not Nasalization) | `geometric-glyphs.ts`, `text-particle-field.ts`, `main.ts` |
| Speech words form, hold and disperse by the audio's time | Done | `word-particles.ts` (PCM clock), `text-particle-field.ts` |
| Speech line with context, without running ahead | Done | `word-particles.ts` (`ANTERIORES`, `SEGURAR_MS`) |
| Natural end vs barge-in | Done | `hud.py` (`reproducao`, `_encerrada_valida`), `audio.py` |
| Privacy (no text without permission; revoking clears) | Kept from Codex, tested | `word-particles.ts`, `hud.py` |
| Reduced motion | Kept from Codex, tested | `word-particles.ts`, `scene-audio.ts` |
| Bottom wave and ring reacting to real audio | Existing base; not changed in this resume | `scene-audio.ts`, `scene.ts` |
| Visual comparison with the real GPU (Windows, RX 9060 XT) | Pending (manual) | — |

### QA and metrics

- `ruff format --check`, `ruff check`, `pytest`: 486 passed, 2 skipped.
- HUD: `npm run lint`, `typecheck`, `test` (65), `build`: approved.
- Clean install (`scripts/testar_instalacao_limpa.py`): approved.
- Playback start with the HUD bridge on (method: `_tocar_partes` with a fake output at 8×
  real time, PCM arriving in 200 ms pieces, 60 samples per series, cloud Linux):
  base `1f96bcc` p50 11.2 ms / p95 21.1 ms; `c39dc44` p50 11.1 ms / p95 21.3 ms (+0.9%, within
  noise; target ≤ 5%). Does not replace the measurement with real ElevenLabs on Windows.
- Audio→visual delay and envelope→wave correlation: **not measured** (the cloud's GPU-less Chromium
  takes 2 to 12 s per capture during speech; frame-by-frame measurement is not possible here).

### Evidence

- `docs/hud/evidencias/hud-repouso-marca-particulas.jpg`: real HUD (server + build) at rest.
- `docs/hud/evidencias/alfabeto-geometrico.jpg`: geometric alphabet formed by particles.
- `docs/hud/evidencias/faixa-da-fala.jpg`: speech line (current word + previous ones).
- Captures of the whole HUD during speech: pending (the GPU-less browser limitation above).

### How to resume

1. `git fetch origin refino/hud-v040 && git switch refino/hud-v040`.
2. `cd hud && npm ci && npm run build`, then `python scripts/hud_cenario.py` and open the address;
   type `falar` to see the mark, the speech line and the wave with a synthetic aligned utterance.
3. Validation: `ruff format --check . && ruff check . && pytest`; in `hud/`:
   `npm run lint && npm run typecheck && npm test && npm run build`.

### Pending items (suggested order)

- [ ] Visual acceptance on Windows with the RX 9060 XT: mark, speech line with the real ElevenLabs v4,
      bottom wave, FPS; compare with the approved image.
- [ ] Measure on Windows the playback start with and without the HUD (p50/p95) and the audio→word delay.
- [x] Nasalization: the mark uses the font **if it is installed on Windows** (`fontesInstaladas` in
      `main.ts`); without it, the own alphabet. The file (Typodermic, fsType 4 "preview and
      print") cannot be embedded. Tested in the cloud with the font installed outside the repository:
      `docs/hud/evidencias/hud-repouso-nasalization-instalada.jpg`.
- [x] Speech line: Gabriel's decision (07/11) — only the words already spoken, never the next ones.
- [x] Merge authorized by Gabriel (07/11): `refino/hud-v040` fast-forwarded `integracao/v0.4.0` to
      `f89d89d` (fast-forward, no merge commit).

### Gabriel's acceptance run (06/11, evening) and adjustments

- The first opening on Windows showed the old HUD (build `3eeba77`): an old Nora was holding
  the port. After stopping the processes and rebuilding, it loaded `93f870f`.
- Findings on Windows: the formed mark sat **still** and did not interact with the dust; the
  "Palavras em partículas" option showed unchecked (form state restored by the browser).
- Fix: `Vida` in `text-particle-field.ts` (tremor, flow out to the dust and back, free dust
  around) and audio energy (`QuadroVisual.energia`, the same signal as the ring) raising
  motion and brightness; words with a light tremor; `autocomplete="off"` on the words option.
  Reduced motion stays still. Video: `docs/hud/evidencias/marca-viva.mp4`
  (0–4 s at rest, 4–8 s with a simulated voice).

### Second round on Windows: "too simplistic" (07/11)

Compared with the approved image, light, the bottom wave and the link between the letters and the dust were missing.

- `d191bc7`: bloom (UnrealBloomPass) in the Detailed quality, scene on black blended with
  `mix-blend-mode: screen` (the page background stays); brighter ring, dust and cyan
  highlights; a living bottom wave (`ondaInferior`, peak at the center, reacts to voice/microphone).
- This batch: `Camada` (the `#letras` canvas over the HUD) and `Cena.poeiraNaTela`. Each point of the mark
  and the words is tied to a grain of the orbiting dust: it leaves it in a staggered stream (mark:
  1.6 s; words: 110 ms), with a trail, forms the letter, now and then goes back to the grain and returns, and
  on dispersal goes back to the orbit. Video with the layer's real code and a simulated orbit:
  `docs/hud/evidencias/letras-da-poeira.mp4`.
- Performance: no CSS filter on the full-screen layer (it was too costly); halo drawn in the canvas.
  Measure FPS on Windows.
