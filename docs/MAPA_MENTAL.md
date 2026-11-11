# Project mind map

> Project overview in diagrams. GitHub draws the `mermaid` blocks automatically.
> **Rule:** every finished stage updates this file, changing the status in the roadmap and adding new nodes to the map.
> Editable visual version in Obsidian: [`MAPA_MENTAL.canvas`](MAPA_MENTAL.canvas) (see [`OBSIDIAN.md`](OBSIDIAN.md)).
> Detailed source: [`PROJETO_ASSISTENTE_IA.md`](../PROJETO_ASSISTENTE_IA.md).
> References studied: [`referencias/`](referencias/video-01-assistente-local.md).

**Roadmap legend:** ✅ done · 🔄 in progress · ⬜ pending

**Versions:** `vMAJOR.MINOR.PATCH`. Each stage bumps the middle number (`v0.1.0` → `v0.2.0`), and fixes within a stage bump the last one (`v0.1.0` → `v0.1.1`). Details in section 5 of [`PROJETO_ASSISTENTE_IA.md`](../PROJETO_ASSISTENTE_IA.md).

---

## 1. Overview

```mermaid
mindmap
  root((Nora))
    Real-time voice
      Wake word
        Name said at the start of the sentence
        Typing also works
      VAD
        Silero VAD
      STT
        whisper.cpp with Vulkan
      TTS
        Kokoro local
        Piper with a trained voice
        ElevenLabs
        ComfyUI
        Fallback voice
      Emotion in the voice
        Chosen by context
        Audio tags on ElevenLabs v3
        Learns from reactions
      Barge-in
        Echo cancellation
      Latency
        Target under 1 s
        MVP under 2 s
    Hybrid brain
      Local
        Ollama
        Qwen 3.5 9B
        keep_alive frees VRAM
      Router
        Triage and second chance
        Local model thinking
        Voice commands
      API
        ChatGPT first
        Claude as fallback
        Holding phrase
      Game mode
        Conversation goes to the API
        Leave only with confirmation
        Never returns to local on its own
    Memory
      SQLite and sqlite-vec
      Raw history
        Total memory
      Curated memory
        Areas by subject
        Date agenda
        Learns pronunciation and way of speaking
      Forget and delete for good
      Half-finished answers
        Resume later
      Obsidian notes
        Read-only index
      Knowledge
      Future LoRA
    Self-improvement
      Observer without text
      Rule-based daily report
      Approve reject postpone
      Future web research
    Extensions
      MCP standard
      Orchestrator persona
      Specialists
        Agenda and routine
        Research
        PC and home control
        Memory
    HUD
      Electron or Tauri
      Three.js orb
      Cards and clock
    Distributed mode
      24h body mini PC
      Brain main PC
      API as fallback
    Hardware
      RX 9060 XT 16 GB
        Vulkan and ROCm
        Avoid CUDA only
      Ryzen 7 9800X3D
      32 GB DDR5
      NVMe for models and database
    Open source
      Data out of Git
      env.example
      No Marvel brand
      Configurable name
      MIT or Apache-2.0
      Check model and voice licenses
    Idea bank
      Camera
        Presence
        Local face recognition
        Privacy
      Obsidian as a second brain
        Graph in the HUD
      Particle words in the HUD
      Voice creation with ComfyUI
```

---

## 2. Roadmap by stage

```mermaid
flowchart LR
  v00["v0.0.0 Foundation"]:::done --> v01["v0.1.0 Voice conversation"]:::done
  v01 --> v02["v0.2.0 Memory"]:::done
  v02 --> v03["v0.3.0 Model router"]:::done
  v03 --> v04["v0.4.0 HUD"]:::pend
  v04 --> v05["v0.5.0 MCP tools"]:::pend
  v05 --> v06["v0.6.0 Routines and initiative"]:::pend
  v06 --> v07["v0.7.0 Agents"]:::pend
  v07 --> v08["v0.8.0 Distributed mode"]:::pend
  v08 --> v10["v1.0.0 Launch"]:::pend

  classDef done fill:#2e7d32,stroke:#1b5e20,color:#fff
  classDef doing fill:#f9a825,stroke:#f57f17,color:#000
  classDef pend fill:#eceff1,stroke:#90a4ae,color:#37474f
```

| Version | Stage | Status | Done criterion |
|---|---|---|---|
| v0.0.0 | Foundation | ✅ | The project runs "hello world" and the config loads |
| v0.1.0 | Voice conversation | ✅ | Say the name, ask and hear the answer in under 2 s |
| v0.2.0 | Memory | ✅ | Remembers facts across sessions |
| v0.3.0 | Model router | ✅ | A hard question goes to the API and comes back in the same voice |
| v0.4.0 | HUD | ⬜ | Interface reacts to the voice in real time |
| v0.5.0 | MCP tools | ⬜ | Performs actions by voice |
| v0.6.0 | Routines and initiative | ⬜ | The AI speaks first on schedule and on presence |
| v0.7.0 | Agents and subagents | ⬜ | Complex tasks delegated |
| v0.8.0 | Distributed mode | ⬜ | Works with the PC off, via the API |
| v1.0.0 | Launch | ⬜ | Third parties install and use it |

---

## 3. Flow of a conversation

```mermaid
flowchart LR
  mic(["Microphone"]) --> ww["Wake word"] --> vad["VAD"] --> stt["STT whisper.cpp"]
  stt --> orq{"Orchestrator"}
  orq -->|conversation| local["Local LLM Ollama"]
  orq -->|heavy| api["API ChatGPT, Claude as fallback"]
  orq -->|action| mcp["MCP tools"]
  mem[("SQLite memory")] <--> orq
  local --> tts["TTS ElevenLabs, Kokoro, Piper"]
  api --> tts
  mcp --> orq
  tts --> spk(["Speaker"])
  tts --> hud["HUD orb and cards"]
```

---

## 4. Decisions made (30/10/2026)

```mermaid
mindmap
  root((v0.0.0 decisions))
    Operating system
      Windows with Vulkan
      Linux as plan B
    Name
      Nora for project and assistant
    Language
      Python core
      TypeScript HUD
    24h use
      Only in v0.8.0
    License
      All rights reserved
```
