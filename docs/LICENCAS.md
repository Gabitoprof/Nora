# Licenses

## Summary

- **Nora's code** is **all rights reserved** ([LICENSE](../LICENSE)): public for reference, with no permission to use, copy or redistribute without authorization. Versions up to `v0.3.0` were released under MIT and remain under MIT.
- **The programs, models and voices Nora uses are not in the repository** and have their own licenses. They are installed or downloaded separately (through `pip`, the scripts in `scripts/` or the tool itself) and Nora talks to them over the local network or as a separate process. **By downloading each one, you accept its license.**
- **What is yours never goes into the repository:** memory and history (`data/`), keys (`.env`), personal config (`config/local.toml`), ComfyUI flows (`config/voz_comfyui.json`) and models and voices (`models/`).

> Checked on 31/10/2026, on each project's page or license file. Licenses change: before redistributing anything, check the current version at the source.

## Python dependencies (`pyproject.toml`)

| Package | License | Extra | What for |
|---|---|---|---|
| sounddevice (uses PortAudio, MIT) | MIT | `voz` | Microphone and speaker |
| numpy | BSD-3-Clause (and MIT, 0BSD, Zlib, CC0 parts) | `voz` | Audio (resampling, measurements) |
| onnxruntime | MIT | `voz` | Running Silero VAD |
| soundfile (uses libsndfile, LGPL-2.1, as a dynamic library) | BSD-3-Clause | `voz` | Reading FLAC, MP3 and WAV |
| pycaw | MIT | `voz` (Windows) | Lowering the volume of other programs |
| websockets | BSD-3-Clause | `voz` | ElevenLabs v4 (real-time dialogue) |
| kokoro-onnx | MIT | `kokoro` | Kokoro local voice |
| phonemizer-fork and espeakng-loader (bring espeak-ng) | GPL-3.0 | `kokoro`, indirectly | Phonemes for Kokoro |
| sqlite-vec | MIT or Apache-2.0 (your choice) | `memoria` | Vector search for memory |
| anthropic (official Claude SDK) | Apache-2.0 | `nuvem` | Cloud brain: Claude |
| openai (official OpenAI SDK) | Apache-2.0 | `nuvem` | Cloud brain: ChatGPT, default for complex questions |
| pytest | MIT | `dev` | Tests |
| ruff | MIT | `dev` | Formatting and lint |
| pyinstaller | GPL-2.0-or-later with a bootloader exception (allows distributing non-free programs built with it) | `empacotar` | Building `nora.exe`; build-time only, not shipped as a library inside the program |

**Inside `nora.exe`:** Python (PSF-2.0) and the packages of the `voz`, `memoria` and `nuvem` extras with their dependencies. The build copies each one's license notice into the program's `licencas` folder (`empacotamento/juntar_licencas.py`). libsndfile (LGPL-2.1, from `soundfile`) and PortAudio (MIT, from `sounddevice`) ship as separate libraries (DLLs) in the program folder. Kokoro, Piper and espeak-ng do **not** go into the `.exe`.

**Installer tool:** [Inno Setup](https://jrsoftware.org/isinfo.php) 6, with its own license ([license.txt](https://github.com/jrsoftware/issrc/blob/main/license.txt)): it allows use "for any purpose, including commercial applications", keeping the copyright notices. Used only to build the installer.

**Programs the dependency pack installs** (each with its own license, accepted on install): Ollama (MIT), whisper.cpp (MIT), Whisper models (MIT), `qwen3.5:9b` and `bge-m3` (table below) and the Visual C++ Redistributable (Microsoft license).

**About espeak-ng's GPL:** Kokoro (which uses espeak-ng, GPL-3.0) runs in a separate process (`nora servidor-kokoro`) and is installed separately, through the `kokoro` extra. Distributing Nora together with it requires complying with GPL-3.0.

## Web HUD (`hud/package-lock.json`)

Licenses checked in the metadata and license files of the installed packages, without copying
third-party code into the core. The lockfile pins the versions actually used.

| Package | Installed version | License | Use |
|---|---|---|---|
| [three](https://github.com/mrdoob/three.js) | 0.173.0 | MIT | WebGL waves and particles; own Canvas fallback |
| [@types/three](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/three) | 0.173.0 | MIT | Development types |
| [vite](https://github.com/vitejs/vite) | 6.4.5 | MIT | Local development server and build |
| [typescript](https://github.com/microsoft/TypeScript) | 5.9.3 | Apache-2.0 | Type checking |
| [vitest](https://github.com/vitest-dev/vitest) | 5.1.0 | MIT | Automated interface tests |
| [eslint](https://github.com/eslint/eslint) | 10.14.0 | MIT | Static analysis |
| [typescript-eslint](https://github.com/typescript-eslint/typescript-eslint) | 8.72.1 | MIT | TypeScript static analysis |
| [@types/node](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/node) | 22.20.5 | MIT | Node types for the tooling tests |
| [minimatch](https://github.com/isaacs/minimatch) | 11.0.4 | BlueOak-1.0.0 | Transitive lint/parser dependency, with an override of vulnerable versions |

The minimatch override applies only to the vulnerable range `>=7.0.0 <11.0.1`.
ESLint and typescript-eslint still declared versions in that range; version 11 keeps
the APIs actually used by those consumers (named function and `Minimatch.match`).
Specific glob/dotfiles/negation/extension tests, plus the project's lint, check
compatibility; full API equivalence across major versions is not claimed.
BlueOak-1.0.0 is permissive; the license was read in the installed package. The license file
comes with the installation of the dependency pinned by the lockfile, without bringing code into the Python core.

The procedural drawing follows the reference PNG provided by the owner. No model,
remote font, third-party image or external service is needed to render the HUD.
The SSE bridge uses Python's standard library and adds no Python dependency.

## Separate programs

| Program | License | How Nora uses it |
|---|---|---|
| [Ollama](https://github.com/ollama/ollama) | MIT | Local brain and embeddings, through the local API |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT | Ear (`whisper-server`), through the local API |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper1-gpl`) | GPL-3.0 | Local voice (separate HTTP server) and voice training (only on Google Colab) |
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI) | GPL-3.0 | Optional: creating a voice, through the local API |

None of them is copied into the repository.

## Models and voices

| Model or voice | License | Note |
|---|---|---|
| Silero VAD | MIT | Downloaded from the official `silero-vad` package |
| Whisper (weights, e.g. `ggml-small`, `ggml-large-v3-turbo-q5_0`) | MIT | Downloaded by `scripts/instalar_voz_windows.ps1` (the model chosen in `-ModeloWhisper`) |
| Qwen 3.5 (`qwen3.5:9b`, through Ollama) | The model's own license | Check at [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5) |
| bge-m3 (memory embeddings) | MIT | Downloaded by Ollama |
| Kokoro-82M (weights) | Apache-2.0 | Downloaded separately into `models/kokoro` |
| Ready-made Piper voices (e.g. `pt_BR-faber-medium`) and training checkpoints (`rhasspy/piper-checkpoints`, e.g. `cadu`) | One license per voice (see each one's `MODEL_CARD`) | Many derive from the `lessac` voice, which is **non-commercial use only**. Use them for personal purposes, or pick a voice with an open license |
| Qwen3-TTS (in ComfyUI) | Apache-2.0 | Optional, to create a voice |

## Cloud services (optional)

| Service | Terms | Note |
|---|---|---|
| OpenAI API (ChatGPT) | OpenAI terms of use | Requires your own key (`OPENAI_API_KEY` in `.env`) and is billed per use. The router's default for complex questions; what goes to the API is that question's conversation, with the persona and the memory notes |
| Anthropic API (Claude) | Anthropic commercial terms | Requires your own key (`ANTHROPIC_API_KEY` in `.env`) and is billed per use. Used by the router (v0.3.0) for hard questions, in cloud mode and in game mode; what goes to the API is that question's conversation, with the persona and the memory notes |
| ElevenLabs | ElevenLabs terms of use | Requires an account and your own key (`.env`). **Do not use the generated audio to train another voice**: the terms do not allow it |

## A voice you trained

A voice trained with `nora voz gerar-dataset` and `scripts/treinar_piper_colab.ipynb` inherits the conditions of everything that went into it:

- **the model that generated the audio** (e.g. Qwen3-TTS, Apache-2.0; the pt-BR F5-TTS, which is CC-BY-NC-4.0, would only allow non-commercial use);
- **the base Piper voice** used for fine-tuning (many are non-commercial only);
- **the person behind the voice:** only use a voice created from scratch or from someone who **authorized** it. Do not imitate actors, characters or real people.

When in doubt, keep the trained voice **for personal use** and out of Git (`models/`, already in `.gitignore`).

## Name and brand

The project does not use names, logos or visual references of characters or registered trademarks (for example, "Jarvis" or Marvel). The assistant's name comes from the config.

## Fonts

- **NORA mark in the HUD:** an original geometric alphabet, drawn in code (`hud/src/geometric-glyphs.ts`). It is not a third-party font; nothing to license.
- **Nasalization (Typodermic Fonts):** the HUD uses it **only if it is installed on the user's computer** (detected by the width measured in the browser). The font file (version 5.000) carries Typodermic Fonts' copyright, "Nasalization" as their registered trademark and embedding permission only for "preview and print" (fsType 4): it **cannot be embedded** in the repository, the HUD build or `nora.exe`. Personal use, installed on your own Windows, works.

## When adding something new

Every new dependency, program, model or voice goes on this page, with the license checked at the source, in the same commit that adds it. A test (`tests/test_licencas.py`) fails if a `pyproject.toml` package is not listed here.
