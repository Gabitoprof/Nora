# Nora's self-improvement (supervised)

Nora watches how the conversations went and, once a day, proposes improvements based on what repeated. **She only proposes:** nothing changes in the code, nothing is installed and nothing is published without you deciding.

## The cycle

```text
during the day: conversation → observer (only times, failures and categories)
at the set time: groups → diagnoses (rules) → proposals → .md report → notice
you: approve | reject | postpone
approved: generates the development task → isolated branch + tests → publish only with a new authorization
```

## What she observes

It lives in `data/auto_melhoria/auto_melhoria.db`, only on your PC:

- each brain tried in each answer: who, the result (answer, escalated, `erro_provedor`, `timeout`, `resposta_vazia`, `stream_interrompido`) and the time until the first chunk;
- commands (such as game mode), unanswered or cancelled answers;
- complaints ("tá errado", "não entendi"), linked to the previous answer, and when the local model answered something you rejected (`rota_suspeita`);
- the transcription and voice times, and the voice failures.

**It does not store the text of what was said or audio:** only IDs, categories, times and the engine name. Events older than `dias_de_eventos` (30) are deleted when the day closes.

## The daily report

At `hora_relatorio` (default 20:00), if Nora is open and is neither answering nor in game mode, she closes the day:

- groups the events by probable cause (type, stage and engine);
- only what happened at least `min_ocorrencias` times (3) becomes a proposal: once is not enough;
- slow answers count above the `latencia_*_ms` limits;
- saves `data/auto_melhoria/relatorios/AAAA-MM-DD.md`.

Each proposal has a number, evidence (how many times, when, median and longest time), probable cause, suggested solution, estimated benefits, impact on time/cost/GPU, risk, required tests, likely files, priority and confidence.

- **Day without problems:** the report only says "Sem novas melhorias relevantes" (no new relevant improvements).
- **PC off at that time:** the report comes out the next time you open Nora, covering the missed period, without repeating.
- **The same problem on another day:** updates the same proposal, without duplicating.

**How you find out, without typing anything:**
- if Nora is open when the day closes: a Windows notification ("Nora: melhorias do dia"; clicking opens the report), and the report opens in the default program for `.md`;
- if it does not open, she shows the **full text** in the current session, when the interface is free, even without a new question;
- if the day closed with Nora closed: in the next conversation she opens the report or shows the full text.

She never does this in the middle of an answer or in game mode: she waits until she is free. The report only counts as shown after it actually appears. If the notification or the opening fail, the reason is recorded. An opening failure tries the text in the same session. A missing or unreadable file stays pending, with one presentation attempt per session to avoid repeated notices. Restore a UTF-8 copy at the given path (or fix the permissions) and restart the session to try again. Without a copy, there is no automatic recovery of the original content; do not close the same day again to try to recover it. With `apresentar = "terminal"`, the text always appears in the conversation, instead of opening the file.

**The report does not include the text of your questions.** For half-finished answers, it shows only the number, the reason and the date; the questions, only on request: `nora pendencias`. Old reports that included the beginning of the questions are cleaned up on their own.

## Deciding

| In conversation | From the terminal | What happens |
|---|---|---|
| "quais melhorias você sugeriu?" | `nora melhorias listar` | lists the ones waiting for a decision |
| — | `nora melhorias relatorio --abrir` | opens the most recent report |
| "aprova a melhoria 3" → "sim" | `nora melhorias aprovar 3` | approved for **development**: generates `data/auto_melhoria/tarefas/melhoria-3.md`, the specification for Codex. The code does not change |
| "recusa a melhoria 3" → "sim" | `nora melhorias recusar 3` | only comes back with new evidence (twice the occurrences) or in a new version |
| "adia a melhoria 3" → "sim" | `nora melhorias adiar 3 --dias 7` | comes back after those days |
| — | `nora melhorias estado 3 preparacao` | tracks development: `preparacao` → `em_teste` → `pronta_para_revisao` → `publicada` |
| — | `nora melhorias fechar-dia` | makes today's report now |

In conversation, she only decides with a clear number and after your "sim". "Não" cancels; so does changing the subject. **Publishing** needs a separate authorization: `nora melhorias estado 3 publicada --autorizo-publicar`. Each decision is recorded with who, when and the reason.

## Settings (`config/local.toml`)

```toml
[auto_melhoria]
ativa = true                  # false: observes and proposes nothing
hora_relatorio = "20:00"
min_ocorrencias = 3
latencia_resposta_ms = 2500   # until the first chunk of the answer
latencia_ouvido_ms = 1500
latencia_voz_ms = 2000
dias_de_eventos = 30
notificar = true              # Windows notification
apresentar = "abrir"          # "abrir" the .md or "terminal" (full text in the conversation)
```

## What does not exist yet (next stages)

- **P3, technical research:** today's diagnosis is rule-based, with no model and **no internet**. Research in official documentation, with cited sources and without sending anything personal, will be optional and off by default.
- **P4, supervised development:** today approving only generates the specification. Taking the task to Codex on an isolated branch and merging it after a new authorization is still a manual step.
- **HUD panel (v0.4.0):** "Melhorias da Nora", using the same database and the same numbers.
- **Scheduling with Nora closed:** today the report only comes out with Nora open (or the next time she opens). The system scheduler arrives with routines, in v0.6.0.

## Limits

- The rules know the problems listed above; a new kind of event falls into a generic proposal.
- The notification uses Windows PowerShell. If your Windows blocks notifications, the notice appears in the next conversation.
- Confidence and priority are estimates from the number and severity of the events, not a test of the problem.
