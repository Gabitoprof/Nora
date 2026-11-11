# Personal Voice AI Assistant: Project Document

> Starting document for developing the project in Claude Code.
> Origin: planning conversation on 29/10/2026.
> Author: Gabriel (Carlos Gabriel Moura Santiago)

---

## 1. Vision

Create a **real-time voice conversation AI**, with its **own exclusive name, voice and identity**.

- **Focus:** the AI talking in real time. A touch table with a projector is **not a priority**.
- **Development:** in stages, each one producing a working version.
- **Distribution:** public repository for reference only, all rights reserved (MIT up to v0.3.0), with commercialization in mind. Anything opened up in the future goes to a separate repository.

### What creates the immersion
- Natural voice and fast answers.
- Interface reacting to speech (an animated orb, clock, cards with the spoken content).
- **Own initiative:** the AI speaks without being called, for example in a morning routine with the date, a message and the plan for the day.

---

## 2. Defined architecture

### 2.1 Real-time voice pipeline
1. **Wake word** with the custom name: openWakeWord (free, trainable) or Porcupine. Runs locally, on the CPU.
2. **VAD** (speech detection): Silero VAD.
3. **STT** (streaming transcription): **whisper.cpp with Vulkan**. faster-whisper requires CUDA/NVIDIA and does not work on the AMD GPU.
4. **Brain (LLM)**: see 2.2.
5. **TTS** (streaming voice, sentence by sentence): Piper (local, CPU). Cloud options: ElevenLabs or Cartesia.
6. **Barge-in**: interrupting the AI by speaking over it. Requires **echo cancellation** and a good microphone.
7. **Latency target:** < 1 s between stopping speaking and hearing the answer (MVP: < 2 s). Only reachable with everything streaming.

### 2.2 Hybrid brain (Gabriel's decision)
- **Everyday conversation → LOCAL model** via Ollama or LM Studio (ROCm or Vulkan backend). Suggestion: a quantized 12–14B model (Qwen or Gemma), using about 9–10 GB of VRAM.
- **Heavy reasoning → external models via API** (Claude and others). The local model decides when to escalate the task.
  - While waiting, the local AI says something like "deixa eu analisar isso" (let me look into that), so it is not silent.
  - The answer comes back and is spoken with the same voice and persona.
- **Game mode:** when a heavy game opens, the local model leaves VRAM and the conversation goes to the API.
- **Automatic unloading:** use Ollama's `keep_alive` to free VRAM after a while unused.

### 2.3 Local database that evolves (Gabriel's decision)
Fed by questions and answers and developed over time. Uses **SQLite + sqlite-vec** (vector search), in a local file, on the NVMe.

**Layers:**
| Layer | Contents | Use |
|---|---|---|
| **Raw history** | Every question and answer | Lookup and future dataset |
| **Curated memory** | Facts and preferences extracted and summarized automatically ("wakes up at 06:30", "prefers short answers") | Injected into the context (RAG) |
| **Knowledge** | Good answers from the large models | The local model answers on its own next time, without spending API |

> **Important:** the local model does not "learn" by itself just by having a database next to it. The evolution comes from memory retrieval (RAG). **Future (phase 4 or 5):** LoRA fine-tuning of the local model with the accumulated history. That is why the raw history is kept from day one.

### 2.4 Extensibility
- **Connectors, skills, agents, subagents and automations** come in as the idea develops.
- **Base decision, right now:** every tool follows the **MCP standard** (Model Context Protocol). Each new connector becomes a plugin, without rebuilding the core.

### 2.5 Agents inside the AI (runtime)
- **Orchestrator (the persona):** talks with the user and delegates to specialists, called as tools.
- **Specialists:** agenda and routine, research, PC and home control, memory (summarizes and keeps what matters).

### 2.6 HUD (visual interface)
- Full-screen TypeScript web page on the ultrawide monitor or a responsive window.
- Official identity: an organic crown of silver waves and digital particles on black,
  as in the approved PNG; not to be replaced by a generic orb. Three.js/WebGL with a Canvas fallback.
- Real audio levels sent by the existing Python pipeline; the browser does not capture
  another microphone or play another TTS. Optional local SSE bridge, never blocking the conversation.
- Cards, clock, state, active model/origin and voice; private content hidden by default.
- v0.4.0 implementation in progress, no release; [HUD guide](docs/HUD.md) and
  [cumulative acceptance](docs/HOMOLOGACAO.md).

### 2.7 Distributed mode (future)
- **Small always-on machine** (mini PC, old laptop or Raspberry Pi 5), the "body": wake word, scheduler, memory database, automations. Draws about 10–15 W.
- **Main PC**, the local "brain": when on, it takes the conversation.
- **API as fallback:** when the PC is off or busy.
- **Rule:** the architecture is born ready for this, with separate components talking over the local network.

---

## 3. Main PC hardware

| Component | Model |
|---|---|
| GPU | Gigabyte **RX 9060 XT 16 GB** (AMD, RDNA 4) |
| CPU | Ryzen 7 **9800X3D** |
| RAM | 32 GB DDR5 6000 MHz CL36 Corsair (2 sticks) |
| PSU | MSI 750 W Gold Plus |
| Motherboard | B850 Gaming X WiFi6E |
| Storage | 1 TB NVMe SSD + 240 GB SATA SSD |

**Implications:**
- **AMD GPU:** avoid CUDA-only tools. Use **Vulkan and ROCm**. RDNA 4 support depends on the driver and program versions, so **test first** (Stage 1).
- **VRAM split (16 GB):** 12–14B LLM (~9–10 GB) + Whisper (~1–2 GB) + headroom for the system and the HUD. 20B+ models fit, but are tight and slow.
- **Storage:** models and database on the **NVMe**. The SATA is for **database backup**.

**Future upgrades (only if missed after using it):**
1. **RAM:** **replace** with 2×32 GB (64 GB) or 2×48 GB (96 GB) DDR5 6000. **Do not use 4 sticks:** on AM5 this usually drops the speed (to 5200–5600) and causes instability.
2. **Second GPU only for AI:** e.g. a used RTX 3060 12 GB. Frees the RX 9060 XT for games and solves CUDA compatibility. Before buying, check:
   - the card's power draw (the 750 W PSU must handle it);
   - the second PCIe slot (usually x4, which does not matter for AI);
   - space and airflow in the case.
3. **Extra NVMe** for the models (organization and space).

---

## 4. Costs and API

- **Claude Pro does not include the API.** They are separate products. Pro is for **developing** the project in Claude Code. The API (Console, pay per use) is for the AI **running**. Max and Team come with monthly API credits, Pro does not.
- **Estimated API cost:** low for personal use. Haiku for conversation and Sonnet/Opus only for heavy work should be a few dollars a month. Set a **spending limit** in the Console.
- **Do not use** `claude -p` with the Pro login as the "brain": it is slow (several seconds) and the plan was not made for that.
- **Energy:** a gaming PC on 24h costs something like R$ 50–80/month, against R$ 7–10/month for a mini PC (estimate).

---

## 5. Roadmap by stage (each stage = one version)

| Version | Stage | Status | Deliveries | Done criterion |
|---|---|---|---|---|
| **v0.0.0** | Foundation | ✅ | Repository, license, README, structure, `.gitignore`, `.env.example`, config for **name, persona, voice and models** | The project runs "hello world" and the config loads |
| **v0.1.0** | Voice conversation | ✅ | Activation by name (transcription), Silero VAD, whisper.cpp, Ollama (Qwen 3.5 9B), Kokoro, Piper and ElevenLabs voices with fallback, hands-free | Say the name, ask and hear the answer in < 2 s |
| **v0.2.0** | Memory | ✅ | SQLite + sqlite-vec: facts by area, total memory (every exchange), date agenda, learning pronunciation and way of speaking; own voice (dataset, checker, Piper training) | Remembers facts across sessions |
| **v0.3.0** | Model router | ✅ | Router local → ChatGPT → Claude (triage, `{pensar}`, second chance), holding phrase, game mode (with confirmation to leave), fallbacks without stitching answers, switching brain and voice by command, Obsidian notes index, emotion in the voice, forget and delete for good, recoverable half-finished answers, supervised self-improvement (daily rule-based report, decisions by the person) | A hard question goes to the API and comes back in the same voice |
| **v0.4.0** | HUD | 🔄 | Reactive waves and particles, cards, clock, full screen | The interface reacts to the voice in real time |
| **v0.5.0** | MCP tools | ⬜ | Agenda, weather, PC control, files | Performs actions by voice |
| **v0.6.0** | Routines and initiative | ⬜ | 06:30 briefing, reminders, automations, **camera** (see Idea bank) | The AI speaks first on schedule and on presence |
| **v0.7.0** | Agents and subagents | ⬜ | Specialists called by the orchestrator | Complex tasks delegated |
| **v0.8.0** | Distributed mode | ⬜ | Split "24h body" × "brain" | Works with the PC off (via API) |
| **v1.0.0** | Launch | ⬜ | Installer, complete docs, AMD/NVIDIA/CPU backends | Third parties install and use it |

### Semantic versioning (`vMAJOR.MINOR.PATCH`)

| Part | When it changes | Example |
|---|---|---|
| **MAJOR** | Stable launch or a change that breaks compatibility | `v0.8.0` → `v1.0.0` |
| **MINOR** | Each new roadmap stage | `v0.1.0` → `v0.2.0` |
| **PATCH** | Small adjustments, fixes and improvements within a stage | `v0.1.0` → `v0.1.1` → `v0.1.2` |

- Each published version gets a **Git tag** with the same name (e.g. `v0.1.0`) and an entry in `CHANGELOG.md`.
- Before `v1.0.0`, the project is still in development and any part may change.

**Future stages:** LoRA fine-tuning, smart home (Home Assistant), projector and touch table.

---

## 6. Public repository and licenses

- **Nothing personal in the repository:**
  - API keys only in `.env` (ignored by Git), with a `.env.example` template;
  - **the memory database, the history and face data never go to GitHub**;
  - `data/` folder in `.gitignore` since v0.0.
- **Name and brand:** do not use "Jarvis", nor Marvel logos or visual references, in the name, logo or promotion. It is a registered trademark. "Inspired by the assistants of fiction" is fine.
- **Customizable name:** the assistant's name comes from the config. Each user gives their own, and Gabriel's stays exclusive.
- **Code license:** all rights reserved since 06/11/2026 (MIT up to v0.3.0). Anything opened in the future goes to a separate repository, with a license chosen at that time.
- **Model and voice licenses:** check them one by one. Some forbid commercial use or redistribution (e.g. **XTTS is non-commercial**; some Piper voices have restrictions). Prefer redistributable components, or download the models separately via script.
- **Swappable backends:** Vulkan, ROCm, CUDA and CPU, to run on other machines.
- **Repository quality:** organized commits (Conventional Commits), one tag per stage, `CHANGELOG.md`, basic CI. It also works as a portfolio.
- **Original voice:** create it with voice design or pick a ready-made one. **Do not imitate a real actor's voice.**

---

## 7. Name suggestions (with acronym)

- **K.A.I.R.O.S.:** *kairós* = "the right moment" (Greek). Fits the briefing and routine.
- **Ó.R.I.O.N.:** Operador de Rotina, Inteligência e Organização Neural (Routine, Intelligence and Neural Organization Operator).
- **V.E.G.A.:** Vigilância, Execução e Gestão Autônoma (Vigilance, Execution and Autonomous Management).
- **A.U.R.A.:** Assistente Universal de Rotina e Automação (Universal Routine and Automation Assistant).

> Still to decide: the **product name** and the **name of Gabriel's personal assistant** may be different.

---

## 8. Idea bank

### 8.1 Camera identification
When someone arrives in the room, the AI identifies the person and interacts. Fits: **Stage 6**.

- **Layer 1, presence:** detect that someone came in, without identifying who. Lightweight: webcam + MediaPipe (CPU) or an **mmWave sensor** (cheap, no camera, detects even someone standing still).
- **Layer 2, recognition:** only when there is presence, compare the face with the registered ones (e.g. InsightFace) and greet with context ("Boa noite, Gabriel. Você tem prova amanhã, quer revisar?").
- **Privacy:**
  - face data **local only**;
  - unknown person → nothing personal is said;
  - voice command or button to turn the camera off;
  - registering visitors only with consent.

### 8.2 Obsidian as a second brain
*Origin: [Reference 01](docs/referencias/video-01-assistente-local.md).*

- ✅ **Done in v0.3.0:** the assistant reads the **Obsidian vault** (`.md` notes) as a knowledge base, indexed in SQLite + sqlite-vec (`nora notas`).
- The HUD draws the **notes graph** and highlights the ones used in the answer. Fits: **Stage 4**.
- Folders can be left out in the config (`[notas] ignorar`). Personal notes stay out of GitHub.

### 8.3 Switching brain and voice by command
*Origin: [Reference 01](docs/referencias/video-01-assistente-local.md).*

- ✅ **Done in v0.3.0:** "use o cérebro local", "use o ChatGPT", "use o Claude", "troque para a voz do Piper". Choosing a specific local model by name ("troque para o Gemma") does not exist yet.
- The HUD always shows the **active model and voice** and the **origin** of each answer (which tool or note was used).

### 8.4 Particle words in the HUD
*Origin: idea for the HUD (31/10/2026).*

- While Nora speaks, **each word appears formed by particles** in the center of the HUD, in sync with the voice; important words get another color (e.g. red).
- Technique: draw the word on an invisible canvas, pick points inside the letters and animate thousands of particles (Three.js) to those points; on the next word, the particles fly to the new positions.
- Use real alignment only when there is timing metadata. Without it, the word animation is a visual estimate, explicitly labeled and possible to turn off; do not promise phonetic sync.
- Fits: **Stage 4 (HUD)**, together with the waves and the cards.

### 8.5 Voice creation with ComfyUI
*Origin: Gabriel's idea (31/10/2026).*

- Use **ComfyUI** (node-based flow interface, running on the PC) as a lab to **create and train Nora's voice**, building the process visually: recordings → audio cleanup → cloning or training → test.
- ComfyUI has community nodes for voice synthesis and cloning (e.g. F5-TTS, Chatterbox, XTTS). **Check each model's license**: some are non-commercial only (XTTS, F5-TTS weights); Chatterbox is MIT.
- The created voice comes out as a file/model and enters Nora through a voice engine (`[voz] motor`), like Kokoro and Piper.
- Care: only your own voices or voices of people who authorize it; no ElevenLabs audio as training material; install ComfyUI in an environment separate from Nora, with **Python 3.12 or 3.13**; check AMD GPU (RX 9060 XT) support on Windows.
- Related: voice lab (`nora voz testar`, Kokoro voice mixing) and training your own voice with Piper.
- **Status (v0.2.0):** done: the `comfyui` engine, `nora voz gerar-dataset`, `nora voz conferir-dataset` and the Piper training notebooks (Kaggle and Colab). **Lesson:** the trained voice is never more natural than the source; Qwen3-TTS speaks Portuguese with an accent, and Piper inherited the accent. For a natural voice, the source must be real pt-BR (record a real voice, with permission, or a model that speaks Portuguese well and allows training).

*(Add new ideas here.)*

---

## 9. Development with Claude Code: suggested roles

| Role | Responsibility |
|---|---|
| **Plan** | Architecture, contracts between modules, plan for each stage |
| **Voice subagent** | Wake word, VAD, STT, TTS, barge-in, echo |
| **Brain subagent** | LLM orchestration, router, persona |
| **Memory subagent** | Database schema, RAG, automatic curation |
| **HUD subagent** | Orb, cards, animations, Electron/Tauri |
| **Integrations subagent** | MCP servers (agenda, weather, PC, home) |
| **Reviewer** | Measures latency per stage, tests, comparison with the reference |

---

## 10. Decisions (made on 30/10/2026, before v0.0.0)

1. **Operating system:** ✅ **Windows**, with GPU acceleration via Vulkan. Linux (ROCm) is plan B if performance is not enough; the code runs on both.
2. **Name:** ✅ **Nora** for the project and for the assistant. The assistant's name stays configurable.
3. **Language:** ✅ **Python core + web HUD (TypeScript)**.
4. **24h use:** ✅ **not for now**. Distributed mode stays in v0.8.0, as planned.
5. **License:** ✅ **MIT** up to v0.3.0; since 06/11/2026, **all rights reserved**, with commercialization in mind (anything opened goes to a separate repository).

---

## 11. Suggested first prompt for Claude Code

```
Read PROJETO_ASSISTENTE_IA.md in full. Let's start Stage 0 (v0.0.0).
Before writing code, use plan mode to:
1. Confirm with me the pending decisions in section 10.
2. Propose the folder structure (modular Python core, separate web HUD,
   MCP servers as plugins, data/ folder outside Git).
3. Create a CLAUDE.md summarizing the project rules (sections 2, 3 and 6).
Then implement v0.0.0 and, right after, a quick AMD GPU compatibility test
(Ollama with ROCm/Vulkan and whisper.cpp with Vulkan) to validate Stage 1.
```
