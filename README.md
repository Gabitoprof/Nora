# Nora

A personal AI assistant that **talks by voice in real time**, runs **mostly on your computer**, remembers what you talked about and gets better with use. Inspired by the assistants of fiction, with its own configurable name, voice and personality.

> **Status:** `v0.3.0` (**model router**): Nora wakes up on her name, listens, talks on the local model and sends the hard questions to **ChatGPT, with Claude as fallback**, always answering with the same voice, emotion and memory. Next stage: `v0.4.0` (HUD). See the [roadmap](docs/MAPA_MENTAL.md#2-roadmap-by-stage).

## What she already does

- **Hands-free voice conversation:** start the sentence with "Nora" and she answers out loud, sentence by sentence, while still thinking. You can also type and hear the answer.
- **Thinks on your PC, and calls the cloud when needed:** the local model through [Ollama](https://ollama.com) (Qwen 3.5 9B on a 16 GB GPU) talks at no cost; the hard questions go up to ChatGPT, with Claude as fallback (both optional, with your own key), in the same voice. "Modo jogo" (game mode) frees the graphics card.
- **Several voices:** Kokoro (local, free, default), Piper (local; you can train your own), ElevenLabs (cloud, the most natural) and ComfyUI (voices you create). A fallback voice takes over on its own if the main one fails, and you can switch voices by speaking ("troque para a voz do Piper").
- **Emotion in the voice:** she picks the tone of each sentence on her own (happy, tender, calm, laughing, whispering...) from the context; on ElevenLabs v3 she really laughs, sighs and whispers.
- **Memory:** notes facts about you by area (health, studies, work...), keeps every full conversation, finds appointments by day ("o que tenho amanhã?") and learns how you want her to speak (pronunciations, way of answering, the tone that works with you). She also reads your Obsidian notes to answer ("o que eu anotei sobre a prova?").
- **You give orders by voice:** "use o cérebro local", "use o Claude", "modo jogo" (frees the graphics card; to leave it, she asks for confirmation), "troque para a voz do Piper", "esquece isso", "apaga de vez ..." (with confirmation), "termina a resposta que ficou pela metade".
- **Does not lose answers:** if an answer drops in the middle, is cancelled or gets no reply, the question is kept so you can resume it later.
- **Improves under supervision:** once a day she gathers what went wrong (slow, failures, complaints) into a report of proposals, without storing the text of the conversations. Nothing changes without your approval.
- **Respects the rest of the PC:** lowers the volume of other programs while she speaks.
- **Private:** memory, history and personal settings stay in `data/` and `config/local.toml`, only on your machine.

## Requirements

- Python 3.11 to 3.13 (**recommended: 3.13**). The voice (onnxruntime) has no packages for Python 3.15 yet.
- [Ollama](https://ollama.com) with the conversation model and the memory model: `ollama pull qwen3.5:9b` and `ollama pull bge-m3`.
- Windows or Linux. Developed on an AMD GPU (Vulkan); CUDA and CPU also work.

## Getting started

```bash
git clone https://github.com/gabitoprof/nora.git
cd nora
python -m venv .venv
```

Activate the environment (Windows: `.venv\Scripts\activate`; Linux/macOS: `source .venv/bin/activate`) and install with voice and memory:

```bash
pip install -e ".[voz,memoria]"
```

```bash
nora --verificar
```

Shows the loaded config and checks Ollama, the ear (speech recognition), the voice and the memory.

### 1. Talk by text

```bash
nora conversar
```

`sair` exits and `/limpar` starts over; `--medir` shows the time of each answer.

### 2. Talk by voice

Install and start the ear (whisper.cpp) and a local voice, only once (step by step for Windows in [docs/VOZ.md](docs/VOZ.md)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1
```

```powershell
.\scripts\iniciar_voz_windows.ps1
```

Then, hands-free (start the sentence with "Nora"; you can also type):

```bash
nora ouvir
```

Or press Enter to speak and Enter to stop: `nora falar`. To type and hear the spoken answer: `nora conversar --voz`.

### 3. Memory

It comes on by default. She notes on her own what is worth remembering and shows `[memória] anotei: ...` in the conversation.

| Command | What it does |
|---|---|
| `nora memoria listar` | What she remembers about you (20 per page) |
| `nora memoria agenda` | Appointments and dates for the next 30 days |
| `nora memoria marcar 21/11/2026 prova` | Adds something to the agenda by hand |
| `nora memoria pronuncias` | The pronunciations she learned |
| `nora memoria preferencias` | How you asked her to speak |
| `nora memoria esquecer 12` | Deletes a fact |

| `nora memoria apagar "assunto"` | Shows what would be removed; with `--confirmar`, deletes it for good (also from history) |
| `nora pendencias` | Answers left halfway |

If an answer is left halfway, say "termina a resposta que ficou pela metade". Everything in [docs/MEMORIA.md](docs/MEMORIA.md). For Nora to read your Obsidian notes: `[notas] pasta` in `config/local.toml` and `nora notas ler` (see [docs/OBSIDIAN.md](docs/OBSIDIAN.md)).

### 4. Cloud (optional)

With `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in `.env` and `pip install -e ".[nuvem]"`, the hard questions go to ChatGPT, with Claude as fallback. With no key at all, everything stays on the PC. Commands and settings in [docs/CEREBRO.md](docs/CEREBRO.md).

### 5. Self-improvement

It comes on by default: the daily report shows up on its own (default: 20:00). To decide:

| Command | What it does |
|---|---|
| `nora melhorias listar` | Proposals waiting for a decision |
| `nora melhorias relatorio --abrir` | Opens the latest report |
| `nora melhorias aprovar 3` · `recusar 3` · `adiar 3` | Decide (approving only produces the specification; the code does not change) |

Details in [docs/AUTO_MELHORIA.md](docs/AUTO_MELHORIA.md).

## Customizing

- **`config/nora.toml`**: default config (name, persona, voice, emotion, memory, models). Do not put anything personal here.
- **`config/local.toml`**: create this file with only what you want to change. Git ignores it. Example:

  ```toml
  [usuario]
  nome = "Seu nome"

  [persona]
  humor = 0.6

  [voz]
  motor = "elevenlabs"   # kokoro, piper, elevenlabs or comfyui
  reserva = "kokoro"

  [emocao]
  intensidade = 0.5      # 0 = no emotion, 1 = very expressive
  ```

- **`.env`**: copy it from `.env.example` to keep API keys (ElevenLabs, OpenAI, Anthropic). Git also ignores it. For the cloud: `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in `.env` and `pip install -e ".[nuvem]"` (see [docs/CEREBRO.md](docs/CEREBRO.md)).

## Structure

| Folder | Contents |
|---|---|
| `src/nora/` | Python core (conversation, router, voice, memory, agenda, emotion, notes, self-improvement) |
| `config/` | Default config |
| `recursos/` | Voice training sentences |
| `scripts/` | Install and start the voice, GPU test, Piper training notebooks (Kaggle and Colab) |
| `tests/` | Automated tests (`pytest`) |
| `docs/` | Documentation, mind map and references (file names kept in Portuguese) |
| `hud/` | Visual interface (web, from v0.4.0) |
| `mcp_servers/` | Tools following the MCP standard (from v0.5.0) |
| `data/` | Memory and personal data. **Created on your machine, never goes to Git.** |

## Documentation

- [Project goal](docs/OBJETIVO.md)
- [Mind map and roadmap](docs/MAPA_MENTAL.md)
- [Full project document](PROJETO_ASSISTENTE_IA.md)
- [Brain: local, ChatGPT, Claude and router](docs/CEREBRO.md)
- [Voice: install, engines, emotion, pronunciation](docs/VOZ.md)
- [Memory: facts, agenda, learning from conversation](docs/MEMORIA.md)
- [Self-improvement: daily report of proposals, with your approval](docs/AUTO_MELHORIA.md)
- [Train your own voice (Piper)](docs/TREINAR_VOZ.md)
- [GPU test](docs/TESTE_GPU.md)
- [Obsidian: the project as a vault and Nora reading your notes](docs/OBSIDIAN.md)
- [Third-party licenses](docs/LICENCAS.md)
- [Version history](CHANGELOG.md)

## License

Copyright © 2026 Carlos Gabriel Moura Santiago. **All rights reserved.** The code is public for reference only; using, copying, modifying or distributing it requires written permission (see [LICENSE](LICENSE)). Versions up to `v0.3.0` were released under MIT and remain under MIT.

Programs, AI models and voices that Nora uses have their own licenses and are downloaded separately: see [docs/LICENCAS.md](docs/LICENCAS.md).
