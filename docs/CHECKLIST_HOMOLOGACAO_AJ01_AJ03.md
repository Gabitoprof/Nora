# Acceptance of AJ-01, AJ-02 and AJ-03 — result on the Linux environment

Base checked: `Pull_code`, `ee5a82e742d95843b0cbfc674c17779d8427eab7` (same as the audit).
Fix branch: `fix/relatorios-aj01-aj03`.

Legend: `[x]` = verified in the code/automated tests of this environment;
`[ ] WINDOWS` = requires acceptance on the real computer;
`[ ] EXTERNO` (external) = depends on GitHub/external access. A simulated opening/notification
does not prove the real integration with Windows.

Validation: `ruff format --check .`, `ruff check .`, `pytest -q -ra` and
`nora --verificar`. Result: Ruff approved; **266 tests passed and 1 was skipped** (real Kokoro).
`nora --verificar` ended with exit code 0, with the missing external services listed below.
P3, P4, the HUD and personal Claude Code integration were out of scope.

# Nora — Test and acceptance checklist for the `Pull_code` branch

**Supporting document for Codex and local acceptance.**
**Base:** `REVISAO_NORA_PULL_CODE_POS_CORRECOES.md`, audit of commit `ee5a82e` of `Gabitoprof/Nora`.
**Goal:** fix only AJ-01, AJ-02 and AJ-03, keep the rest, prove the tests and prepare a PR to `Pull_code` **without automatic merge**.

## 1. Before changing

- [x] Check the current HEAD of `Pull_code` and compare it with `ee5a82e`; do not reapply fixes already present.
- [x] Read `CLAUDE.md`, `docs/ANDAMENTO.md`, `docs/AUTO_MELHORIA.md` and the attached review report.
- [x] Create a separate work branch, derived from `Pull_code`.
- [x] Confirm that P3 (web research), P4 (development integration) and personal Claude Code integration are out of this PR.

## 2. AJ-01 — Automatic report presentation

- [x] With `apresentar = "terminal"`, generate the report after `hora_relatorio`: the **whole text** appears in the current session, when Nora is free, without a new question and without restarting.
- [x] With `apresentar = "abrir"`, the `.md` file opens automatically in the associated application, when the system allows it. **Automated with simulated calls; confirm the integration on real Windows.**
- [x] If opening the file fails, Nora shows the content in the terminal in the same session, when possible, without bringing the conversation down.
- [x] While Nora is answering or resuming an answer, do **not** show the report or interrupt the interaction.
- [x] During game mode, do not open reports, do not reactivate Ollama and do not take the GPU; present it later, after leaving game mode and being free. **Automated with simulated calls; confirm the integration on real Windows.**
- [x] Once shown successfully, the report is not shown again on the next start.
- [x] If the day's report was already generated, do not create a duplicate proposal by restarting the program.

## 3. AJ-02 — Missing file

- [x] Create a test report and **delete only the temporary copy**, not personal data or production reports.
- [x] The missing report stays `mostrado = 0` / pending; Nora reports the failure.
- [x] There is a procedure to recover/regenerate the report from the persisted data, or to clearly say when recovery is not possible.
- [x] After recovery and actual display, update `mostrado = 1`.
- [x] Avoid infinite retries and repeated notifications every minute.

## 4. AJ-03 — Read failures

- [x] Simulate `PermissionError` when reading the file.
- [x] Simulate a file with invalid encoding (`UnicodeDecodeError`).
- [x] Simulate an I/O failure (`OSError`) and a file removed between the check and the read.
- [x] In all cases, the conversation keeps working, the technical error is logged without personal text and the report is not marked as shown if it was not presented.
- [x] The scheduler does not stop silently on a recoverable error; there is a technical log for diagnosis.

## 5. Regression — keep earlier behavior

- [x] Ctrl+C during generation records the incomplete question in `nora pendencias` in the same session, without duplicating. **Automated regression; does not replace the corresponding manual test.**
- [x] Resuming (`termina a resposta que ficou pela metade`) produces a new complete answer and is not confused with an incomplete permanent fact. **Automated regression; does not replace the corresponding manual test.**
- [x] Resuming keeps `conversa.ocupada = True` until it ends; the scheduler waits. **Automated regression; does not replace the corresponding manual test.**
- [x] In game mode, a cloud failure does not call the local brain; leaving game mode requires confirmation. **Automated regression; does not replace the corresponding manual test.**
- [x] When leaving game mode, Nora only offers to resume unanswered questions, without running them on her own. **Automated regression; does not replace the corresponding manual test.**
- [x] Voice switch commands and questions about voices are not confused. **Automated regression; does not replace the corresponding manual test.**
- [x] Delete/forget prevents removed facts and pending items from reappearing; permanent deletion requires confirmation. **Automated regression; does not replace the corresponding manual test.**
- [x] The `.md` report contains no question text, audio, keys, tokens or the user's personal data. **Automated regression; does not replace the corresponding manual test.**
- [x] The `aprovar`, `recusar` and `adiar` actions require the user's decision; approval only creates a task, without automatically changing the code. **Automated regression; does not replace the corresponding manual test.**

## 6. Quality automation — Codex / GitHub

Run at the repository root:

```bash
python -m pip install -e ".[dev,memoria]"
ruff format --check .
ruff check .
pytest
```

- [x] The three quality commands pass locally in Codex's environment.
- [x] Create deterministic tests for AJ-01/AJ-02/AJ-03 without depending on the real clock or a real Windows notification.
- [x] GitHub Actions CI approved on **Windows and Ubuntu**, Python **3.11 and 3.13**,
  on fix commit `71cf727` (run 41757775366; four `succeeded` jobs).
- [ ] **EXTERNO:** Create a PR against `Pull_code`, with the changed files, a description of the tests and residual risks.
- [x] Do not merge, do not create the `v0.3.0` tag and do not publish a release automatically.

## 7. Manual acceptance — Windows with an AMD GPU

These tests are **not replaced by CI**. Do them after the PR's technical approval or in a test environment on the real computer.

- [ ] **WINDOWS:** `nora --verificar` correctly reports the state of Ollama, whisper.cpp, voice and available credentials (without showing secrets).
- [ ] **WINDOWS:** `nora ouvir`: voice activation, transcription, spoken answer and typing with the microphone active.
- [ ] **WINDOWS:** Test switching to Piper/ElevenLabs and a question about engines without an improper switch.
- [ ] **WINDOWS:** Turn on game mode, confirm VRAM is released in Task Manager and check that a cloud failure does not reactivate Ollama.
- [ ] **WINDOWS:** `sai do modo jogo` asks for confirmation; after `sim`, check the offer to resume pending items.
- [ ] **WINDOWS:** Simulate a real interruption with Ctrl+C and check `nora pendencias`; resume a question and check that the record is resolved.
- [ ] **WINDOWS:** Temporarily set `hora_relatorio` a few minutes ahead in the **test environment** and test the `terminal` mode with Nora open and idle.
- [ ] **WINDOWS:** Repeat the `abrir` mode and confirm the file opens in the Windows default application.
- [ ] **WINDOWS:** Test presentation after Nora was busy, after game mode and after starting the computer/application after the scheduled time.
- [ ] **WINDOWS:** Confirm the Windows notification and the click action that opens the report; the current automated tests simulate the operating system.
- [ ] **WINDOWS:** Confirm that reports stored in `data/auto_melhoria/relatorios/` do not expose the content of personal questions.
- [ ] **WINDOWS:** Calibrate latency and search times with the AMD GPU, real STT and TTS, without sending personal data to external services.

## 8. Final acceptance

- [x] AJ-01, AJ-02 and AJ-03 fixed and covered by regression tests.
- [x] Earlier fixes A1–A6 kept; no component reimplemented unnecessarily.
- [x] Report delivered automatically when Nora is free, in the chosen mode, without a required restart.
- [x] A file failure does not cause silent loss or block conversations.
- [ ] **EXTERNO:** Green CI and reviewed PR; **manual acceptance done** for the items that depend on Windows, audio and the AMD GPU.
- [x] Merge and release only with explicit approval.

**Scope note:** P3, P4 and the HUD are not part of this set of fixes. Development implementation by Codex must remain supervised.

## Evidence and limitations of this run

- AJ-01: deterministic tests of the clock, the input wait and the text,
  typed-voice and no-speech listening loops prove delivery in the current session. The main loop
  presents the content; the scheduler closes/notifies. Game mode and an answer in progress block it.
- AJ-02: the removed temporary file stays pending. The warning points to restoring a
  backup and restarting; the test restores the file and proves the presentation and `mostrado = 1`.
  Automatic regeneration was not implemented: there is no guaranteed full historical copy.
- AJ-03: PermissionError, UnicodeDecodeError, OSError and removal between check/read
  are simulated. The conversation keeps answering, and the diagnosis persists without the
  potentially personal exception message. The scheduler logs the technical class and stays active.
- Failed presentation attempts limited to one per report per session.
- `nora --verificar`: ran; does not prove inference/voice. Ollama, Whisper and Kokoro
  absent; optional cloud SDKs/keys and the personal notes folder not configured.
- Real Kokoro test skipped for lack of `ELLA_KOKORO_PASTA`/local model.
- History before the portability fix: the attached review identified a failure
  on Windows 3.11/3.13 and success on Ubuntu in 41756602954 and 41756693905.
  The CRLF failure was reproduced locally before the fix.
- Fix `71cf727`: parameterized LF/CRLF test; restored bytes kept and the
  presented content compared as text. No production file was changed
  in this round. Local environment: Linux, Python 3.12.14; 266 passed, 1 skipped.
- New CI: [run 41757775366](https://github.com/Gabitoprof/Nora/actions/runs/41757775366).
  Four jobs confirmed as `This job succeeded` on the commit's public checks page:

  | Environment | Python | Result | Job |
  |---|---|---|---|
  | Ubuntu | 3.11 | Approved | [126337864642](https://github.com/Gabitoprof/Nora/actions/runs/41757775366/job/126337864642) |
  | Ubuntu | 3.13 | Approved | [126337864198](https://github.com/Gabitoprof/Nora/actions/runs/41757775366/job/126337864198) |
  | Windows | 3.11 | Approved | [126337864527](https://github.com/Gabitoprof/Nora/actions/runs/41757775366/job/126337864527) |
  | Windows | 3.13 | Approved | [126337864436](https://github.com/Gabitoprof/Nora/actions/runs/41757775366/job/126337864436) |

  The matrix runs Ruff, pytest and `nora --verificar`; it does not prove physical audio/GPU.
- The GitHub API (`api.github.com`) answered `Forbidden`: `gh pr create` also failed with `Forbidden` on GraphQL; no PR created in this run.
  The branch was pushed to GitHub successfully.
  The REST/GraphQL API and `gh pr create` remain blocked by `Forbidden` in this round.
  `GH_TOKEN` is present, but validating authentication through the API also fails;
  it is not possible to conclude that a new token would solve the network policy.
  The public comparison page reports an unauthenticated session (`logged_in=false`).
  Git through the proxy allows reading and pushing; it does not provide a web session or prove API access.
  CI can be checked on GitHub's public page, without working around the API block.
  [Manual PR form for Pull_code](https://github.com/Gabitoprof/Nora/compare/Pull_code...fix/relatorios-aj01-aj03?expand=1).
- Merge, tags and releases not done. The fixed code passed remote CI. Integration acceptance
  remains pending on creating/reviewing the PR and Windows/AMD acceptance.

## Additional input acceptance — pending on real Windows

- [ ] **WINDOWS:** keyboard during the alert, Ctrl+C, accented characters, prompt
  restoration and two consecutive inputs, checking for interference or blocked input threads.
- [ ] **WINDOWS:** listening in prolonged silence delivers the report without new speech.

These caveats from the re-evaluation were not treated as defects without reproduction.
Recovery remains manual from a backup; the test keeps that behavior.
