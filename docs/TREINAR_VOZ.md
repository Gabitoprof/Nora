# Training your own voice (ComfyUI → Piper)

The idea: use **ComfyUI to create** the voice (heavy, slow, but with the quality you chose) and **Piper to speak** day to day (light, runs on the CPU, answers in under half a second and does not compete for the GPU with the brain).

```
ComfyUI (your voice)  ──►  500 to 1,000 spoken sentences  ──►  Piper training (Colab, free)  ──►  light voice in Nora
   nora voz gerar-dataset                                         .onnx file                 motor = "piper"
```

## 0. Before you start: license and rights

- **Check the license of the voice model used in ComfyUI** (on the model page): it must allow using the generated audio to train another model. Non-commercial-only models limit the use of the final voice the same way.
- The voice must be **created** (voice design) or belong to someone who **authorized** it. Do not use ElevenLabs audio for training: their terms do not allow it.
- **The trained voice is never more natural than the source.** Piper copies what it receives, accent included. Cloning models trained mostly on Chinese and English (e.g. Qwen3-TTS) speak Portuguese with a foreign accent, and the final voice inherits it. Before generating hundreds of sentences, listen carefully to about 10 from the source; for the most natural result, record a real voice (with permission).

## 1. Get the voice ready in ComfyUI

Follow [VOZ.md](VOZ.md#using-a-voice-made-in-comfyui): flow exported in API format as `config/voz_comfyui.json`, with `{{texto}}` (or `[voz.comfyui] campo`), and `[voz] motor = "comfyui"` in `config/local.toml`. Test with `nora voz salvar "teste" --ouvir`.

**Tip:** fix the seed (`seed`) in the voice node. With a fixed seed, every sentence comes out with the same voice; with a random seed, the voice may vary from one sentence to the next, and training learns an "average" voice.

## 2. Generate the training set

```powershell
nora voz gerar-dataset --nome minha_voz
```

- Uses the project's sentence list (`recursos/frases_pt.txt`, 204 varied sentences, with questions, nasal sounds and short greetings).
- To reach **500 to 1,000 sentences**, also use a **public-domain** text (e.g. a Machado de Assis book from the Domínio Público portal), which Nora splits into sentences on her own:

  ```powershell
  nora voz gerar-dataset --nome minha_voz --texto "C:\caminho\para\livro.txt" --limite 800
  ```

- Uses **only the main voice** (never the fallback), so voices are not mixed in the set.
- **You can interrupt it** (Ctrl+C, or ComfyUI closed): running it again, it resumes where it stopped.
- Result in `data\dataset_voz\minha_voz\`: the `wavs\` folder (0001.wav, 0002.wav... mono, 16-bit, 22,050 Hz) and `metadata.csv` (`0001|sentence text`), the format Piper training uses.

How long it takes: ComfyUI spends a few seconds per sentence; 800 sentences may take a few hours. Leave it running and close other heavy programs (the GPU is all ComfyUI's; Ollama does not even need to be open at this stage).

## 3. Check the set (10 minutes well spent)

Bad audio in training becomes a bad voice later. Nora helps find the bad ones: with the **whisper-server open** (the same one from `scripts\iniciar_voz_windows.ps1`), run

```powershell
nora voz conferir-dataset --nome minha_voz
```

Whisper listens to each sentence and compares it with the expected text, and the audio is measured. Each sentence gets a grade:

| Grade | When |
|---|---|
| **ruim** (bad) | words swapped, missing or extra; no speech; too short; pace far off normal (cut or dragged) |
| **conferir** (check) | some different word or numbers (Whisper writes "28" where the text says "vinte e oito"); pace slightly off; more than 1 s of silence at the start or end; long pause in the middle; low volume; clipped audio |
| **boa** (good) | nothing odd |

The result shows on screen (worst first, with what was expected and what Whisper heard) and in a spreadsheet, `conferencia.csv`, inside the set's folder (opens in Excel).

- **Listen to the "conferir" ones** and remove the bad ones: `nora voz conferir-dataset --nome minha_voz --tirar 0079 0088` (they go to `descartadas\`, leave `metadata.csv` and are not regenerated).
- **Remove the bad ones at once:** `nora voz conferir-dataset --nome minha_voz --descartar`. They go to the `descartadas\` folder, leave `metadata.csv` and `gerar-dataset` does not regenerate them (with a fixed seed, they would come out the same).
- **What it does not catch:** accent and pronunciation. Whisper understands "houje" as "hoje", so also listen to about 20 random sentences. Words that always come out wrong go into `[voz.pronuncias]` (see [VOZ.md](VOZ.md)), before generating the set.

## 4. Train on Kaggle (free, recommended)

Training needs an NVIDIA GPU. **Kaggle** lends one for free for **30 hours a week** and runs training **in the background**, for up to 12 hours, even with the browser and the PC off. The notebook is in [`scripts/treinar_piper_kaggle.ipynb`](../scripts/treinar_piper_kaggle.ipynb).

**Only once:** create an account at [kaggle.com](https://www.kaggle.com) and confirm your phone (**Settings → Phone verification**). Without it, the GPU and internet are blocked.

**Each training:**

1. **Dataset:** zip `data\dataset_voz\minha_voz` into `minha_voz.zip`. On Kaggle: **Create → New Dataset**, upload the zip (it unzips on its own) and click **Create**.
2. **Notebook:** **Create → New Notebook → File → Import Notebook** and choose `scripts\treinar_piper_kaggle.ipynb`.
3. In the right panel: **Accelerator** on **GPU P100** (or **GPU T4 x2**), **Internet** on, and in **Add Input** (**Your Datasets** tab) the dataset from step 1.
4. In cell 1, check `NOME_VOZ` and `MAX_EPOCAS` (default 1,000, about 3 to 4 hours).
5. **Save Version → Save & Run All (Commit) → Save.** You can close the page.
6. Come back after a few hours, open the saved version, go to the **Output** tab and download `pt_BR-minhavoz-medium.onnx`, `pt_BR-minhavoz-medium.onnx.json` and `teste.wav` (a test sentence).

Training stops on its own before the 12-hour limit and still exports the voice. **To train more**, run it again with the previous version's output in **Add Input** and a larger `MAX_EPOCAS`: it continues from its `last.ckpt`.

## 4b. Or on Google Colab (free)

Colab also works, but the free GPU lasts a few hours a day, and the tab must stay open.


Training needs an NVIDIA GPU; Colab lends one for free for a few hours a day. The ready notebook is in [`scripts/treinar_piper_colab.ipynb`](../scripts/treinar_piper_colab.ipynb) and uses the current Piper ([piper1-gpl](https://github.com/OHF-Voice/piper1-gpl), GPL-3.0, downloaded inside Colab, never in the repository).

1. Zip the `data\dataset_voz\minha_voz` folder (with `wavs\` and `metadata.csv`) into `minha_voz.zip` and upload it to Google Drive, in a `Nora` folder (`My Drive/Nora/minha_voz.zip`).
2. Open [Google Colab](https://colab.research.google.com), go to **File → Upload notebook** and choose `scripts\treinar_piper_colab.ipynb`.
3. **Runtime → Change runtime type → GPU (T4)**.
4. In cell 1, put the set's name (`minha_voz`) in `NOME_VOZ`. Run the cells in order.

What the notebook does:

- Checks the set (audio at 22,050 Hz, sentences without audio) and estimates the training time.
- Starts from a ready Piper pt-BR "medium" voice (`rhasspy/piper-checkpoints`) and **fine-tunes** it with your sentences, for 2,000 epochs (Piper's recipe for less than 5 h of speech).
- Every 5 minutes it saves the latest training checkpoint to `My Drive/Nora/treino_minha_voz/` and shows `[drive] salvo às HH:MM`: up to that time, the training is safe. **If Colab disconnects**, open it again and run the cells again: it continues where it stopped.
- In cell 7 it exports to `.onnx` and plays a test sentence. You can listen mid-training: stop cell 6, run 7 and then 6 again.
- In cell 8 it saves the two voice files to Drive: `pt_BR-minhavoz-medium.onnx` and `pt_BR-minhavoz-medium.onnx.json` (the name loses the "_", because Piper uses "_" and "-" to separate language, name and quality).

How long: with ~10 minutes of speech (the 154 sentences of the list), about 6 to 8 hours on the T4, usually over two or three free Colab sessions. More sentences make the voice better, but each epoch gets slower.

**License:** Piper's base voices usually derive from non-commercial-only data; the trained voice is for personal use and stays out of Git (`models/`).

## 5. Use it in Nora

1. Copy `pt_BR-minhavoz-medium.onnx` and `pt_BR-minhavoz-medium.onnx.json` to `B:\Nora\models\piper\`.
2. In `config\local.toml`:

   ```toml
   [voz]
   motor = "piper"
   reserva = "kokoro"

   [voz.piper]
   voz = "pt_BR-minhavoz-medium"
   ```

3. Start with `scripts\iniciar_voz_windows.ps1 -Voz piper -VozPiper pt_BR-minhavoz-medium` and test: `nora voz salvar "Oi! Esta é a minha voz." --ouvir`.

Done: the same voice you created in ComfyUI, now fast, local and free.
