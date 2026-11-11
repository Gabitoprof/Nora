# Reference 01: 100% local assistant (demo video)

> A ~25 min video (in English) showing a fiction-inspired voice assistant running fully locally: brain through Ollama and a locally cloned voice.
> Studied on 30/10/2026 from the video and its transcript. Only the **ideas** are kept here; the video's name, brand and voice are not used in the project (see section 6 of [`PROJETO_ASSISTENTE_IA.md`](../../PROJETO_ASSISTENTE_IA.md)).

---

## 1. What the video shows

| Time | What happens |
|---|---|
| 0:00 | Voice command "switch to the local brain" → the assistant confirms which model took over, with humor. |
| 1:52 | **Interface:** a web page on `localhost`, with a **3D graph of all the files and folders** the assistant can access (the "second brain"), an orb with status and connected tools. |
| 2:44 | **Brain switching by voice:** Qwen 3.5 9B ↔ Gemma 4 12B ↔ a cloud model. The active model shows on screen. |
| 4:35 | **Voice switching by voice:** cloud voice (ElevenLabs) ↔ local cloned voice (VoiceStudio) ↔ other cloned voices. |
| 9:42 | **Test 1, second brain:** "pull my brand voice" → opens the notes linked to that topic and highlights the nodes in the graph. |
| 10:47 | **Test 2, tools:** "what do I have on my calendar tomorrow?" → holding phrase ("let me see if I have the tools for that"), queries Google Calendar and answers with a humorous comment. The screen shows **which tool was used**. |
| 13:19 | **Test 3, long task:** analyzes a website by opening a clean browser, scrolling the page and building a technical report. Says how long it will take and narrates progress. |
| 16:50 | Other functions mentioned: calls, scheduling, invoices. Access **controlled by permission** ("if you don't give it access, it doesn't have it"). |
| 17:43 | **Cloud × local** comparison and installation (Ollama + VoiceStudio). |

---

## 2. Interface details (screenshots from the video)

- **Background:** a graph of nodes colored by category (routes, wiki, concepts, skills, tools, notes, files), with physics controls (repulsion, link weight).
- **Left sidebar:** second-brain categories with item counts; when a topic is requested, it shows the list of related notes.
- **Orb** in the corner: an animated ring with status (`SPEAKING`), an **active model badge** (`QWEN3.5:9B`, `GEMMA4:12B`) and visual modes (ring, core, face).
- **Panel of toggleable modes:** vision (camera), hold, focus, reflex.
- **Footer:** the answer text with its **source** ("via google calendar · gcal_events"), a text field and tool icons.
- **Activity indicators:** "searching tools", "tool executed via …", and a checklist of steps during long tasks.

---

## 3. Cloud × local comparison (from the video's material)

| Aspect | Cloud | Local |
|---|---|---|
| Listening | Browser speech recognition (audio goes to Google) | Whisper on the machine, fast enough |
| Thinking | Large API model, fast and very capable | Ollama model; slower on a laptop, fast on a strong machine |
| Speaking | ElevenLabs, paid monthly | Local cloned voice; a bit slower |
| Privacy | Audio and text go through third parties | Nothing leaves the machine |
| Quality | Better reasoning and tool use | Good, not brilliant; depends on model size |
| Cost | Subscriptions and API usage | Only electricity |

---

## 4. What we learned (and how it enters the project)

| # | Idea from the video | How to apply it in our project | Stage |
|---|---|---|---|
| 1 | **Switching brains by voice** ("use o cérebro local", "troque para o Gemma") | A voice command that forces the router to a specific model; a list of installed models in the config. The automatic router still exists. | v0.3.0 |
| 2 | **Switching voices by voice** | Several voices in the config (local and cloud), switched by command. | v0.3.0 |
| 3 | **Badge of the active model and voice** | The HUD always shows which brain and which voice are in use. | v0.4.0 |
| 4 | **Second-brain graph** | Use the **Obsidian vault** as the second brain: the assistant indexes the `.md` notes (vector search) and the HUD draws the graph, highlighting the notes used in the answer. | v0.2.0 (index) and v0.4.0 (graph) |
| 5 | **Holding phrase** while using tools | Already planned for the API; extend it to **any** slow tool. | v0.3.0 and v0.5.0 |
| 6 | **Showing the source** of the answer ("via Google Agenda") | Every answer that used a tool or note carries the source on the HUD card. | v0.4.0 and v0.5.0 |
| 7 | **Narrating long tasks** (time estimate and checklist of steps) | Agent tasks publish progress to the HUD and the voice gives short updates. | v0.7.0 |
| 8 | **Access by permission** | Each MCP tool declares what it can access; the user grants them one by one. | v0.5.0 |
| 9 | **Adjustable personality with humor** | Humor and formality levels as persona parameters in the config. | v0.0.0 (config) |
| 10 | **Choosing the model by hardware** | On our 16 GB GPU, **Qwen 3.5 9B (~7.6 GB)** is a good default candidate, leaving room for Whisper; also test 12–14B models. | v0.1.0 |
| 11 | **Testing tool use on the local model** | Small models make more mistakes when calling tools. The v0.1.0 compatibility test should also measure **tool call quality**, not just speed. | v0.1.0 |
| 12 | **Agent that uses a browser** | A specialist that opens an isolated browser to research or analyze sites. | v0.7.0 |

---

## 5. Cautions

- **Voice:** the video clones the voice of a movie character. **We will not do that:** the assistant's voice will be original (voice design) or a ready-made voice with an open license.
- **VoiceStudio license:** the repository screenshot shows **AGPL-3.0**. If we use it, it must run as a **separate program** (installed separately, called over the local network), without copying the code into our repository. Check before adopting.
- **Performance:** the video runs on a very strong Apple machine. On ours (AMD RX 9060 XT), the real latency only comes from the v0.1.0 test.
- **Name and visuals:** the graph and the orb are generic ideas; do not copy the logo, the exact colors or the character's name.
