# Release v0.3.0 — Model router

Stable version `v0.3.0`, prepared on the `Pull_code` branch and merged into `main` through PR [#5](https://github.com/Gabitoprof/Nora/pull/5), with the maintainer's authorization on 05/11/2026.

## 1. Release notes

**Nora now has two brains that work together.** Everyday conversation stays on your PC, free and private. The hard questions go to the cloud and come back with the same voice, the same personality and the same memory.

### What's new

- **Model router:**
  - the local brain (Ollama) handles conversation; code, math, analyses, plans and long texts go to **ChatGPT**, with **Claude** as fallback, and the local model is the last fallback;
  - while the cloud thinks, she says a holding phrase;
  - if you complain about a local answer ("tá errado"), the question gets a second chance in the cloud.
- **Spoken commands:**
  - "use o cérebro local", "use o ChatGPT", "use o Claude", "modo automático";
  - "use o Claude para explicar fotossíntese" answers only that question through Claude;
  - **game mode:** frees the graphics card and answers through the cloud. To leave it, she asks for confirmation, and she never goes back to using the card on her own.
- **Emotion in the voice:** she picks the tone of each sentence. On ElevenLabs v3, she actually laughs, sighs and whispers.
- **Switching the voice by speaking:** "troque para a voz do Piper", "volta pro ElevenLabs".
- **Obsidian notes:** she reads your vault (read only) and uses the notes to answer, saying which note it came from.
- **Forget and delete for good:** "esquece isso" makes her stop using the subject; "apaga de vez ..." shows what will go and only deletes after your "sim".
- **No answer lost:** if an answer drops midway, is cancelled or gets no answer, the question is kept. "Termina a resposta que ficou pela metade" answers again, in full.
- **Supervised self-improvement:**
  - once a day, she gathers what went wrong (failures, slowness, complaints) into a report of proposals, without storing the conversation text;
  - you approve, reject or postpone; nothing changes in the code without you;
  - in this version, no internet and no AI model in the diagnosis.

### Fixes in this release preparation

- **Enter in `nora falar` with self-improvement on:**
  - an error while presenting the report left the keyboard reader behind, and the next Enter (the one to stop recording) was lost;
  - opening the report could take the focus away from the terminal.
  
  Now the report opens minimized and without focus, and the prompt reappears after it.
- **Substring search in the agenda and in `listar --contendo`** ([#3](https://github.com/Gabitoprof/Nora/issues/3)): accented capitals ("Álgebra" finds "álgebra") and no `_`/`%` wildcards.

### How to update

```bash
git pull
```

```bash
python -m pip install -e ".[voz,memoria,nuvem]"
```

```bash
nora --verificar
```

The cloud is optional: it needs `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in `.env`. With no key at all, everything stays on the PC. There is no manual migration: the databases get the new tables on their own (`respostas_pendentes`, `esquecidos`, `data/auto_melhoria/`).

## 2. Quality report

### Scope

- **Base:** `Pull_code` at `70d39b7` (with PR #4 already merged), plus the commits of this preparation.
- **Out of the release:** no commit from the `feat/v0.4.0-hud` branch. Checked with `git log Pull_code..feat/v0.4.0-hud`: 5 commits, none in `Pull_code`. `hud/README.md` is the foundation marker, already present in `main`.
- **Out of scope, by earlier decision:**
  - P3 (technical web research);
  - P4 (automated development);
  - personal integration with Claude Code;
  - the HUD.

### Final audit

| Check | Result |
|---|---|
| `CLAUDE.md` rules (pt-BR, Conventional Commits, nothing personal in Git, licenses, `.env.example`, nothing CUDA-only) | Ok. No `data/`, `.env` or `config/local.toml` file versioned; no secret found; "Jarvis/Marvel" only in the rules that forbid them |
| Dependency licenses (`tests/test_licencas.py`) | Ok. New dependencies of the stage: `openai` and `anthropic` (Apache-2.0), in the `nuvem` extra |
| Environment variables (`tests/test_env_exemplo.py`) | Ok |
| Tests without the optional packages (anthropic, openai, numpy, sqlite-vec) | Ok |
| Enter regression in `nora falar` with self-improvement | **Found and fixed** (section 2.1) |
| Open issue [#3](https://github.com/Gabitoprof/Nora/issues/3) | **Reproduced and fixed** |
| Earlier fixes (A1–A6, P1/P2, audit, AJ-01–AJ-03) | Preserved; all regression tests pass |
| Stage documentation (README, roadmap, goal, mind map `.md` and `.canvas`, guides, idea bank, CHANGELOG) | Reviewed for the v0.3.0 state |

### 2.1 Enter regression in `nora falar`

With self-improvement on (default), PR #4 started reading the keyboard on a helper thread (`melhorias.py::ler_entrada`), while the session loop presents the reports. I found three paths where an Enter was lost:

| Cause | How it was confirmed | Fix |
|---|---|---|
| An error while presenting the report escaped `ler_entrada`, and the reading thread stayed alive and swallowed the next Enter (the one to stop recording). In `nora falar`, the error also brought down the conversation | **Reproduced** by a test with a keyboard that blocks like the real one (`test_falha_ao_apresentar_nao_deixa_leitor_orfao_que_engole_o_enter`) | The error is recorded (only the type) and `ler_entrada` only returns with the line its own thread read |
| The `abrir` mode (default) opened the `.md` with focus on Windows, and the Enter went to the editor. On Linux, `xdg-open` inherited Nora's terminal | Code reading (`os.startfile` without `show_cmd`; `Popen` inheriting stdin). Focus on Windows **cannot be reproduced in the cloud** | Windows: opens **minimized and without activating** (`SW_SHOWMINNOACTIVE`). Other systems: no stdin, stdout and stderr, in its own session. Test: `test_abrir_o_relatorio_nao_rouba_o_teclado_da_sessao` |
| The notification PowerShell inherited the console keyboard | Code reading (`subprocess.run` without `stdin`) | `stdin=DEVNULL` (same test) |
| (Usability) A report shown during the wait hid the "[Enter para falar]" | Test | The prompt is printed again (`test_relatorio_que_aparece_na_espera_mostra_o_prompt_de_novo`) |

I also ran the real `nora falar` loop (`conversar_por_voz`, with the real `input`) in a **Linux pseudo-terminal**, in the `abrir` and `terminal` modes: two cycles of Enter to speak and Enter to stop, answered and with the prompt back, before and after the fix. On Linux the basic flow already worked; the real Windows stays on the acceptance list.

### 2.2 Automated tests

| Run | Result |
|---|---|
| `ruff format --check .` | Ok |
| `ruff check .` | Ok |
| `pytest` (Linux, Python 3.12, local) | **270 passed**, 2 skipped (real Kokoro and an audio test without a device) |
| `pytest` without anthropic, openai, numpy and sqlite-vec | **252 passed**, 13 skipped |
| `nora --verificar` | Exit code 0 |
| GitHub Actions CI (Windows and Ubuntu × Python 3.11 and 3.13) | See section 2.3 |

Found during acceptance (05/11): with the `.venv` recreated on another Python version, `nora ouvir` said "Falta a parte de áudio" (the audio part is missing) with the package installed. The message now shows the real cause (`test_audio_que_nao_carrega_mostra_a_causa`).

New tests in this preparation: `test_falha_ao_apresentar_nao_deixa_leitor_orfao_que_engole_o_enter`, `test_relatorio_que_aparece_na_espera_mostra_o_prompt_de_novo`, `test_abrir_o_relatorio_nao_rouba_o_teclado_da_sessao`, `test_busca_por_trecho_ignora_maiusculas_acentuadas_e_nao_usa_curingas`.

### 2.3 CI

All the candidate's runs are in section 6. The criterion to change the version from `0.3.0.dev0` to `0.3.0` was green CI on all four combinations at the fixes commit (`389e3cc`).

## 3. Pending manual tests (Windows with an AMD GPU)

CI has no microphone, speaker, GPU, Ollama, whisper.cpp or the real keys. Items to validate on the PC:

**Basics**
- [ ] First of all: `python --version` in the active `.venv` shows **3.13.x**. In the 05/11 acceptance, the `.venv` was on another Python version and the audio packages compiled for 3.13 did not load (`_cffi_backend`). The fix is to recreate it with `py -3.13 -m venv .venv --clear` and reinstall.
- [ ] `nora --verificar` with everything ok: Ollama, whisper-server, main and fallback voice, ChatGPT and Claude keys and connections, notes, self-improvement.
- [ ] `nora ouvir`: activation by "Nora", transcription, spoken answer; typing with the microphone on.

**Enter regression (priority)**
- [ ] `nora falar` with an unshown report (run `nora melhorias fechar-dia` first and close Nora): on opening, the report opens **minimized** in the taskbar and the **first Enter** already starts recording.
- [ ] `nora falar`: ten cycles in a row of Enter to speak and Enter to stop, without any lost Enter.
- [ ] With `hora_relatorio` 2 minutes away, leave Nora idle at "[Enter para falar]": the report appears (minimized, or the text on screen), the prompt comes back and the next Enter works.
- [ ] The same with `apresentar = "terminal"`, and in `nora conversar` (text).
- [ ] Ctrl+C at the prompt closes Nora normally; typed accents arrive correctly.

**Router and voice**
- [ ] Hard question ("escreve um script python...") → holding phrase → ChatGPT answer; with a wrong OpenAI key, Claude answers with the `[cérebro]` notice.
- [ ] "use o Claude para explicar fotossíntese" answers through Claude and the mode stays automatic.
- [ ] "modo jogo" frees the VRAM (Task Manager); without internet, she warns and the VRAM stays free; "sai do modo jogo" asks for "sim"; "como sair do modo jogo?" only explains.
- [ ] "troque para a voz do Piper" and "volta pro ElevenLabs"; "o Piper é melhor que o Kokoro?" does not switch.

**Memory**
- [ ] "esquece que eu ..." and then "apaga de vez ..." → "sim, pode apagar"; "não" cancels.
- [ ] `nora notas ler` and a question about a note.
- [ ] Ctrl+C while she thinks → `nora pendencias` shows the question immediately → "termina a resposta que ficou pela metade".

**Self-improvement**
- [ ] The Windows notification appears and clicking opens the report. The PowerShell script has never run on a real Windows.
- [ ] The report in `data/auto_melhoria/relatorios/` does not have the text of the questions.
- [ ] Calibrate with the real bge-m3 and GPU the `TROCA_ESQUECIDA` (0.6) and `latencia_*_ms` limits.

## 4. Residual risks

| Risk | Impact | Mitigation |
|---|---|---|
| Some programs ignore "open minimized and without focus" (e.g. an editor that is already open and brings its own window to the front) | The Enter may go to the editor, as before | Validate on the PC; if it happens, use `[auto_melhoria] apresentar = "terminal"` |
| The Windows notification (PowerShell + WinRT) was not tested on a real Windows | The notification may not appear | The failure is recorded and the report appears in the session anyway |
| Limits calibrated with test vectors (`TROCA_ESQUECIDA`, latencies) | "Forget" may hide too many or too few passages; slowness proposals may come out too often or too rarely | Adjustable; `nora memoria apagar` shows beforehand what goes |
| The router's triage is keyword-based | Some questions go to the wrong place | Second chance, commands and the automatic `rota_suspeita` proposal; the classifier with confidence is left for a next version |
| The self-improvement diagnosis is rule-based | Generic proposals per category | The decision is always human; research (P3) is optional and future |
| Reading the keyboard on a thread is new in `nora falar` | Console behavior varies between Windows terminals | Regression tests and the manual script above (section 3) |

## 5. Final acceptance and publishing (with authorization)

1. **Download the candidate** on the PC (with Nora closed):
   ```bash
   cd B:\Nora
   ```
   ```bash
   git pull origin Pull_code
   ```
   ```bash
   B:\Nora\.venv\Scripts\python.exe -m pip install -e ".[voz,memoria,nuvem]"
   ```
2. **Run the manual tests** in section 3 and note the result of each item. If any fails, the release stops and the fix goes into `Pull_code`.
3. **Review the Pull Request** `Pull_code` → `main` and check green CI on the last commit.
4. **Authorize** (the maintainer): merge the PR; tag `v0.3.0` on the merge commit in `main`; GitHub release with the notes from section 1.
5. **After the release:** create `0.3.1.dev0` (or start `0.4.0.dev0`) on the development branch.

## 6. CI record

| Commit | Run | Result |
|---|---|---|
| `389e3cc` (Enter and search fixes) | [42087432996](https://github.com/Gabitoprof/Nora/actions/runs/42087432996) | Green: Windows 3.11, Windows 3.13, Ubuntu 3.11, Ubuntu 3.13 (Ruff, pytest, `nora --verificar`) |
| `df72267` (message for audio that does not load) | [42110839485](https://github.com/Gabitoprof/Nora/actions/runs/42110839485) (push) and [42110850121](https://github.com/Gabitoprof/Nora/actions/runs/42110850121) (PR #5) | Green on all four combinations |

## 7. Acceptance performed and release decision

Done by the maintainer on Windows with an AMD GPU on 05/11/2026:

- `nora --verificar` with version `0.3.0`. Found and resolved: the `.venv` was on another Python version; it was recreated on 3.13 and the audio message started showing the cause (`df72267`).
- **Enter regression, approved:** with self-improvement on, the report opened at the start of `nora falar`, the first Enter started recording and the second stopped it. The prompt came back after the whisper-server error, since it was closed.
- **Full voice conversation** with the whisper-server open: recording, transcription, spoken answer and prompt back.

**Decision:** the maintainer authorized closing v0.3.0 with the other section 3 items (ten cycles in a row, report during the wait, router, game mode, memory and notification) to be followed up in use. They remain as pending validation items.

**For `v0.3.1`, observed during acceptance:**
- **Voice:** the first short sentence is synthesized alone, and the switch to the next request changes the tone and creates a pause on ElevenLabs v3. Plan: join the first short sentence with the next one and test continuity (`previous_text`/`next_text`) and a fixed seed.
- **Ear:** the Whisper `small` model gets less clear speech wrong. Plan: quantized `large-v3-turbo` through Vulkan and vocabulary as a hint also in `nora falar`.
