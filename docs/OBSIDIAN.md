# Using the repository in Obsidian

The whole repository works as an Obsidian **vault**: documentation, mind map and the notes for each stage live in the same `.md` files that go to GitHub.

## Setup (once)

1. Clone the repository on your PC.
2. In Obsidian: **Open folder as vault** → choose the repository folder.
3. Install the **Git** community plugin (by Vinzent03) to commit, pull and push without leaving Obsidian.
   - Suggestion: turn on *auto pull* when opening the vault, to receive what is done in Claude Code.

## What to open

| File | What it is | Where it shows |
|---|---|---|
| `docs/MAPA_MENTAL.canvas` | Visual, editable mind map (Canvas) | Only in Obsidian |
| `docs/MAPA_MENTAL.md` | Mind map, roadmap and flow in Mermaid | Obsidian **and** GitHub |
| `PROJETO_ASSISTENTE_IA.md` | Full project document | Obsidian and GitHub |

## Conventions

- **Links:** use standard Markdown links (`[texto](caminho.md)`) instead of `[[wikilinks]]`, so they also work on GitHub.
- **Each completed stage:** update the status in `MAPA_MENTAL.md` and in `MAPA_MENTAL.canvas` (⬜ → 🔄 → ✅).
- **Personal notes** (that must not go to GitHub): put them in `data/` or in a folder ignored by Git.

## Nora reading your notes (v0.3.0)

Nora can read the notes in **your** Obsidian vault (your personal one, it does not need to be the project's) and use what you wrote to answer: "o que eu anotei sobre a prova de cálculo?", "qual era a receita do bolo?". She **only reads**: she never creates, changes or deletes a note.

### Turn it on (once)

1. In `config/local.toml`, put the vault path. Use forward slashes `/` (or single quotes), because the Windows backslash means something else in TOML:

   ```toml
   [notas]
   pasta = "C:/Users/voce/Documents/Obsidian"
   # folders she must not read (hidden ones, like .obsidian and .trash, are already left out)
   ignorar = ["Diário", "Privado"]
   ```

2. Read the notes for the first time (it may take a few minutes on a large vault; it uses Ollama's `bge-m3`, the same as memory):

   ```bash
   nora notas ler
   ```

3. Check: `nora --verificar` shows the `Notas (Obsidian)` line with how many notes are in the index.

After that, every time you open a conversation, she reads in the background only the new or changed notes (and forgets the deleted ones), without delaying the start. To turn this off: `atualizar_ao_abrir = false`.

### How she uses them

- Each note is split into passages (by heading and paragraphs). Before answering, she searches the passages most similar to the question (`trechos_por_pergunta`, default 3, above `similaridade_minima`, default 0.5) and reads them along, as she does with memory.
- When she uses a note, she says which one it came from ("na sua nota Cálculo, a prova é dia 21").
- With `--medir`, each answer shows how many notes she read.
- `[[...]]` links, properties (frontmatter), images and `%%...%%` comments are cleaned up first.

| Command | What it does |
|---|---|
| `nora notas ler` | Reads the new or changed notes now |
| `nora notas buscar prova de cálculo` | Shows the passages she would find for that text |
| `nora notas status` | How many notes and passages are in the index |

### Privacy

- The index lives in `data/notas.db`, only on your PC (outside Git). You can delete the file and run `nora notas ler` again whenever you want.
- The passages used in an answer go along with the question to whoever answers. If the question goes to ChatGPT or Claude, those passages go to the cloud too. Put in `ignorar` the folders that must never leave the PC, or use "use o cérebro local".
