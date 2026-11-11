# Nora's voice

Nora talks by voice using local programs, each in its own process, and talks to them over the local network:

| Role | Program | Port | License |
|---|---|---|---|
| Brain | Ollama (`qwen3.5:9b`) | 11434 | MIT |
| Ear | whisper.cpp (`whisper-server`) | 8178 | MIT |
| Voice (default) | Kokoro (`nora servidor-kokoro`) | 5001 | Apache-2.0 weights; uses phonemizer/espeak-ng (GPL-3.0) |
| Voice (optional) | Piper (`piper.http_server`) | 5000 | GPL-3.0 |
| Voice (optional, cloud) | ElevenLabs | — | paid service |

Splitting into processes keeps Nora's core free of third-party licenses, leaves each piece swappable and prepares the distributed mode (v0.8.0).

## Voice engines

Choose in `[voz] motor` (in `config/local.toml`, so it applies only on your machine):

| Engine | Voice | Where it runs | Cost | For whom |
|---|---|---|---|---|
| **`kokoro`** (default) | `pf_dora` (female pt-BR); also `pm_alex`, `pm_santa` | your PC (CPU) | free | whoever downloads the project and wants to try it |
| `piper` | `pt_BR-faber-medium` (male) or a voice you trained ([TREINAR_VOZ.md](TREINAR_VOZ.md)) | your PC | free | your own lightweight voice; personal use (non-commercial bases) |
| `elevenlabs` | the one you pick or create | cloud | pay per use | the most natural voice; default `eleven_v4_turbo`, in real time ([ElevenLabs v4](#elevenlabs-v4-real-time-dialogue)) |
| `comfyui` | the one you build in a ComfyUI flow | your PC | free | your own voices, created or cloned with permission |

## Install (once)

In the repository folder, with the environment activated (`.venv\Scripts\activate`) and **Python 3.12 or 3.13**:

```powershell
git pull
```

```powershell
pip install -e ".[dev,voz]"
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1
```

The script downloads (all outside Git, in `ferramentas\` and `models\`):

- the official CPU **whisper.cpp** and the **`ggml-small.bin`** model (~470 MB);
- **Kokoro** (`pip install -e .[kokoro]`), the model and the voices (~330 MB) in `models\kokoro\`;
- **Piper** and the `pt_BR-faber-medium` voice. To skip: `-SemPiper`.

## Use

1. Start the ear and the voice (they open windows; leave them open):

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
   ```

   The default is Kokoro. With `-Voz piper` it starts Piper; with `-Voz nenhuma` (for ElevenLabs) only the ear. The engine chosen in the script must be the same as `[voz] motor`.

2. Test the microphone and the speaker (lists the devices, records 3 seconds and plays them back):

   ```powershell
   nora audio
   ```

   To use another microphone or speaker, put the number or name from the list in `config\local.toml`:

   ```toml
   [audio]
   microfone = "23"
   ```

3. Check that everything is up:

   ```powershell
   nora --verificar
   ```

4. Talk:

   ```powershell
   nora falar --medir
   ```

   Press **Enter**, speak, press **Enter** again. You can also type the question. `sair` exits.

With `--medir`, each answer shows three times, counted from the moment you stop recording:

| Time | What it is | Target |
|---|---|---|
| transcrição (transcription) | Whisper turning your speech into text | as low as possible |
| primeira frase (first sentence) | the first sentence of the answer being ready | |
| **começou a falar (started speaking)** | Nora's sound starting to come out | **< 2 s** (MVP), < 1 s (final) |

## Typing instead of speaking

For people who have difficulty speaking, or in places where you cannot speak, Nora accepts **typed text** and answers **out loud**:

| Command | You | She |
|---|---|---|
| `nora conversar --voz` | only type (no microphone) | answers speaking and writing |
| `nora ouvir` | say "Nora, ..." **or** type at any time | answers speaking |
| `nora falar` | press Enter and speak, **or** type the question | answers speaking |
| `nora conversar` | type | answers only in writing |

In `nora ouvir`, what you type does not need her name. Typing `sair` exits.

## Hands-free (`nora ouvir`)

Instead of pressing Enter, Nora listens all the time and answers when the sentence **starts with her name**:

```powershell
nora ouvir --medir
```

- **"Nora, que horas são?"** → she answers.
- After the answer, for **8 seconds** you can continue **without saying the name** ("E amanhã?").
- **"Nora"** alone → she says "Oi, pode falar." and waits.
- **"Tchau"**, **"é só isso"** → she says goodbye and goes back to waiting for the name.
- **Ctrl+C** exits.

How it works: **Silero VAD** (MIT license, downloaded automatically from PyPI the first time to `models\silero_vad.onnx`) notices when you start and stop speaking; each utterance goes to Whisper; if the text starts with the wake word, it becomes a question.

Settings in `config\local.toml`:

```toml
[assistente]
palavra_de_ativacao = "Nora"   # or "Oi Nora", if she wakes up by accident

[escuta]
limiar = 0.5        # raise it (e.g. 0.6) if noise becomes speech; lower it if she does not notice you
silencio_ms = 700   # pause that ends your utterance; lower answers faster, but cuts pauses
janela_s = 8.0      # seconds to continue without saying the name
```

Limits of this version:

- **Why "Nora":** the old name, "Ella" (pronounced "Élha"), turned into "Elia", "Ilha" or "ele" in transcription, and she almost never woke up. Whisper recognizes "Nora" well and it almost never starts a sentence by chance. Activation accepts "Nora", "Norah" and "Nóra". If she wakes up by accident, use `palavra_de_ativacao = "Oi Nora"`. To change how the voice says the name, use `[assistente] pronuncia`. A real wake word (openWakeWord trained with her name, running before Whisper) comes later.
- **Every utterance goes through Whisper**, even the ones not for her. With TV or conversation in the room, the CPU works harder. `--mostrar-ignoradas` shows what she heard and ignored.
- **While she speaks, she does not listen** (the microphone is paused), because there is no echo cancellation yet. With a **Bluetooth headset** this is also needed: with the microphone open, the headset stays in call mode and the normal sound output goes silent. When the microphone reopens, the headset may take a moment to switch modes. Interrupting by speaking over her (barge-in) comes later; with headphones this gets easier.

## Music playing at the same time (voice priority)

When another program is playing sound (music, video), Nora speaks over it like this:

```toml
[audio]
prioridade = true     # while she speaks, the other programs get quieter and then come back
volume_outros = 0.2   # how much of their volume remains (0 = muted, 1 = unchanged)
```

With `prioridade = false`, she speaks mixed with everything else, at normal volume. For written-only answers, use `nora conversar`.

Works on Windows (the `pycaw` library, installed with `.[voz]`). If the output chosen in `alto_falante` does not open (the device is gone, changed number or is busy with another program), Nora uses the Windows default output and warns with `[som] ...`.

## Bluetooth headset (microphone and sound on the same headset)

Bluetooth headsets have two modes: **music** (good sound, no microphone) and **call** (microphone on, phone-quality sound). When the microphone opens, the headset goes into call mode and the "Fones de ouvido" (headphones) output goes **silent**; each mode switch takes about 1 second of silence.

So the sound does not disappear, keep the headset always in call mode:

1. Run `nora audio` and look, among the **speakers**, for the headset's "Headset" (on Windows it usually shows up as `Headset (@System32\drivers\bthhfenum.sys...(HEADSET NAME))`, on the WDM-KS API). Note the number.
2. In `config\local.toml`:

   ```toml
   [audio]
   alto_falante = "17"   # the number of the headset's "Headset"

   [escuta]
   pausar_microfone = false
   ```

The numbers change when you connect or disconnect devices; check with `nora audio`. With a separate microphone (or a speaker), go back to `alto_falante = ""` and `pausar_microfone = true`.

## Voice lab (create your own voice, for free)

Each Kokoro voice is a numeric "DNA", and you can **mix voices** to create a new one, on your PC and for free:

```powershell
nora voz listar
```

```powershell
nora voz testar "pf_dora:0.7 + af_heart:0.3" --velocidade 0.95
```

She speaks a test sentence (or yours, with `--frase "..."`) and saves the sample in `data\vozes\`. When you like it, put the recipe in `config\local.toml`:

```toml
[voz]
motor = "kokoro"

[voz.kokoro]
voz = "pf_dora:0.7 + af_heart:0.3"
velocidade = 0.95
```

Tips: keep `pf_dora` (Brazilian Portuguese) with the **largest weight**, for the accent and pronunciation; mix small portions of other voices to change the timbre (deeper, softer, brighter). The weights do not need to add up to 1; Nora adjusts them.

## Switching the voice by speaking

In the voice modes (`nora ouvir`, `nora falar`, `nora conversar --voz`), you can switch the voice in the middle of the conversation, without touching the config:

| Say | What happens |
|---|---|
| "troque para a voz do Piper" / "usa o Piper" | starts speaking with Piper (whichever voice is open on the server, like your trained one) |
| "volta pro ElevenLabs" | goes back to ElevenLabs |
| "usa a voz do Kokoro" | switches to Kokoro |
| "volta para a voz normal" | goes back to the `[voz] motor` voice |
| "qual voz você está usando?" | she says which one is speaking |

- The confirmation ("Pronto, agora falo com a voz do Piper.") already comes out in the new voice, so you hear right away how it sounds.
- If the requested voice does not respond (Piper window closed, missing ElevenLabs key), she says why and **keeps the previous voice**.
- The fallback still applies: if the chosen voice fails mid-conversation, `[voz] reserva` takes over. If you chose exactly the voice that was the fallback, the config's main voice becomes the fallback.
- The switch lasts until Nora is closed. To change it for good, use `[voz] motor` in `config/local.toml`.
- The voice server must be open (`iniciar_voz_windows.ps1` opens Kokoro or Piper; ElevenLabs is in the cloud). The script opens one local voice at a time: with ElevenLabs as the main voice, open with `-Voz piper` to be able to switch to Piper.
- In `nora conversar` (text only) there is no voice: she warns instead of pretending to switch.
- She only switches on a clear request (a verb such as usar, trocar, mudar, voltar, or "fala com a voz do..."). Questions and comparisons ("o Piper é melhor que o Kokoro?", "usa o Kokoro ou o Piper?") go to the brain, without changing the voice. With two engines in the sentence, the one after "para" wins: "troca do Kokoro para o Piper".

## Saving a Nora utterance as .wav

Nora speaks a text with the configured voice (ElevenLabs, Kokoro, a mix...) and saves the audio:

```powershell
nora voz salvar "Bom dia! Hoje é dia de prova, boa sorte." --pasta "C:\Users\voce\Music\Nora" --nome bom-dia --ouvir
```

Without `--pasta`, it saves to `data\audios\`; without `--nome`, it uses the date and the start of the text. With `--ouvir`, it also plays it. (Asking for this in conversation, without a command, arrives with the v0.5.0 tools.)

## Using a voice made in ComfyUI

Any voice you build in ComfyUI (cloned from a sample of yours, or another voice node) can be Nora's voice. She sends each sentence to your flow, through ComfyUI's local API, and plays the generated audio.

1. **Prepare the flow in ComfyUI:** in the node where the sentence goes, write **`{{texto}}`** in place of the text (or, without touching the flow, give the node and field in `[voz.comfyui] campo = "12.text"`: the number is the node ID in the exported JSON; if wrong, Nora lists the flow's text nodes and fields). The flow must end in a node that saves the audio (e.g. **Save Audio**). Test it once in ComfyUI itself.
2. **Export in the API format:** menu **Workflow → Export (API)** (if it does not show up, turn on **Enable dev mode options** in the ComfyUI settings). The normal format (with `widgets_values`) does not work: Nora warns if it is that one. Save the file as `B:\Nora\config\voz_comfyui.json` (it stays out of Git).
3. **In `config\local.toml`:**

   ```toml
   [voz]
   motor = "comfyui"
   reserva = "kokoro"   # if ComfyUI is closed or slow, she speaks with Kokoro

   [voz.comfyui]
   url = "http://127.0.0.1:8188"   # the address ComfyUI shows when it opens
   espera_s = 120.0
   ```

4. **Leave ComfyUI open**, run `nora --verificar` (it should show `ComfyUI ok`) and test: `nora voz salvar "Oi! Esta é a minha voz nova." --ouvir`.

The audio can come out as WAV, FLAC or MP3: Nora converts it (it needs `soundfile`, which comes with `.[voz]`). Depending on the model and the GPU, ComfyUI takes a few seconds per sentence: the conversation is slower than with ElevenLabs or Kokoro. Use only your own voices or voices of people who authorized it, and check the license of the voice model used in the flow.

> To have the ComfyUI voice **fast and light** day to day, generate a set of sentences with it and train a Piper: see [TREINAR_VOZ.md](TREINAR_VOZ.md).

## Questions that sound like statements

Some voice models do not raise the intonation on "?". You can test ways of writing the question that help the model notice:

```powershell
nora voz comparar "Amanhã você vai à academia?" --ouvir
```

She produces the same sentence plain, `duplo` ("??"), `invertido` ("¿...?") and `exclamado` ("?!"), saves them to `data\vozes\pergunta_*.wav` and plays each one. Pick the best and put it in `config\local.toml`:

```toml
[voz]
realce_pergunta = "invertido"
```

It also applies to `nora voz gerar-dataset`, so the training set comes out with the questions in the chosen style.

## Start of speech cut off or too fast

If the first word comes out swallowed ("Oi" too fast), try in this order, in `config/local.toml`:

1. **Silence before speech.** Bluetooth headsets and some sound cards "wake up" after the sound has started and cut the beginning:

   ```toml
   [audio]
   silencio_inicial_ms = 200
   ```

   To know whether that is it: `nora voz salvar "Oi! Tudo bem?"` and open the file in `data\audios\` in any player. If the "Oi" is normal there, the cut is in the sound output, and the silence fixes it.
2. **Piper speed** (applies to all speech):

   ```toml
   [voz.piper]
   velocidade = 0.9   # 1.0 normal; lower = slower
   ```

## Voice changing tone or pausing between sentences

Each voice request is made separately, while the model is still writing. A short first sentence ("Hahaha, esse atchim!") became a short audio: it ended before the next sentence was ready (the pause), and the voice started the next one without knowing how the previous one sounded (the tone change). This weighs more on ElevenLabs v3, the most expressive and the slowest.

Since v0.3.1:

- **A short sentence goes together with the next one.** A request with fewer than `juntar_curta` characters waits up to 1.5 s for the next sentence and goes in a single request. If the answer ends, it goes immediately. A question never waits: the "?" at the end guarantees the intonation.
- **ElevenLabs with a fixed seed.** The same `semente` in every request keeps the voice more consistent from one sentence to the next.
- **Streaming ElevenLabs.** Nora requests the audio from the streaming endpoint and starts playing when the first part arrives (~150 ms of audio), without waiting for the whole sentence. Requests still go one at a time. If the internet drops mid-sentence, she plays what arrived and warns `[erro na voz] A voz parou no meio da frase`.
- **ElevenLabs with the previous sentence.** The request carries the previous sentence (`previous_text`), so the intonation continues where it stopped. It applies for up to 1 minute after the last utterance. If the model rejects the field, Nora speaks without it and stops sending it until she closes.

```toml
[voz]
juntar_curta = 60        # 0 = each sentence goes alone, as before

[voz.elevenlabs]
semente = 42             # -1 = the API picks a random one per request
continuidade = true      # false = do not send the previous sentence
```

If the first utterance still takes a while to start, lower `juntar_curta` (e.g. 30). If the tone still changes, change the `semente`: each number gives a slightly different reading of the same voice.

## Robotic or monotone Piper voice

Piper has two naturalness controls, in `config/local.toml`:

```toml
[voz.piper]
variacao = 0.75        # sound variation (model default: ~0.667). Higher = more expressive
variacao_ritmo = 1.0   # rhythm variation (default: ~0.8). Higher = less monotone
```

Change one at a time, in small steps, and compare with `nora voz salvar "frase" --ouvir`. If it starts hissing, slurring or sounding odd, go down. `0` returns to the model default.

If the voice is metallic or hissy (not only monotone), the setting does not fix it: it is undertrained. Train more epochs or with more sentences (see [TREINAR_VOZ.md](TREINAR_VOZ.md)).

## Emotion in the voice

Nora picks the emotion of each sentence on her own, looking at what you said and how, what she remembers about you, the agenda and the time of day. You do not mark anything.

| Engine | What happens |
|---|---|
| ElevenLabs **v3** (`modelo = "eleven_v3"`) | It becomes an audio tag: she laughs, sighs, whispers, speaks excited or sad. More expressive, but starts speaking a little slower |
| ElevenLabs Flash, Turbo or Multilingual | These models do not understand the tags: emotion becomes a per-sentence tone adjustment (more or less stable, more or less emphasis, a little faster or slower) |
| Piper, Kokoro, ComfyUI | The mark is removed; the voice speaks normally (also when it comes in as the fallback) |

Settings in `config/local.toml`:

```toml
[emocao]
ativa = true
intensidade = 0.5          # 0 = no emotion, 1 = very expressive
reacoes_por_resposta = 1   # at most how many laughs or sighs per answer
```

She also learns from your reactions: if you laugh at a joke, complain about exaggeration or open up after a tender tone, curation stores it as a preference (`nora memoria preferencias`). To change it on the spot, say: "não precisa rir tanto", "pode ser mais animada".

## Fixing the pronunciation of a word

If the voice says a word badly, rewrite it as it should sound, only in speech (the screen keeps showing the original text). It works for any voice engine:

```toml
[voz.pronuncias]
"amanhã" = "amanhãn"
"PUCMG" = "puque eme gê"
```

Test with `nora voz salvar "Até amanhã!" --ouvir` and adjust until it sounds right.

## Using ElevenLabs

1. Create an account at elevenlabs.io and an API key (profile → API Keys). Set a spending limit.
2. Pick a voice from the library or create one in **Voice Design**. On the voice page, copy the **voice ID**.
3. In `.env` (outside Git):

   ```
   ELEVENLABS_API_KEY=sua_chave
   ```

4. In `config\local.toml` (outside Git):

   ```toml
   [voz]
   motor = "elevenlabs"

   [voz.elevenlabs]
   voz_id = "cole_o_voice_id_aqui"
   ```

5. Start the ear and Kokoro, which serves as the **fallback voice** when ElevenLabs fails (e.g. no internet): `iniciar_voz_windows.ps1 -Voz kokoro`. Without a fallback, use `-Voz nenhuma` and `reserva = ""` in `[voz]`.
6. Run `nora --verificar` (it should show `ElevenLabs configurado` and `Kokoro (reserva) ok`) and `nora falar --medir`.

The default model is `eleven_v4_turbo`, through real-time dialogue (next section). If the dialogue fails, Nora speaks with `eleven_flash_v2_5` (the `modelo_reserva`), the fastest ElevenLabs model, through the usual path: one request per sentence, with the language fixed to Portuguese. Both ways consume credits. To keep the tone from changing between sentences on flash, see [Voice changing tone or pausing between sentences](#voice-changing-tone-or-pausing-between-sentences).

> If your `config\local.toml` has an old `modelo` (e.g. `eleven_v3`), that is the one used. To use v4, change it to `modelo = "eleven_v4_turbo"` or delete the line.

## ElevenLabs v4 (real-time dialogue)

v4 does not work on the regular text-to-speech (ElevenLabs answers `400 unsupported_model`): only on **Text to Dialogue**, over WebSocket (`wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input`). Nora uses it like this:

- **One connection per conversation.** It opens while the model thinks and stays open between answers (`keep_alive` every 10 s, because the server closes after 20 s without a message). It closes on its own after `manter_conexao_s` without speaking.
- **The text goes as the model writes**, sentence by sentence, on the same connection: the first of each answer with `new_turn`, and a `flush` at the end. There is no request per sentence.
- **The audio plays as it arrives**, in a single playback, with no pause between sentences.
- **Aligned words in the HUD.** ElevenLabs sends the time of each letter (`sync_alignment`); the HUD receives the words with `precisao "alinhada"`. If the alignment does not come, it estimates from the sound, as with the other voices.
- **Interrupting** (Ctrl+C) cuts the audio and closes the connection; the next answer opens a new one, with no leftover from the previous one.
- **Fallback.** If the connection does not open or ElevenLabs refuses (e.g. the model is not enabled on your account), Nora speaks the whole answer with the `modelo_reserva` over HTTP, warns `[voz reserva] ...` with the reason and tries the dialogue again after 5 minutes.
- From `voice_settings`, the dialogue only uses **stability**. The voice is the `voz_id` one, a single voice.

```toml
[voz.elevenlabs]
modelo = "eleven_v4_turbo"          # or "eleven_v4" (slower, more expressive)
modelo_reserva = "eleven_flash_v2_5"
estabilidade = 0.5                  # 0 = more varied, 1 = more stable
continuidade = true                 # false = close the connection after each answer
manter_conexao_s = 120              # time without speaking until the connection closes
```

It needs the `websockets` package (comes with `pip install -e ".[voz]"` and in `nora.exe`).

**Diagnostics.** `nora --verificar` shows the **modelo efetivo** (effective model: what will actually speak; without `websockets`, it is the fallback), the **Continuidade ElevenLabs** (`ativa`, `desativada`, `não suportada` or `erro`) and the timings of the last utterance. `nora falar --medir` shows the same for each answer:

- **primeiro áudio (first audio):** from sending the first text until the first PCM arrives;
- **tocando (playing):** from sending until the sound starts coming out;
- **silêncio entre trechos (silence between chunks):** gaps from missing network audio (sum and the largest).

The numbers also go to the log and to `data\diagnostico_voz.json`, without the conversation text and without the key.

**Measured on Gabriel's PC (06/11/2026, `eleven_v4_turbo`):** first audio in 985 ms, playing in 1555 ms, 0 ms of silence between chunks and aligned words. Nora uses only v4; no comparison with other models is planned. `eleven_flash_v2_5` is only an automatic fallback when the dialogue fails.

## Ear mishearing

When you speak fast, quietly or far from the microphone, `small` makes more mistakes. There are three adjustments, from lightest to heaviest:

1. **Vocabulary.** Names and terms it usually gets wrong go as a hint to Whisper, in `nora falar` and `nora ouvir`, together with the assistant's name:

   ```toml
   [ouvido]
   vocabulario = ["Obsidian", "Ollama", "Kokoro"]
   ```

2. **Bigger model.** `large-v3-turbo` makes far fewer mistakes than `small` on unclear speech. The `q5_0` version (~550 MB) fits well in memory. Download it once and start with it:

   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1 -ModeloWhisper large-v3-turbo-q5_0 -SemPiper
   ```

   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1 -ModeloWhisper large-v3-turbo-q5_0
   ```

   On the CPU it is slower than `small` (`small` took 0.72 s on the 9800X3D). Measure with `nora falar --medir`: if transcription goes over ~1.5 s, self-improvement will point it out. The real speed gain comes with whisper.cpp built with Vulkan (see below).

3. **Beam search.** With `-Feixe 5` in `iniciar_voz_windows.ps1`, Whisper tries 5 paths instead of 1: fewer mistakes, slower. Try it after the bigger model, if it still makes mistakes.

First of all, check the microphone: Windows input volume around 80% and the headset close to the mouth already fix a good share of the mistakes.

## Choices and pending items

- **Whisper on the CPU, for now.** The official project does not publish a ready-made Windows build with Vulkan; it must be compiled (Vulkan SDK, CMake and Visual Studio Build Tools) or would come from third parties. In the first test, `small` on the 9800X3D transcribed in 0.72 s. If it gets slow, the next steps are the `base` model (`-ModeloWhisper base` in both scripts) or compiling with Vulkan. To make fewer mistakes, the path is the opposite: `large-v3-turbo-q5_0` (see [Ear mishearing](#ear-mishearing)), which only gets really fast with Vulkan.
- **`pt_BR-faber-medium` (Piper) voice for personal use only.** It was fine-tuned from an English voice trained on a **non-commercial-only** base. It is downloaded separately and never distributed.
- **Two modes:** `nora falar` (Enter to speak, good for noisy rooms) and `nora ouvir` (hands-free).
- **No interruption yet.** Speaking over Nora (barge-in) needs echo cancellation and comes later; for now, Ctrl+C interrupts.

## If something goes wrong

- **pip installs into `...\pythoncore-3.xx\Scripts` and warns "not on PATH":** the environment was not activated. Run `.venv\Scripts\activate` (the terminal starts showing `(.venv)`) and repeat the `pip install`.
- **`pip install` fails with "conflicting dependencies" and "no matching distributions" for `onnxruntime`:** the Python is too new (it happened with 3.15). See the versions with `py -0`, install 3.13 (`py install 3.13`) and recreate the environment: `deactivate`, `Remove-Item -Recurse -Force .venv`, `py -3.13 -m venv .venv`, `.venv\Scripts\activate`, `pip install -e ".[dev,voz]"`.
- **"Access denied" when installing:** some `nora` is open (close the terminals or run `Stop-Process -Name nora -Force`).
- **"Não consegui abrir o microfone" (e.g. `MME error 11`):** Nora already tries the same microphone through the other Windows APIs. If nothing opens, check in Settings → Privacy & security → Microphone that "Let desktop apps access your microphone" is on, and run `nora audio`.
- **Nora answers `[MÚSICA DE FUNDO]` or hears nothing:** the recording was too quiet; speak closer to the microphone, after "(gravando...)" appears.
- **Kokoro, Piper or whisper-server "não respondeu" (did not respond)** in `nora --verificar`: look at the matching window opened by the start script; the error message shows up there. Send me a screenshot.
- **Piper refuses the request (405 or 404):** the version changed the address. Run `Select-String -Path .venv\Lib\site-packages\piper\http_server.py -Pattern "route"` and send me the result.
