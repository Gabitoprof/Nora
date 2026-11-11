# Nora HUD · v0.4.0 in development

A local presentation interface for the same Python core. The official reference is the PNG
approved in the task: black and silver, an open organic crown of filaments, diagonal rivers of
particles, restrained lighting, calibration arcs and discreet side panels. The scene is
procedural and animated; there is no second brain, microphone or TTS in the browser.

## Prepare and start

Requirements: the project's Python and Node.js LTS 22.13+ or 24 with npm. At the repository root:

```powershell
cd hud
npm ci
npm run build
cd ..
nora ouvir --hud
```

Open `http://127.0.0.1:8765` in the browser. The core still handles hands-free listening,
transcription, memory, game mode and speech. Closing the page does not stop those modules.
`nora hud` starts only the interface server; in that mode it reports that the core is
disconnected instead of making up audio or model data. Voice services and Ollama are
configured as in [the voice guide](../docs/VOZ.md).

To develop the interface, keep Nora's local server running and, in another terminal:

```powershell
cd hud
npm run dev
```

Vite listens only on `127.0.0.1:5173`. The `/api` proxy points to `127.0.0.1:8765`; it
normalizes Host/Origin only for local same-origin requests. Production serves the build from
the Python server itself, on the same origin. Do not expose ports on the network.

## State, privacy and supervision

- The authoritative JSON contract is [`src/nora/hud_contrato.json`](../src/nora/hud_contrato.json),
  imported by TypeScript. SSE `/api/eventos` carries versioned events; snapshots reset the
  sequence after a reconnect. Late or malformed events are ignored.
- States and audio levels come only from the Python pipeline. With no data, the level stays
  neutral. The resting waves represent visual presence, not a measured signal.
- Text and notes are hidden by default. The **Privado** (Private) button asks the server for
  consent; hiding clears local content immediately. No `localStorage`, `sessionStorage` or
  conversation cache. The browser does not ask for microphone permission and does not upload.
- Proposals use the existing domain service, via POST with a session token and confirmation.
  Approving only creates a task; it does not change code, publish or merge.
- Notes show only the results the core used from the explicitly authorized folder.
- Text is inserted with `textContent`; no answer or note is interpreted as HTML.

## Visuals, accessibility and performance

The crown and the particles use Three.js/WebGL with an economy option and a Canvas fallback.
The **Ajustes da interface** (interface settings) menu offers quality and a 30/60 FPS limit.
DPR is capped at 1.5; game mode lowers the rate to 8 FPS. The scene honors
`prefers-reduced-motion` and avoids drawing frames while the page is hidden. The emotional
palette is mostly monochrome, with silver/gold/pink/turquoise/terracotta/blue/lavender accents
according to real events.

**Palavras em partículas** (particle words) are optional, shown only with consent and in the
speaking state. Without phonetic timestamps from the TTS, the caption explicitly marks a visual
estimate; exact sync is not promised. The effect turns off with reduced motion or privacy.

The layout covers ultrawide, 16:9 and mobile screens. Controls have accessible names, visible
focus, decision confirmations and a fullscreen option. No external font, image or CDN is
requested at runtime. Measuring with Ollama/AMD GPU and the final look on real hardware remain
in the [cumulative checklist](../docs/HOMOLOGACAO.md).

## Verify

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

The tests cover the Python/TypeScript contract, out-of-order events and restarts, real
amplitude, privacy with SSE arriving before the HTTP response, and token renewal without
repeating actions on ambiguous failures. Visual tests use explicitly test data, never made-up
status at runtime. CI must pass on Windows and Ubuntu before a PR is considered ready.

v0.4.0 is not a published release. Integrated Windows/AMD acceptance depends on the owner's
approval; P3/P4, full MCP and distributed operation remain out of this scope.

On Windows, do not run the cloud Bash script. To fix Linux paths in PowerShell or an
environment created with Python 3.15, use the [Windows procedure](../docs/HUD.md#powershell-does-not-run-the-cloud-linux-script).

If opening from a link returns `Origem local obrigatória`, update the branch and restart the
Python server: the fix tells the initial public navigation apart from API access.
See [navigation troubleshooting](../docs/HUD.md#the-hud-returns-origem-local-obrigatória-when-opened-from-a-link).

## Ideas

- Create a step-by-step guide so users have individual experiences: each Nora has its own identity.
