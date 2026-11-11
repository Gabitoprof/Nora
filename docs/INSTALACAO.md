# Installing Nora on Windows

This guide is for whoever is going to **use** Nora. To develop, use the repository (see the README).

There are two parts:
1. the **Nora installer** (`Nora-<version>-instalador.exe`), with the program and the HUD;
2. the **Nora dependency pack**: the programs she uses that do not come inside her, because they are large, have their own licenses and update themselves. The installer offers to install this pack at the end.

## Before you start

- Windows 10 or 11, 64-bit.
- Internet, for the dependency pack: about **8 GB** of download (the conversation model is most of it).
- For Nora's voice: an [ElevenLabs](https://elevenlabs.io) account with an API key. The local voices (Kokoro and Piper) use GPL programs and do **not** come in the installer.
- Graphics card: Nora was made for the AMD RX 9060 XT 16 GB, but Ollama uses whatever card you have, or the CPU, more slowly.

## 1. Install Nora

1. Run `Nora-<version>-instalador.exe`. It does not need admin: it goes into your user folder.
2. **Windows will warn** "Windows protected your PC", because the installer has no digital signature yet. Click **More info** and then **Run anyway**. If the antivirus asks, allow it: new unsigned programs are usually scanned the first time.
3. Leave **"Instalar agora o pacote de dependências"** (install the dependency pack now) checked and click Install.

## 2. The dependency pack (automatic)

It opens a PowerShell window and installs, in order:

| Step | What it installs | Size |
|---|---|---|
| 1 | Visual C++ Redistributable (x64), if missing | ~25 MB |
| 2 | **Ollama** (local brain), through `winget` | ~1 GB |
| 3 | Ollama models: `qwen3.5:9b` (conversation) and `bge-m3` (memory) | ~7 GB |
| 4 | **whisper.cpp** (ear), from the official site | ~10 MB |
| 5 | Whisper model (`small`) | ~470 MB |

At the end a **summary** shows, with `ok` or `FALHOU` (failed) for each step. The full log is in `%APPDATA%\Nora\instalacao\`.

- **You can run it again** as many times as needed (Start menu > Nora > **Instalar dependências da Nora**): what is already done is skipped.
- **"O winget não está neste Windows"** (winget is not on this Windows): install **App Installer** from the Microsoft Store and run it again.
- **More accurate ear** (fast or unclear speech): run the pack with another model, in a PowerShell opened in Nora's folder (`%LOCALAPPDATA%\Programs\Nora`):

  ```powershell
  powershell -ExecutionPolicy Bypass -File instalar_dependencias.ps1 -ModeloWhisper large-v3-turbo-q5_0
  ```

## 3. Configure (once)

Open **Start menu > Nora > Pasta da Nora (config e memória)**. It is the `%APPDATA%\Nora` folder, where everything of yours lives:

| File or folder | What it is |
|---|---|
| `.env` | Your keys. Put `ELEVENLABS_API_KEY=` and, if you want the cloud for hard questions, `OPENAI_API_KEY=` and/or `ANTHROPIC_API_KEY=` |
| `config\local.toml` | Your config: your name and the `voz_id` of the ElevenLabs voice (Voices > ... > Copy voice ID) |
| `data\` | Memory, history and reports. Never leaves your PC |
| `models\`, `ferramentas\` | Models and programs downloaded by the dependency pack |

Open both files in Notepad: they already come with comments explaining each line.

## 4. Use

- **Start menu > Nora:** starts Ollama and the ear if they are not running yet, opens the HUD in the browser and starts continuous listening. Say "Nora, ..." and speak.
- **Start menu > Nora > Nora - verificar instalação:** shows the version, the commit and whether each part (Ollama, ear, voice, keys) is ok. Use this first if something does not work.

## Uninstall

Settings > Apps > **Nora** > Uninstall. The `%APPDATA%\Nora` folder (config, keys and memory) **stays**, so you do not lose anything. To delete everything, delete that folder too. Ollama and its models are uninstalled through Ollama itself.

## Building the installer (for developers)

On every push to `main`, to `integracao/...` or to a `v*` tag, GitHub builds the installer and the `.zip`: **Actions > Empacotar > the run > Artifacts > nora-windows** (kept 14 days). To build it on your PC: `scripts\empacotar_windows.ps1`, with the instructions at the top of the file.
