# Nora's Second Brain (v0.3.1)

The memories Nora has already consolidated become notes in your Obsidian, linked by area, by names that appear in more than one memory and by the agenda months. You browse them through the Obsidian graph or through the **memory map**, a page that shows the network as linked neurons.

**Speech comes first.** None of this happens while Nora answers or speaks: the notes are written afterwards, when she is free. See [Response time](#response-time).

## Turn it on (once)

The Second Brain writes into your vault, so it comes **off**. In `config/local.toml`:

```toml
[notas]
pasta = "C:/Users/voce/Documents/Obsidian"   # your vault

[segundo_cerebro]
ativo = true
# pasta = "Nora Brain"                 # inside the vault (default) or an absolute path
# areas_privadas = ["saúde", "finanças"]   # never become notes (default)
```

Then:

```bash
nora cerebro sincronizar
```

And, in Obsidian, open the `Nora Brain` folder or the graph (Ctrl+G).

## What goes into the vault

```text
Nora Brain/
  Nora Brain.md          index: areas, agenda months and preferences
  Áreas/Estudos.md       one note per area, with its memories
  Memórias/...md         one note per consolidated memory
  Nomes/...md            names (people, places, acronyms) that appear in 2 memories or more
  Agenda/2026-11.md      memories with a date, by month
  Preferências.md        how you asked her to speak
```

Example (made-up data) of a memory note (the note content Nora writes is in Portuguese):

```markdown
---
nora_id: "mem-000042"
nora_gerenciado: true
tipo: "memoria"
camada: "episodica"
area: "estudos"
emocao: "curiosa"
emocao_fonte: "tom da resposta da Nora"
data: "2026-11-21"
origem: "conversa de 2026-11-05"
criado_em: "2026-11-05T10:12:00"
atualizado_em: "2026-11-05T10:12:00"
tags:
  - "nora"
  - "nora/area/estudos"
  - "nora/tipo/memoria"
  - "nora/camada/episodica"
  - "nora/emocao/curiosa"
---

# Lia tem prova de Cálculo na Unifictícia em 21-11-2026

Lia tem prova de Cálculo na Unifictícia em 21/11/2026

## Ligações

- Área: [[Nora Brain/Áreas/Estudos|Estudos]]
- Menciona: [[Nora Brain/Nomes/Unifictícia|Unifictícia]] (nome que aparece em outras memórias)
- Agenda: [[Nora Brain/Agenda/2026-11|novembro de 2026]] (21/11/2026)
```

**What does not go:**
- the transcription of the conversations (only the memories curation has already consolidated);
- the areas in `areas_privadas`;
- pronunciations, half-finished answers and the self-improvement events;
- made-up emotion. The `emocao` field is the **tone Nora used** in the conversation where the fact came up (the `{curiosa}`, `{calma}`... tags of the answer), not a feeling of yours. Without a tone tag, the field does not appear. To remove it: `emocoes = false`.

## Links (why two things connect)

| Link | From → to | Basis |
|---|---|---|
| `pertence_a` | memory → area | the area curation noted |
| `menciona` | memory → name | the name appears in the memory's text and in at least one more |
| `aconteceu_em` | memory → month | the date in the agenda |

No link is made up to make the drawing fuller: a name that appears in only one memory does not become a node, and your name and Nora's (from the config) do not count, because they are in almost everything.

## Sync

- **Incremental:** compares the memory with what was already exported and writes only what changed. Repeating does not duplicate anything.
- **Correction:** a fact with new text replaces the note (the title follows) and the old one goes away.
- **Forget and delete for good:** the memory leaves the vault and the map on the next round, without coming back through reimport. Backups outside Nora (Obsidian Sync, the system trash, the file recovery plugin, OneDrive...) she does not control: delete there too, if needed.
- **Your notes are untouchable:** Nora only touches the files she herself created in her folder. If a note of yours with the same name already exists, or if you edited one of her notes, she does not overwrite or delete it: it becomes a conflict in `nora cerebro status`. To give the note back to her, delete your version.
- **No cycle:** the notes reader (`[notas]`) ignores the Second Brain folder, so memories do not come back as if they were your notes.
- **Power loss:** each note is written to a temporary file and swapped in at once; a drop in the middle leaves the previous version whole. The next round resumes where it stopped, without duplicating.
- **Vault unavailable** (disk disconnected, folder without permission): Nora keeps talking; the error shows in `nora cerebro status` (only the error type, no content) and the next round tries again.

## Memory map

Ask by speaking ("Nora, mostre seu segundo cérebro", "abra o mapa da memória", "visualize suas conexões") or from the terminal (`nora cerebro mapa --abrir`). The map is a single page, offline and without external libraries, in `data/segundo_cerebro/mapa.html`, built during sync. Opening it recalculates nothing.

| On the map | Means |
|---|---|
| Node color | the memory's area |
| Colored halo | the conversation's tone (the same colors as the HUD) |
| Size | number of links (capped) |
| White pulse | memory updated in the last 7 days |
| Links appearing on opening | animation of the real links; no memory is created |

Click a node to see its card: area, layer, origin, date and **why it links** to each neighbor, with the link to open the note in Obsidian. The link uses the file's full path (`obsidian://open?path=...`), so it works with any vault name; it only needs the vault folder to have been opened in Obsidian at some point (Open folder as vault). No plugin needed. Search, filters by area, type and tone, zoom and drag. With more than 900 nodes, the map opens with only areas, names and months, and the memories appear on click or in "Ver tudo" (see all).

**Privacy:** the memory text opens hidden (blurred), and appears with the "Mostrar textos" (show texts) button. To open it already visible: `mostrar_texto_no_mapa = true`.

### Colors

Areas (node color):

| Area | Color |
|---|---|
| Trabalho (work) | `#2F6BFF` blue |
| Pessoal (personal) | `#F09BD8` pink/lilac |
| Saúde (health) | `#4ADE80` green |
| Família (family) | `#FBBF24` warm yellow |
| Estudos (studies) | `#22D3EE` cyan |
| Projetos (projects) | `#FF8A3D` orange |
| Rotina (routine) | `#CBD5E1` silver |
| Finanças (finances) | `#059669` emerald green |
| Espiritualidade (spirituality) | `#A855F7` violet |
| Tecnologia (technology) | `#7C8CFF` electric blue |
| Other areas | a fixed color from the reserve, always the same for the same area |

Tones (halo): **the same colors as the HUD**, read from the same file, `src/nora/paleta.json` (in Python, `nora.paleta`), with the same names as the tags in `emocao.py`. There is no second color system; to change a color, change only that file:

| Tone | Color |
|---|---|
| alegre, empolgada | `#F0C66A` |
| carinhosa | `#E3A4BD` |
| calma | `#66D4CB` turquoise |
| séria | `#80A8F6` |
| triste | `#AA9ACF` lavender |
| curiosa | `#DF876A` terracotta |
| neutra | `#C9C9C9` |

## Contract for the memory HUD

The Second Brain does not depend on the main HUD (v0.4.0) and does not touch it. What it produces follows a versioned contract, so a memory HUD can plug in later: [`src/nora/segundo_cerebro_contrato.json`](../src/nora/segundo_cerebro_contrato.json) (version 1). It defines:
- the `data/segundo_cerebro/grafo.json` file, with `versao`, `nos`, `ligacoes` and `legenda`;
- the node and link types;
- the `texto` field, marked as private;
- the emotions, with the same names as the HUD's `emocao` event;
- the `segundo_cerebro_atualizado` event, reserved for when the memory HUD exists (in v0.3.1 only the file is written).

## Response time

The critical path is this:

```text
Speech → VAD/STT → memory search (the same as before) → LLM → TTS → playback
                                                              │
               curation (already in the background) ◄─────────┘ (after the answer)
                        │
                        └─► avisar(): only raises a signal (Event.set), never waits
                                  │
                 "nora-segundo-cerebro" thread (another thread)
                   waits for conversa.ocupada and conversa.falando to be off
                   reads the memory over a read-only connection
                   writes the notes that changed (stops midway if Nora speaks again)
                   writes grafo.json and mapa.html
                                  │
                   map in the browser (another process, on request)
```

Guarantees, with automated tests in `tests/test_segundo_cerebro.py`:
- **No writing on the speech path:** the conversation only calls `avisar()`. The test sets a 3 s sync and checks that the answer comes out in under 1 s, and that the sync runs only on the `nora-segundo-cerebro` thread.
- **Waits for the voice:** `conversa.falando` stays on from the start of the answer until the last audio plays. The thread does not start meanwhile, and stops between one file and the next if Nora speaks again.
- **No model:** no call to a model, embeddings or the cloud. It uses what curation already produced, so it does not wake the local brain in game mode.
- **Isolated failure:** an error in the vault or the thread does not reach the conversation.
- **Separate map:** the map runs in the browser, in another process. Opening, closing or freezing the map does not touch the audio.
- **Continuous listening:** the thread does not read the keyboard or the microphone.

### Measurement

`python scripts/medir_segundo_cerebro.py` runs the real voice path (`responder_falando`, `Locutor`, playback), with a fake brain and voice of fixed timing, in three scenarios: off, on with a large memory (real use) and stress (the sync rewriting everything nonstop, ignoring whether Nora speaks, an artificial worst case). Budget defined before measuring: **audio-start p95 up to 5% above the off scenario**, with no relevant increase in the pauses between chunks.

Result on 05/11/2026 (cloud Linux x86_64, Python 3.13, 60 answers per scenario, memory with 2000 facts; fake brain with the first chunk at 150 ms and a fake voice of 120 ms + 2 ms per character):

| Scenario | Audio start p50 | p95 | p99 | Std. dev. | Δ p95 | Largest pause between chunks (p95) | Syncs |
|---|---|---|---|---|---|---|---|
| Off | 494.2 ms | 495.0 ms | 496.5 ms | 0.5 ms | reference | 0.1 ms | 0 |
| On (real use) | 493.9 ms | 494.7 ms | 497.8 ms | 0.6 ms | −0.1% | 0.1 ms | 61 |
| Stress (artificial worst case) | 493.7 ms | 494.6 ms | 514.7 ms | 3.1 ms | −0.1% | 0.1 ms | 220 |

**Reading:**
- **On:** within budget. The Second Brain ran 61 times, once per answer and always after it, without changing the start of speech or the pauses.
- **Stress:** the sync rewrote 2000 notes nonstop, including while Nora spoke. Even so the p95 stayed the same; only the p99 rose by about 18 ms, CPU contention at the worst moments. In real use this does not happen, because the thread waits for the voice.
- **Measurement limit:** the fake brain and voice only wait; they use no CPU. Ollama, Kokoro and Piper run in separate processes and ElevenLabs in the cloud, so the contention that matters is inside Nora's process, which is what this measurement covers.

**This is not the acceptance.** It still needs measuring on Windows with the real model and voice (checklist below).

## Acceptance checklist (Windows + Obsidian)

1. `git switch feat/v0.3.1-second-brain` and `git pull`.
2. Without the Second Brain (`ativo = false`): 10 similar questions in `nora falar --medir`; note "começou a falar em".
3. With `ativo = true`: the same 10 questions. The p95 of "começou a falar em" must not exceed step 2 by more than 5% (cloud variations count: repeat if the network fluctuates).
4. Say something new ("eu estudo com a Ana às quartas"), wait for the answer to finish and see the note appear in `Nora Brain/Memórias` within ~1 minute, without a pause in speech.
5. Correct it ("não é às quartas, é às sextas"): the note changes, the old one disappears.
6. "Esquece que eu estudo com a Ana": the note disappears from the vault and the map.
7. Edit one of Nora's notes in Obsidian and change the fact in conversation: your edit stays, and `nora cerebro status` shows the conflict.
8. Close Obsidian (or rename the vault) and talk: Nora answers normally; `nora cerebro status` shows the error; bring the vault back and the next round completes.
9. "Nora, mostre seu segundo cérebro": the map opens in the browser; keep talking with it open and animating, and compare "começou a falar em".
10. `nora ouvir` with several utterances in a row: no utterance lost.
11. Game mode: Ollama does not load the model because of the Second Brain (watch VRAM usage).

## The ten improvements (A–J): status and decision

| ID | Improvement | Before | In this version | Next step |
|---|---|---|---|---|
| A | Layered memory | Partial: facts, history (episodes), agenda, preferences and session context were already separate, without a layer label | `camada` in the notes: `semantica` (fact), `episodica` (fact with a date), `procedural` (preferences). No new table | v0.4.x: layer stored in the database, curation classifying it; "affective" separate from preference |
| B | Explicit graph | Absent | Nodes (memory, area, name, month, preferences) and links with type and basis; names deduplicated without accents and case; a single name does not become a node | v0.4.x: resolving homonyms (two "Ana"s), relations declared by curation (`participa_de`, `depende_de`) |
| C | Strength and relevance | Partial: update date and similarity in search | Node size = number of links; pulse = updated within 7 days. No made-up score | v0.5.x: "isso é importante" in conversation, frequency of use in answers (the history already stores which facts were used) |
| D | Forgetting and retention | Existed: forget, delete for good, reimport block | The vault and the map follow the memory: what leaves it leaves the notes. Nothing is forgotten by age | v0.5.x: archive (out of focus, still queryable) and expiry of facts with a past date |
| E | Batch consolidation | Partial: background curation per answer | Batch sync, incremental, idempotent and resumable, on its own thread, with no new model call | v0.4.x: group several mentions of the same subject into a topic note (without a paid LLM) |
| F | Explainable memory | Partial: fact origin and IDs of the memories used in the history | Each link has its basis ("área anotada pela curadoria", 'o texto cita "X"', "data na agenda"); the map card shows origin, dates and the why of each link | v0.4.x: "de onde veio isso?" answered by Nora herself |
| G | Active context | Partial: the session conversation is already the short context, and the session does not become memory on its own | Nothing new on the speech path (decision from document 2) | v0.4.x: nodes used in the answer highlighted on the map, through a light event |
| H | Hybrid retrieval | Partial: vector + agenda by date + date math (v0.3.1) | Not changed (the document asks to measure first) | v0.5.x: FTS5 for proper names, with a precision and latency benchmark against the current search |
| I | Affective memory | Partial: emotion tags in the voice and tone preferences | Conversation tone stored on the fact (`fatos.emocao`, taken from the answer's tags, in the background), optional, with source and HUD colors | v0.4.x: correct or remove the tone in conversation |
| J | Cognitive visualization | Absent | Map (functional MVP): colors by area, halo by tone, size by links, pulse, animated reveal, search, filters, focus, card with the why, link to Obsidian and large-graph mode | v0.4.x: integrate into the HUD through the contract; 3D and cluster grouping |

## Risks and limits

- **Proper names by rule:** a capitalized word in the middle of a sentence becomes a name. Homonyms ("Ana" from work and "Ana" from the family) become the same node, and a name that starts the sentence only counts if it is an acronym.
- **Titles change with the text:** a hand-written link to one of Nora's notes breaks if she corrects the fact. Use the links in the area notes, which she updates.
- **Python concurrency:** the thread runs in the same process as the conversation. It waits for the voice and stops midway if Nora speaks again, but a round already in progress still competes for CPU for a few milliseconds. The measurement's stress scenario shows the worst case.
- **Graph plugins** that show tags as nodes (`#nora` is in every note) or create guessed links ("inferred links") tangle the drawing: turn those options off to see only Nora's links.
- **Obsidian's native graph** colors by search groups (tag, folder), not by halo or size by relevance. To see the area colors there: Graph → Groups → `tag:#nora/area/estudos` with the color from the table. Nora's map shows the rest.
