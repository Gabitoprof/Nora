# Changelog

All notable changes to the project are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow [Semantic Versioning](https://semver.org/) (`vMAJOR.MINOR.PATCH`).

## [Unreleased]

### Changed

- **License:** from 06/11/2026, the code is **all rights reserved** (public for reference only). Versions up to `v0.3.0` remain under MIT.
- **Documentation and code comments in English.** Nora's speech, messages, CLI help, voice commands, config keys and the names in the code stay in Portuguese (rule in `CLAUDE.md`).

## [0.3.0] - 2026-11-05

**Model router.** Everyday conversation stays on the PC, and hard questions go to the cloud and come back with the same voice, persona and memory. Stage criterion met in the automated tests: the hard question goes up to the API (ChatGPT, with Claude as fallback) and the answer comes back spoken in Nora's voice. Along with it came emotion in the voice, switching brain and voice by command, Obsidian notes, forget and delete for good, recoverable half-finished answers and supervised self-improvement. Acceptance on Windows with an AMD GPU recorded in `docs/RELEASE_v0.3.0.md`.

### Added

- **Model router** (`[roteador]`, guide in `docs/CEREBRO.md`):
  - the local brain (Ollama) talks; hard questions go to the cloud in the order **ChatGPT → Claude → local** (`[roteador] complexas`), with a holding phrase in the same voice;
  - the cloud is triggered by triage (code, math, analyses, plans, texts, long questions), by the local model's `{pensar}` and by a second chance when you complain;
  - direct request: "pensa com calma", "pergunta pro ChatGPT ...", "use o Claude para ...". The request is answered by whoever was called and the mode does not change;
  - spoken commands: "use o cérebro local", "use o ChatGPT", "use o Claude", "modo automático", "modo jogo" (frees the graphics card and answers through the cloud) and "sair do modo jogo" (asks for confirmation);
  - fallbacks in both directions, with `[cérebro]` warnings. A reply that dropped midway is not stitched with another brain's;
  - `--medir` and the history show who answered;
  - config `[modelos.openai]`, `[modelos.nuvem]` and `[roteador]`; extra `.[nuvem]` (`openai` and `anthropic` SDKs); `--verificar` checks keys, packages and connection.
- **Emotion in the voice** (`[emocao]`): Nora picks the tone of each sentence from the context. On ElevenLabs v3 it becomes an audio tag (she laughs, sighs, whispers); on Flash, a tone adjustment; on local voices, the mark is removed. Curation learns from your reactions.
- **Switching the voice by speaking:** "troque para a voz do Piper", "volta pro ElevenLabs", "qual voz você está usando?". Questions and comparisons about voices do not switch anything.
- **Obsidian notes** (`[notas] pasta`, guide in `docs/OBSIDIAN.md`): incremental, read-only reading of the vault, with the similar passages used in the answer and cited by note name. Commands `nora notas ler | buscar | status`.
- **Forget and delete for good** (guide in `docs/MEMORIA.md`):
  - "esquece que eu disse X" stops using the subject, including passages from old conversations and `importar`;
  - "apaga de vez X" (in conversation, with "sim") or `nora memoria apagar "X" --confirmar` removes it from memory and history, first showing what will be removed.
- **Half-finished answers become pending items:** an answer that dropped, got no reply, was cancelled (Ctrl+C) or was cut by the program closing is kept, never as a fact. "Termina a resposta que ficou pela metade" answers again, complete and labeled; `nora pendencias` lists and cancels.
- **Supervised self-improvement** (`[auto_melhoria]`, guide in `docs/AUTO_MELHORIA.md`):
  - an observer records, without the conversation text, attempts, failures by category, timings and complaints;
  - once a day, local rules (no internet and no model) group what repeated into proposals with evidence, cause, solution, impact, risk and tests;
  - the report shows up on its own, without interrupting an answer or game mode;
  - you approve, reject or postpone (`nora melhorias`, or by voice with "sim"). Approving only produces the specification; nothing changes in the code or is published without you.
- Tests that keep `.env.example` and `docs/LICENCAS.md` up to date.

### Fixed

- **Enter in `nora falar` with self-improvement on:**
  - an error while presenting the report could leave behind the thread that reads the keyboard, and it swallowed the next Enter (the one to stop recording);
  - the `abrir` mode could take focus away from the terminal (the `.md` editor kept the keyboard on Windows; on Linux, `xdg-open` inherited the terminal).
  
  Now the report opens minimized and without focus, neither the opened program nor the notification uses the session's keyboard, and the prompt reappears after a report.
- **Audio that does not load:** when the audio package is installed but does not load (the common case is a `.venv` recreated with another Python version), Nora shows the real cause instead of "Falta a parte de áudio".
- **Substring search in the agenda and in `listar --contendo`** ([Gabitoprof/Nora#3](https://github.com/Gabitoprof/Nora/issues/3)): "Álgebra" now finds "álgebra", and `_` and `%` no longer act as wildcards.
- **Game mode:** if no cloud answers, Nora does not go back to the local brain (which would occupy the graphics card); the question becomes a pending item and, when leaving game mode, she offers to resume it.
- **Command with a request:** "use o Claude para explicar fotossíntese" answers the question instead of only switching the mode; "como sair do modo jogo?" is answered, not executed.
- **Answer that drops midway:** no two answers stitched together. The answer is marked in the history (`"situacao"`) and does not go to memory.
- **Ctrl+C** in the middle of an answer stores the pending item immediately; **resuming** an answer counts as "busy" for the daily report.
- **Daily report:** does not include the text of the questions (old reports are cleaned); only counts as shown after it appears; a missing or unreadable file stays pending and does not bring the conversation down.
- **Deleting in conversation:** memory no longer re-records the deleted fact or notes the delete request itself.
- In `nora ouvir`, typed text is read even with the microphone capturing nonstop.

## [0.2.0] - 2026-11-02

**Memory.** Nora remembers you from one conversation to the next: notes facts by area (health, studies, work...), keeps every full exchange, finds appointments by day ("o que tenho amanhã?") and learns how you want her to speak (pronunciations and preferences). Stage criterion met: in the test, facts said in one conversation (the exam, the birthday) were remembered in new conversations, including by date ("foi ontem, 31 de outubro"). Along with it came typing instead of speaking, voice priority over other programs and the path to creating your own voice (dataset, checker and Piper training on Kaggle or Colab).

### Added

- **Memory across conversations** (v0.2.0): after each answer, in the background, the local model notes lasting facts about the person; before answering, Nora searches the facts similar to the question and reads them along. Stored in `data/memoria.db` (SQLite), with meaning-based search (`bge-m3` embeddings through Ollama, optional `sqlite-vec` index). Near-identical facts are merged. Guide in `docs/MEMORIA.md`.
- **Learning from conversation:** when you correct a pronunciation ("o certo é ôje") or ask for another way of speaking ("não repita minha pergunta"), curation stores it: pronunciations apply immediately for any voice (and for `gerar-dataset`), and preferences go along with every answer. `nora memoria pronuncias | preferencias` to see, teach by hand and forget.
- **Memory agenda:** facts with a date (exam, appointment, birthday) also go into an agenda; curation converts "amanhã", "sexta", "dia 21" and "21/11" into dates, and birthdays repeat every year. Before answering, Nora reads what is scheduled for the next 7 days (`[memoria] agenda_dias`) and for the period the question is about ("o que tenho amanhã?", "e na sexta?", "em dezembro"), which meaning-based search alone did not find. `nora memoria agenda | marcar | desmarcar`. Old facts with a date enter the agenda on their own.
- **Total memory:** besides the noted facts, every question and answer is kept in full, with its vector; before answering, Nora also reads the passages of old conversations most similar to the question (`[memoria] trocas_por_pergunta`, default 3). `importar` also stores old exchanges.
- **Memory areas:** each fact gets an area (health, work, studies...). Curation receives the existing areas, reuses the one that fits and creates a new one when the subject is new; "Saude" and "saúde" count as the same. `nora memoria areas` and `listar --area saúde`; `lembrar --area`. Old databases get the column on their own.
- `nora memoria listar | buscar | lembrar | esquecer | importar`. `listar` shows 20 per page (`--pagina`, `--contendo`, `--todos`). `importar` extracts facts from the old conversations in `data/historico/` and resumes where it stopped.
- Config `[memoria]` (`ativa`, `modelo_embeddings`, `curadoria`, `fatos_por_pergunta`, `similaridade_minima`) and the `.[memoria]` install extra.
- **Typing instead of speaking** (accessibility): `nora conversar --voz` (keyboard only, spoken answer) and `nora ouvir` accepting typed text at any time, without needing her name.
- `[voz] realce_pergunta` (`duplo` "??", `invertido` "¿...?", `exclamado` "?!") rewrites questions for voices that do not raise the intonation on "?"; `nora voz comparar "Tudo bem?"` produces the sentence in each style to choose by ear.
- A question always closes the voice request (the "?" stays at the end, where the intonation rises), even when sentences are joined.
- `[voz.piper] velocidade` (0.5 to 2.0), `variacao` and `variacao_ritmo` (naturalness: less robotic and less monotone) and `[audio] silencio_inicial_ms`: a little silence before each utterance, for headsets and sound cards that cut the beginning (the "Oi" came out swallowed).
- `[voz.pronuncias]`: words rewritten only in speech (e.g. `"amanhã" = "amanhãn"`), for any voice engine.
- A training sentence list with 204 sentences, including 46 questions, almost 50 with nasal sounds (ã, ão, õe) and 50 greetings and short replies ("Oi!", "Tá bom.", "Tchau, até amanhã!"), which the voice trained without them spoke choppily.
- The training set is converted to 22,050 Hz with frequency cutoff (FFT, numpy), without muffling or hissing; it used to be a simple interpolation.
- `docs/LICENCAS.md`: what is MIT (the code) and the license of each dependency, program, model, voice and service Nora uses, checked at the source; a test fails if a `pyproject.toml` dependency is not listed.
- `nora voz conferir-dataset --nome X [--descartar]`: Whisper listens to each sentence of the training set and compares it with the text; the audio is measured (pace, silences, pauses, volume, distortion). Each sentence becomes "boa" (good), "conferir" (check) or "ruim" (bad), with a `conferencia.csv` spreadsheet; `--descartar` removes the bad ones from the set and `gerar-dataset` does not redo them; `--tirar 0079 0088` removes sentences picked by ear.
- **Piper training notebook on Kaggle** (`scripts/treinar_piper_kaggle.ipynb`): 30 h of free GPU per week and background training (up to 12 h, with the PC off); stops before the limit, exports the voice and a test sentence, and resumes a previous training.
- **Piper training notebook on Colab** (`scripts/treinar_piper_colab.ipynb`): checks the set, fine-tunes from a Piper pt-BR voice (piper1-gpl, downloaded in Colab), saves progress to Google Drive (every 5 minutes, with an on-screen notice) to continue if Colab disconnects, stops when there is no GPU, exports the `.onnx` and plays a test sentence. Step by step in `docs/TREINAR_VOZ.md`.
- `nora voz gerar-dataset`: speaks many sentences with the main voice (e.g. the ComfyUI flow) and saves them in Piper's training format (`wavs/` mono 22,050 Hz + `metadata.csv`), resuming where it stopped; accepts a sentence list or running text (`--texto`). Initial list in `recursos/frases_pt.txt` and guide in `docs/TREINAR_VOZ.md` (ComfyUI → set → Colab training → Piper in Nora).
- Sentences already waiting go together in a single voice request (up to 400 characters): with slow voices like ComfyUI, there are fewer requests and fewer pauses between sentences.
- **Voice through ComfyUI** (`[voz] motor = "comfyui"`): Nora sends each sentence to your own ComfyUI flow (exported with "Export (API)", with `{{texto}}` in the text node), waits on the local API and plays the generated audio (WAV, FLAC or MP3, converted with `soundfile`). `config/voz_comfyui.json` stays out of Git. Instead of `{{texto}}`, you can point to the node and field of the sentence in `[voz.comfyui] campo` (e.g. `"12.text"`); if wrong, Nora lists the flow's text nodes and fields.
- `nora voz salvar "texto" [--pasta] [--nome] [--ouvir]`: Nora speaks the text with the configured voice and saves it as .wav (default: `data/audios/`).
- **Voice lab:** `nora voz listar` and `nora voz testar "pf_dora:0.7 + af_heart:0.3"` mix Kokoro voices to create a new voice, free and on the PC; the recipe goes in `[voz.kokoro] voz`.
- **Voice priority** (`[audio] prioridade`, default `true`; `volume_outros`, default 0.2): on Windows, while Nora speaks, the other programs get quieter and then come back (pycaw).
- Curation also notes pets and remarkable events, with the date (before, only lasting facts: the scare with the dog was left out).
- Nora shows what she noted in memory (`[memória] anotei: ...`) and knows she has memory: with no memory of the subject, she says she does not remember, instead of saying she has no memory.
- `nora --verificar` checks the embeddings model; `--medir` shows how many facts were used in each answer.

### Fixed

- If the sound output chosen in `[audio] alto_falante` does not open (gone, changed number, or busy with another program), Nora plays on the default output and warns, instead of going silent.
- 0.1.0 CHANGELOG: activation accepts "Nora", "Norah" and "Nóra" (not "Ela").

## [0.1.0] - 2026-10-30

**Voice conversation.** Nora wakes up on her name, listens, thinks on the local model (Qwen 3.5 9B on the RX 9060 XT) and answers out loud, sentence by sentence. Stage criterion met: in the test with a Bluetooth headset and the ElevenLabs voice, the voice started between 1.4 and 2.4 s after the end of speech (transcription ~0.7 s on the CPU; first sentence ~0.9 to 1.5 s), not counting the 0.7 s pause that ends the utterance.

### Changed

- **The project and the assistant are now called Nora** (formerly "Ella"): package `nora`, command `nora`, default config `config/nora.toml`, variable `NORA_CONFIG`. The name "Ella" ("Élha") was transcribed as "Elia", "Ilha" or "ele" and the wake word almost never worked.

### Fixed

- Sound is played in callback mode (handing audio over in pieces), which works on all Windows audio APIs. The previous mode does not exist on WDM-KS, the only API that shows the call-mode output of Bluetooth headsets ("Blocking API not supported yet").
- Connection errors show the real reason (e.g. timeout, no internet); for internet services, the hint is to check the connection instead of "Ele está aberto?".
- `nora ouvir` pauses the microphone while Nora speaks (`[escuta] pausar_microfone`, default `true`; with a Bluetooth headset, use `false` and the headset's "Headset" output). With a Bluetooth headset, the open microphone puts the headset in call mode and her voice did not come out of the headset.

### Added

- Fallback voice (`[voz] reserva`, default `kokoro`): if the main voice fails (e.g. ElevenLabs without internet), Nora speaks with the fallback and warns.
- `nora conversar`: typed conversation with the local model, with the answer appearing as it is generated (part 1 of v0.1.0). `--medir` shows the time to the first word and the speed.
- Persona: system prompt built from the config (humor, formality, short answers, date and time, user name), with rules for speaking aloud (no markdown or emojis).
- `nora conversar` loads the model into memory on start, so the first question does not pay the ~18 s load.
- `nora falar`: voice conversation with Enter to speak (part 2 of v0.1.0). Ear through whisper-server (whisper.cpp), voice through Piper's HTTP server, each as a separate program. The answer is spoken sentence by sentence while the model is still writing. `--medir` shows the transcription time, the first sentence and until speech starts.
- Scripts `instalar_voz_windows.ps1` and `iniciar_voz_windows.ps1`, and guide in `docs/VOZ.md`.
- Config `[ouvido]` and `url` in `[voz]`; default voice `pt_BR-faber-medium` (personal use, downloaded separately).
- `nora --verificar` also checks whisper-server and Piper.
- Voice configurable in `[voz] motor`: **`kokoro`** (new default, female pt-BR voice `pf_dora`, local), `piper` or **`elevenlabs`** (cloud, key in `ELEVENLABS_API_KEY`, voice in `[voz.elevenlabs] voz_id`).
- `nora servidor-kokoro`: local voice server with Kokoro-82M, in the same format as Piper (`POST /synthesize`). Install extra `.[kokoro]`.
- Voice scripts install Kokoro and start the chosen voice (`-Voz kokoro|piper|nenhuma`).
- `nora ouvir`: hands-free conversation (part 3 of v0.1.0). Silero VAD (MIT, downloaded from PyPI the first time) detects the start and end of speech; the utterance becomes a question when it starts with the wake word ("Nora", accepting "Norah" and "Nóra"); after answering, you can continue for `janela_s` seconds without saying the name; "tchau" ends it. Config `[escuta]` (`limiar`, `silencio_ms`, `janela_s`).
- Name pronunciation: `[assistente] pronuncia` only changes how the voice says the name (the screen keeps showing the name).
- The ear sends Whisper a hint with the assistant's name ("Conversa com a assistente Nora."), so it writes "Nora" the right way.
- `nora ouvir --gravar-falas` saves each heard utterance in `data/falas/`, for diagnosis. The detector keeps 0.5 s before the start of speech, so the first syllable is not cut.
- More objective persona: no repeating the question, no opening compliments, no inventing facts about the person and no ending every answer with a question.
- Config `[modelos.local] temperatura` (default 0.6), sent to Ollama.
- `nora audio`: lists microphones and speakers, records a few seconds and plays them back. Config `[audio]` to choose the devices.

### Fixed

- The microphone now records at the rate it accepts (e.g. 48 kHz) and converts to 16 kHz, instead of requiring 16 kHz (it caused `MME error 11` on Windows). Microphone errors become a clear message instead of bringing the program down.
- If the microphone does not open, Nora tries the same microphone through the other Windows audio APIs (WASAPI, DirectSound, WDM-KS) and in stereo, converting to mono.
- The microphone also tries other rates (48, 44.1, 16, 32, 22.05 and 8 kHz): Bluetooth headsets announce 44.1 kHz, but their microphone only opens at 16 or 8 kHz. If nothing opens, the error lists each attempt. On WASAPI, it asks Windows to convert the format (`auto_convert`); and it also finds the WDM-KS version of Bluetooth headsets, which has another name. Testing each option includes starting to record: a microphone that opens but does not record (e.g. "dispositivo não conectado") moves to the next option instead of bringing the program down.
- Whisper sound descriptions (e.g. `[MÚSICA DE FUNDO]`, `(risos)`) no longer become questions for Nora.
- The voice requests speech from Piper at `POST /synthesize`, the address of the current piper-tts HTTP server (`POST /` used to give error 405).
- Raw history: each question and answer is recorded in `data/historico/AAAA-MM-DD.jsonl`, outside Git.

## [0.0.1] - 2026-10-30

### Added

- `pensar` option in `[modelos.local]` to turn the local model's "thinking" mode on or off (off by default).
- Results of the first GPU test in `docs/TESTE_GPU.md`.

### Changed

- `scripts/teste_gpu_windows.ps1` measures through the Ollama API: total time, load and speed, with and without thinking mode, without the terminal animation characters in the report.

## [0.0.0] - 2026-10-30

### Added

- Repository structure: Python core in `src/nora/`, folders `hud/`, `mcp_servers/`, `scripts/`, `docs/`.
- TOML config (`config/nora.toml`) with name, persona (humor and formality), voice and models; personal override through `config/local.toml` and secrets through `.env`, both outside Git.
- `nora` command (greeting) and `nora --verificar` (shows the config and checks Ollama and the API key).
- Script `scripts/teste_gpu_windows.ps1` to test Ollama on the AMD GPU, preparing v0.1.0.
- Tests (pytest), lint (ruff) and CI on GitHub Actions for Windows and Linux.
- Documentation: goal, mind map (Mermaid and Obsidian Canvas), reference study, Obsidian guide, `CLAUDE.md`.
- MIT license.
