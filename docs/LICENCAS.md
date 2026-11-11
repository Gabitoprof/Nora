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
| kokoro-onnx | MIT | `kokoro` | Kokoro local voice |
| phonemizer-fork and espeakng-loader (bring espeak-ng) | GPL-3.0 | `kokoro`, indirectly | Phonemes for Kokoro |
| sqlite-vec | MIT or Apache-2.0 (your choice) | `memoria` | Vector search for memory |
| anthropic (official Claude SDK) | Apache-2.0 | `nuvem` | Cloud brain: Claude |
| openai (official OpenAI SDK) | Apache-2.0 | `nuvem` | Cloud brain: ChatGPT, default for complex questions |
| pytest | MIT | `dev` | Tests |
| ruff | MIT | `dev` | Formatting and lint |

**About espeak-ng's GPL:** Kokoro runs in a separate process (`nora servidor-kokoro`), and Nora only talks to it over HTTP. Nora's code imports nothing GPL, so it is not subject to the GPL. Whoever redistributes a package with the `kokoro` extra installed must comply with the GPL-3.0 for that part.

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
| Whisper (weights, e.g. `ggml-small`) | MIT | Downloaded by `scripts/instalar_voz_windows.ps1` |
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

## When adding something new

Every new dependency, program, model or voice goes on this page, with the license checked at the source, in the same commit that adds it. A test (`tests/test_licencas.py`) fails if a `pyproject.toml` package is not listed here.
