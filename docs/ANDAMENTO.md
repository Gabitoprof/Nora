# Nora progress (for review)

Summary of the project state for a code review. Updated on 05/11/2026 (preparing the `v0.3.0` release), branch `Pull_code`.

## What it is

Personal voice assistant in pt-BR, local first, all rights reserved (MIT up to v0.3.0). Python 3.11–3.13. Project rules in `CLAUDE.md`; full vision in `PROJETO_ASSISTENTE_IA.md`.

## Versions

- `v0.2.0` released (tag): voice conversation and memory.
- `v0.3.0` released (05/11/2026): model router. Release, quality and acceptance in [`RELEASE_v0.3.0.md`](RELEASE_v0.3.0.md).
- Next: `v0.3.1` (voice without tone changes between sentences and a more accurate ear) and `v0.4.0` (HUD, on the `feat/v0.4.0-hud` branch).

## Path of a question

1. **Listen:** Silero VAD (`vad.py`) → whisper.cpp HTTP (`ouvido.py`) → the word "Nora" (`ativacao.py`). Or typed text. Loops: `conversa_voz.py`, `maos_livres.py`.
2. **Remember:** `conversa.py::_lembrar` gathers preferences, facts and passages (`memoria.py`: SQLite + sqlite-vec, bge-m3 embeddings through Ollama), agenda (`agenda.py`) and Obsidian notes (`notas.py`).
3. **Classify:** `roteador.py`. Commands (brain, game mode), keyword triage, the local model's `{pensar}` and a second chance when the person complains.
4. **Execute:** local Ollama (`cerebro.py`); cloud ChatGPT (`cerebro_openai.py`, Responses API) → Claude (`cerebro_nuvem.py`) → local. No brain switch if the answer has already started coming out.
5. **Speak:** emotion tags (`emocao.py`) → voice (`voz.py`: ElevenLabs, Kokoro, Piper, ComfyUI, with fallback). Voice switch by command in `troca_voz.py`.
6. **Record:** JSONL history (`historico.py`) and background curation (`curadoria.py`), which notes, corrects and forgets facts. Answers that did not finish go to `respostas_pendentes` (`memoria.py`).
7. **Observe and propose:** `observador.py` records metrics and categories (no text); `melhorias.py` closes the day, generates proposals and the report and stores the decisions.

## Done in v0.3.0 (commits since v0.2.0)

- Automatic emotion in the voice (`emocao.py`, `[emocao]`).
- Local ↔ cloud router, game mode, holding phrase, fallbacks, `[cérebro]` notices.
- Triage and second chance (`[roteador] triagem`).
- Deleting and correcting facts in conversation (the `esquecer` field in curation).
- ChatGPT as the default for complex questions, Claude as fallback (`[roteador] complexas`, `[modelos.openai]`).
- Voice switching by speaking ("troque para a voz do Piper").
- Obsidian notes index (`[notas] pasta`, `nora notas ler|buscar|status`, `data/notas.db`).
- Fix: text typed in `nora ouvir` is now read with the microphone on (`vad.py::falas`).
- Test that keeps `.env.example` up to date (`tests/test_env_exemplo.py`).

## Fixes from the 03/11/2026 review (next-actions report)

| ID | Fix | Test |
|---|---|---|
| A1 | Game mode does not call the local brain when the cloud fails; it warns (`FRASE_JOGO_SEM_NUVEM`) | `test_modo_jogo_sem_nuvem_nao_reacende_o_cerebro_local` |
| A2 | Forget = stop using (`esquecidos` table: filters `buscar_trocas` and blocks `importar`); `nora memoria apagar` = delete for good (memory + `data/historico`, with preview and `--confirmar`) | `test_esquecido_nao_volta_...`, `test_apagar_de_vez_...`, `test_comando_apagar_...` |
| A3 | A command with content answers the content (`achar_comando` returns whether it is pure) | `test_comando_com_pergunta_responde_a_pergunta` |
| A4 | A local model that drops after speaking does not get another answer stitched on | `test_falha_do_local_no_meio_nao_emenda_outra_resposta` |
| A5 | `Roteador.situacao` (complete, interrupted, no answer) goes to the history; only complete ones go to curation | `test_resposta_interrompida_fica_marcada_...`, `test_falha_da_nuvem_no_meio_fica_marcada` |
| A6 | Voice switching requires a switch verb and ignores questions/comparisons | `test_perguntas_sobre_vozes_nao_trocam_a_voz` |

All six were reproduced by a test before the fix (A1: local called in game mode; A3: `comando_em` returned "nuvem" and the question was lost; A4: output "Uma reResposta do Claude."; A2: a forgotten passage came back with similarity 0.79; A6: "qual voz é melhor..." became a request).

## Consolidated review of 04/11/2026 (supervised self-improvement plan)

| Stage | Delivered | Tests |
|---|---|---|
| P1 · A1 | Leaving game mode asks for "sim" (rule in `confirmacao.py`, no model); "como sair do modo jogo?" changes nothing; mode switches are stored as `situacao: "comando"` and do not go to curation | `test_sair_do_modo_jogo_pede_confirmacao_...` |
| P1 · A5 | `respostas_pendentes` table: one "open" row per answer becomes a pending item if the program crashes; also interrupted stream, no answer, Ctrl+C; identified resumption ("termina a resposta que ficou pela metade"), 3 attempts; `nora pendencias`; forget/delete remove the subject's pending items | `test_resposta_interrompida_vira_pendencia_...`, `test_pendencia_de_cancelamento_...`, `test_respostas_completas_e_comandos_...`, `test_comando_pendencias_...` |
| P1 · A4 | `CerebroIndisponivel.categoria` and `categoria_do_erro`; `Roteador.tentativas` (engine, result, time to the 1st chunk); fallback only before content | `test_tentativas_ficam_anotadas_...` |
| P2 | `observador.py` (no text) and `melhorias.py`: rule-based diagnosis, proposals with evidence, daily report, one per day, recovery of the missed day, a scheduler that waits for Nora to be free, Windows notification, decisions (approving generates a task; publishing requires `--autorizo-publicar`), `nora melhorias` and by voice with "sim" | `tests/test_auto_melhoria.py` (12 tests) |

### Audit of 04/11/2026 (`AUDITORIA_NORA_PULL_CODE_2026-11-03.md`)

The five points were checked in the code and reproduced by a test before the fix.

| Point | Fix | Test |
|---|---|---|
| P0 Ctrl+C | `conversa.py::_responder` handles `KeyboardInterrupt` together with `GeneratorExit`: pending item stored immediately, only once | `test_ctrl_c_no_meio_vira_pendencia_na_hora` |
| P1 busy resumption | `perguntar` also sets `ocupada` during `_retomar` (`try/finally`) | `test_retomada_marca_a_nora_ocupada_e_o_relatorio_espera` |
| P1 privacy | `_relatorio` does not write the question; `_limpar_perguntas_dos_relatorios` cleans the old ones | `test_relatorio_nao_mostra_perguntas_e_limpa_os_antigos` |
| P1 presentation | `apresentar()` opens the .md or shows the full text; `marcar_mostrado` only afterwards; `falha_aviso` recorded; waits for game mode; `[auto_melhoria] apresentar` | `test_inicio_da_sessao_abre_...`, `test_se_nao_abrir_...`, `test_relatorio_do_meio_da_sessao_...`, `test_no_modo_jogo_o_relatorio_espera` |
| P2 game mode | `sem_resposta` rule rewritten; `_oferecer_retomada_do_jogo` when leaving game mode (only offers) | `test_sem_resposta_no_modo_jogo_nao_sugere_usar_o_local` |

**Not implemented (decision pending):** P3, technical web research (optional, off by default), and P4, taking the approved task to Codex on an isolated branch (manual today). Self-improvement is new scope: the `v0.3.0` tag does not depend on it.

## Pending

- **Validation on the real PC** (Windows, AMD), which CI does not cover:
  - [ ] `nora --verificar` with everything ok (Ollama, whisper, voice, Claude, ChatGPT, notes).
  - [ ] `nora ouvir`: speak and type; "troque para a voz do Piper" and "volta pro ElevenLabs"; "o Piper é melhor que o Kokoro?" does not switch.
  - [ ] "modo jogo" frees the VRAM (Task Manager); without internet, she warns and the VRAM stays free.
  - [ ] "use o Claude para explicar fotossíntese" answers through Claude; the mode stays automatic.
  - [ ] "esquece que eu ..." and then `nora memoria apagar "..."` (preview and `--confirmar`).
  - [ ] By voice: "apaga de vez ..." → she says what would go → "sim, pode apagar"; and a "não" cancels.
  - [ ] `nora notas ler` and a question about a note.
  - [ ] "sai do modo jogo" asks first; "como sair do modo jogo?" only explains.
  - [ ] Ctrl+C in the middle of an answer → the notice appears in the next conversation → "termina a resposta que ficou pela metade".
  - [ ] `nora melhorias fechar-dia` generates the report; the Windows notification appears and opens the file (the notification PowerShell has not been tested on a real Windows yet).
  - [ ] With Nora open after 20:00 (or changing `hora_relatorio`), the report opens on its own in the .md program; with Nora closed, it opens in the next session.
  - [ ] Ctrl+C while she is still thinking (before speaking) → `nora pendencias` already shows the question, immediately.
  - [ ] Game mode without internet → a question → "sai do modo jogo" → "sim" → the offer to resume appears.
  - [ ] Check with the real bge-m3 the `TROCA_ESQUECIDA` limits and the latency limits in `[auto_melhoria]`.
- Done on 05/11/2026: final audit, the Enter regression in `nora falar` fixed, issue #3 fixed, documentation reviewed and version `0.3.0`. The updated list of manual tests, the risks and the acceptance steps are in [`RELEASE_v0.3.0.md`](RELEASE_v0.3.0.md); merge, tag and release wait for the maintainer's authorization.
- Next (proposal, not decided yet): a classifier with confidence in the router, first with bge-m3 and examples per route; test `Mapika/decider-2b` (Apache-2.0, GGUF) as an alternative.
- Roadmap: v0.4.0 HUD, v0.5.0 MCP tools (with permissions), v0.6.0 routines, v0.7.0 agents, v0.8.0 distributed mode.

## Rules the review should check

- Nothing personal in Git: keys only in `.env`, personal config in `config/local.toml`, `data/` ignored.
- Every new dependency in `docs/LICENCAS.md` (tested by `tests/test_licencas.py`); nothing AGPL; GPL tools (Piper, espeak) only as a separate process.
- Every environment variable read by the code in `.env.example`, with no value.
- Tests pass without `anthropic`, `openai`, `numpy` or `sqlite_vec` installed (optional dependencies).
- Before committing: `ruff format .`, `ruff check .`, `pytest`. Commits in English (Conventional Commits); user-facing texts and code names in pt-BR.
- Target: Windows with an AMD GPU (Vulkan); nothing that only works with CUDA.

## Points to look at carefully

- `roteador.py::_nuvem`: cloud order, notices and the failure-mid-answer case.
- `notas.py`: incremental update (modification date and size), optional vector index and the background thread that reads the notes when the conversation opens (`conversa.py::nova_conversa`).
- `troca_voz.py`: the list of question words (`_PERGUNTA`) may block some unusual legitimate request.
- `memoria.py`: the `TROCA_ESQUECIDA` (0.6) and `FATO_ESQUECIDO` (0.85) limits were calibrated with test vectors; worth checking with the real bge-m3.
- Concurrency: curation, notes and the self-improvement scheduler run on separate threads, each with its own SQLite connection and lock (`check_same_thread=False`); observer and improvements share the same `auto_melhoria.db` file.
- `melhorias.py::notificar`: the PowerShell script (notification with `activationType="protocol"` and the .md path) was only tested with a mocked `subprocess.run`.
- `melhorias.py::diagnosticar`: the rules and limits are a starting point; the proposal texts are generic per category.
- Keyword triage is fragile by nature; its replacement is in the Pending section.

## How to test

```bash
pip install -e ".[dev,memoria]"
ruff check . && pytest
```

On the real machine: `nora --verificar` (checks keys, packages, Ollama, notes and voices), `nora conversar --medir` and `nora ouvir`.
