# Memory (v0.2.0)

Nora remembers you from one conversation to the next. Everything lives in a file **only on your machine**: `data/memoria.db` (the `data` folder never goes to GitHub). To change the location, use `[caminhos] dados` in `config/local.toml`.

## How it works

1. **She takes notes.** After each answer, in the background, the local model rereads the exchange and notes what is worth remembering about you: **lasting facts** (preferences, routine, close people, pets), **dates and plans** and **remarkable events**, with the date ("Ana faz aniversário em 12 de março", "Em 05/03/2026 o gato da Ana fugiu e foi encontrado perto de casa"). On the next answer `[memória] anotei: ...` shows. Near-identical facts are merged: the newer replaces the older.
   Each fact goes into an **area** (health, work, studies, family, pets...). She reuses the existing areas and **creates a new one** when a new subject comes up.
2. **She keeps everything.** Every question and answer is also kept **in full**, even when it does not become a fact. That way she remembers anything you said.
3. **She remembers.** Before answering, she searches the facts and the **passages of old conversations** most similar to the question (by meaning, not exact words) and reads them along. If you ask "onde eu achei meu cachorro?", she finds the passage where you told her that.
4. **You are in charge.** You can see, add and delete what she knows (below).

The model itself does not change: it gets smarter about you because it receives the right memory with each question. The full history stays in `data/historico/`, word for word.

## Install (once)

```powershell
ollama pull bge-m3
```

```powershell
pip install -e ".[dev,voz,kokoro,memoria]"
```

- **`bge-m3`** turns texts into meaning vectors (multilingual, MIT license, ~1.2 GB, runs on the GPU alongside Qwen).
- **`memoria`** installs `sqlite-vec` (MIT/Apache) so search is fast. Without it, search works the same, just slower when there are many thousands of facts.

Check with `nora --verificar`: the **Memória** line should say `ok`.

## Agenda: remembering by day

Meaning-based search finds "quando é minha prova?", but not "o que tenho amanhã?": the question has no word in common with "prova em 21/11". So every fact with a date also goes into an **agenda**:

- **When noting:** curation turns "amanhã", "sexta", "dia 21" and "21/11" into real dates and stores the fact in the agenda (birthdays and commemorative dates are marked as **every year**). In the conversation `[memória] anotei: ... (agenda: 21/11/2026)` shows.
- **When answering:** she always reads what is scheduled for the **next 7 days** (`agenda_dias`) and, if the question mentions a period, what is scheduled in it. Ask naturally: "o que tenho amanhã?", "tenho algo essa semana?", "e na sexta?", "e no dia 21?", "o que tem em dezembro?", "quando é meu aniversário?".
- **Old facts:** the ones that already had a date written in the text enter the agenda on their own, the first time the memory is opened.
- **In Obsidian (v0.3.1, optional):** with the Second Brain on, each memory becomes a note linked to the area, the names and the agenda month, and what you correct or forget leaves there too. See [SEGUNDO_CEREBRO.md](SEGUNDO_CEREBRO.md).
- **Date math:** "que dia vai ser daqui a 23 dias?", "e daqui a 24?", "há 2 semanas", "3 meses atrás" and "que dia da semana cai 25/12?" are calculated by the code, and the model only speaks the result. The local model got these calculations wrong, even knowing today's date. It also works with memory turned off.

## Learning from conversation: pronunciation and way of speaking

You teach by talking, and she keeps it:

- **Pronunciation:** "Nora, você fala 'houje', o certo é 'ôje'." Curation notes the word and how to say it, and in the conversation `[memória] aprendi a pronúncia: hoje → ôje` shows. It applies immediately, for any voice (ElevenLabs, Piper, Kokoro, ComfyUI) and also for `gerar-dataset`, so the next trained voice is born with the right pronunciation. Tip: to teach pronunciation, **type** the correction; spoken, Whisper writes "hoje" both times.
- **Way of speaking:** "Não precisa repetir minha pergunta", "Seja mais direta", "Me chama pelo nome." She keeps it as a preference (`[memória] vou lembrar de: ...`) and follows it in every conversation: preferences go along with every answer, not only when the subject is similar.

Requests only for that answer ("resume isso") do not become a preference.

## Deleting and correcting in conversation

- **Forget:** "apaga isso", "esquece que eu falei da viagem". Nora removes the fact from memory and the agenda and **stops using the subject**: passages of old conversations about it no longer come back in answers, and `nora memoria importar` does not bring the fact back. `[memória] esqueci: ...` shows.
- **Correct:** "não é cálculo 1, a prova é de outra matéria". The wrong fact goes out and the right one comes in.

Forgetting **does not delete the conversation record** in `data/historico`: the message says so and shows the command to delete it for good. If you tell the same thing again in a new conversation, she remembers it again.

She forgets the noted fact most similar to what you asked for. Check with `nora memoria listar`; if something is left, `nora memoria esquecer 12` deletes it by number.

## Deleting for good

**In conversation (speaking or typing):**

1. "Nora, apaga de vez a prova de cálculo" (or "apaga tudo sobre a viagem", "apaga ... para sempre").
2. She says how much would go ("Isso apagaria 1 fato e 2 trechos de conversa sobre a prova de cálculo... Confirma?") and shows the list on screen, in `[memória] apagaria: ...`. **Nothing is deleted yet.**
3. "Sim, pode apagar" deletes it. "Não" cancels. If you talk about something else, the request expires.

The request itself also leaves the history, because it mentions the subject. Without "de vez", "apaga isso" and "esquece que eu disse X" only make Nora stop using the subject (above).

**From the terminal:**

```bash
nora memoria apagar "prova de cálculo"
```

Shows what would go (facts and stored conversations about the subject) and **deletes nothing**. To delete:

```bash
nora memoria apagar "prova de cálculo" --confirmar
```

It leaves memory (facts, agenda, conversation passages and the search indexes) and the history in `data/historico`: only the utterances about the subject become `[apagado a pedido]`, the rest of the conversation stays. Obsidian notes are not touched; if the subject is in a note, edit the note.

## Half-finished answers

When an answer does not finish, Nora keeps the question and the part that came out, in a separate list (never as a fact). This happens when:
- the brain dropped in the middle;
- no brain answered;
- you interrupted with Ctrl+C;
- the program closed in the middle of the answer.

- Ctrl+C in the middle of an answer stores the pending item immediately, in the same conversation.
- **When leaving game mode** (with "sim"), if some question was left unanswered there, she warns and offers to resume; nothing is answered on its own.
- **When opening the conversation,** she warns: `[memória] 1 resposta(s) ficaram pela metade...`.
- **"Termina a resposta que ficou pela metade"** (or "continua aquela resposta") makes her answer the last one again, **in full and labeled** ("Retomando a pergunta ..."). If it works, the pending item closes and the answer follows the normal memory path. After 3 unsuccessful attempts, she gives up on that one.
- `nora pendencias` lists them all; `nora pendencias --cancelar 4` removes one from the list.
- Forgetting or deleting a subject for good also removes the pending items about it.
- The [self-improvement](AUTO_MELHORIA.md) daily report lists the ones still open.

An error only in the voice (the text answer came out complete) does not become a pending item.

## See and edit

| Command | What it does |
|---|---|
| `nora memoria listar` | The 20 most recent facts, with each one's number and the total. `--pagina 2` for earlier ones, `--contendo cachorro` to filter, `--todos` to see everything |
| `nora memoria areas` | The memory areas (health, work, studies...) and how many facts each has |
| `nora memoria listar --area saúde` | Only one area's facts |
| `nora memoria buscar prova de cálculo` | The facts most similar to the text, with the similarity score (0 to 1) |
| `nora memoria lembrar Ana prefere chá` | Stores a fact by hand |
| `nora memoria esquecer 12` | Deletes fact no. 12 |
| `nora pendencias` | The answers left halfway (`--cancelar 4` removes one) |
| `nora memoria apagar "assunto"` | Shows what would go; with `--confirmar`, deletes it for good from memory and history |
| `nora memoria agenda` | Appointments and dates for the next 30 days (`--dias 90` for more, `--passados 7` to also see the past week) |
| `nora memoria marcar 21/11/2026 prova de cálculo` | Adds an appointment to the agenda by hand (and stores it as a fact). `--anual` for what repeats every year |
| `nora memoria pronuncias` | The pronunciations she learned. `nora memoria pronuncias hoje ôje` teaches one by hand; `--esquecer hoje` deletes it |
| `nora memoria preferencias` | What you asked about her way of speaking. `nora memoria preferencias "Seja mais direta."` stores one by hand; `--esquecer 2` deletes it |
| `nora memoria desmarcar 3` | Removes event no. 3 from the agenda (the fact stays in memory) |
| `nora memoria importar` | Reads the old conversations in `data/historico/` and extracts facts from them (may take a while; you can run it again, it resumes where it stopped) |

With `--medir`, each answer shows how many facts she used (`lembrou N fatos`).

## Settings (`config/local.toml`)

```toml
[memoria]
ativa = true                 # false turns everything off
curadoria = true             # false: she remembers, but does not note new facts on her own
fatos_por_pergunta = 5       # how many facts she reads before answering
similaridade_minima = 0.45   # raise it if she brings unrelated facts; lower it if she forgets things
modelo_embeddings = "bge-m3"
agenda_dias = 7              # how many days ahead of the agenda she reads before answering (0 = none)
```

## Limits of this version

- Curation uses the same model as the conversation (Qwen 9B): sometimes it notes something useless or misses a fact. Use `listar` and `esquecer` to clean up.
- "Esquece isso" works in conversation; "o que você sabe sobre mim?" does not list the memory yet: use `nora memoria listar`.
- Forgetting finds the subject by meaning: a conversation passage very different from the request's words may slip through. `nora memoria apagar` shows beforehand what will go.
- Within the same conversation, what was already said stays in the context until it ends (or until `/limpar`).
- Memory stores facts, not yet the **knowledge** layer (good API answers reused): that is for a later stage.
