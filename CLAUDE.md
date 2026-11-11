# CLAUDE.md

Nora project rules for Claude Code. Details in `PROJETO_ASSISTENTE_IA.md`.

## What it is

A personal real-time voice AI assistant, local first, with a memory that evolves. Built in stages (`v0.0.0` → `v1.0.0`), each one a working version. The repository is public for reference only, all rights reserved (MIT up to v0.3.0); it is meant to be sold, and anything opened up goes to a separate repository.

## Language

- **Documentation and code comments/docstrings in English.**
- **Everything the user sees or hears stays in Portuguese (pt-BR):** Nora's speech and persona, messages, CLI help, voice commands, HUD text, config keys and the generated Second Brain notes.
- **Names in the code** (modules, functions, classes, variables, files) stay in **pt-BR**; do not rename them for translation.
- Commits in English, following **Conventional Commits** (`feat:`, `fix:`, `docs:`...).

## Architecture (section 2 of the document)

- Voice pipeline, all streaming: wake word (openWakeWord) → VAD (Silero) → STT (whisper.cpp with Vulkan) → LLM → TTS (Piper), with barge-in. Target: under 1 s (MVP: under 2 s).
- Hybrid brain: conversation on the **local** model (Ollama, `keep_alive` to free VRAM); heavy tasks on the **API** (Claude), with a holding phrase and the same voice. Game mode unloads the model from VRAM.
- Memory: **SQLite + sqlite-vec** in `data/` (raw history, curated memory, knowledge). History kept from day one.
- Every tool follows the **MCP** standard (`mcp_servers/`). Orchestrator = persona; specialists are tools.
- Web HUD in `hud/` (TypeScript). Separate components talking over the local network (distributed mode in v0.8.0).

## Target hardware (section 3)

- **AMD RX 9060 XT 16 GB** GPU (RDNA 4) on **Windows**: **avoid CUDA-only tools**; use Vulkan (ROCm on Linux). Backends always swappable (Vulkan, ROCm, CUDA, CPU).
- VRAM: LLM ~9–10 GB + Whisper ~1–2 GB + headroom.

## Public repository (section 6), mandatory

- **Nothing personal in the repository.** Keys only in `.env`; personal config only in `config/local.toml`; `data/` never goes to Git.
- **Do not use** "Jarvis", Marvel or their visual references in name, logo or promotion.
- The assistant's name always comes from the config.
- Check the license of every model and voice; prefer redistributable ones or download them separately via script. AGPL code does not go into the repository.
- **`.env.example` follows `.env`:** every new variable (key, address, option) goes into `.env.example` in the same commit, with a comment on what it is and where to get it, but **no personal value** (keys always empty). `tests/test_env_exemplo.py` checks that every variable the code reads is there and that no key is filled in.
- Every new dependency, program, model or voice goes into `docs/LICENCAS.md` in the same commit, with the license checked at the source (`tests/test_licencas.py` checks the `pyproject.toml` dependencies).
- Original voice: do not imitate the voice of a real actor or character.

## Workflow

- Versions `vMAJOR.MINOR.PATCH`: each stage bumps MINOR, fixes bump PATCH. Git tag and a `CHANGELOG.md` entry per version.
- When a stage is done: update the status in `docs/MAPA_MENTAL.md` **and** `docs/MAPA_MENTAL.canvas` (⬜ → 🔄 → ✅).
- When a stage is done, **review and rewrite all documentation** for the new state, not only the CHANGELOG: `README.md` (status, what it does, getting started, commands), the section 5 roadmap of `PROJETO_ASSISTENTE_IA.md` (status and actual deliveries), `docs/OBJETIVO.md`, the mind map (new nodes and status), the guides in `docs/` and the idea bank (what became real). No text describing an old version as current.
- Standard Markdown links (not `[[wikilinks]]`), so they work on GitHub and in Obsidian.
- Before committing: `ruff format .`, `ruff check .` and `pytest`.

## Integrated acceptance testing

Follow the strategy and keep the [cumulative per-module checklist](docs/HOMOLOGACAO.md).
Write and run unit, integration and regression tests for the changes, keeping the existing
ones. A ready PR needs green CI on Windows and Linux on the evaluated commit; that does not
mean full functional acceptance. The final integrated acceptance will be on Windows with the
AMD GPU at the end of the planned implementation. During development, one-off manual tests
only when essential for hardware or external integration. Do not ask to repeat approved
manual tests unless the component is directly affected; keep their evidence.
Merging into `main`, merges, tags and publishing still require explicit authorization.
