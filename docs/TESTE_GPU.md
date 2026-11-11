# GPU test (preparing v0.1.0)

Before building the voice conversation, we need to know whether the **RX 9060 XT** accelerates the models on Windows. This test runs **on your PC**.

## 1. Ollama (the local brain)

1. Install Ollama: https://ollama.com/download (latest version).
2. Open PowerShell in the repository folder and run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\teste_gpu_windows.ps1
   ```

   The first time it downloads the `qwen3.5:9b` model (~7.6 GB). To test another model: `-Modelo gemma4:12b`. If the model is already downloaded: `-PularDownload`.

3. Send me the report saved in `data\teste-gpu-<date>.txt` (or a screenshot of the end).

**How to read the result:**

| Line | Good sign |
|---|---|
| `PROCESSOR` (in `ollama ps`) | `100% GPU` |
| `eval rate` | above ~30 tokens/s |
| `load duration` | a few seconds the first time; almost zero afterwards |

### If it runs on the CPU

The RX 9060 XT is a new card (RDNA 4), and support depends on the Ollama and driver versions. In this order:

1. Update the AMD Adrenalin driver and Ollama, restart the PC and run the test again.
2. Turn on Ollama's Vulkan mode: close Ollama (icon near the clock → Quit), run `setx OLLAMA_VULKAN 1` in PowerShell, open Ollama again and repeat the test.
3. If it still does not use the GPU, send me the report: the alternatives are LM Studio (Vulkan backend) or plan B with Linux.

## Results

### 29/10/2026: RX 9060 XT, Windows, Ollama 0.40.13, `qwen3.5:9b`

| Measure | Result |
|---|---|
| Processor | **100% GPU** (5.6 GB in VRAM, context 4096) |
| Generation speed | **46.8 tokens/s** |
| Prompt reading | 345.6 tokens/s |
| Model load (first time) | 17.6 s |
| Total time, **with** thinking mode | 23.8 s, including the load |

**Conclusions:**

- The AMD GPU works on Windows with Ollama, without extra configuration. ✅
- The speed clears the ~30 tokens/s target comfortably.
- Qwen 3.5's **thinking mode** writes a long reasoning before answering, even on simple questions. For voice it stays **off** (`pensar = false` in the config); for hard tasks, the router sends the question to the cloud (see [CEREBRO.md](CEREBRO.md)).
- The ~18 s load only happens when the model is not in memory: `keep_alive` keeps it loaded between utterances.

### 30/10/2026: same PC, script measuring through the API

| Test | Total time | Speed | Tokens generated |
|---|---|---|---|
| Warm-up (loads the model) | 18.07 s (17.83 s load) | 52.9 tokens/s | 8 |
| **Without thinking mode** (model already loaded) | **0.21 s** | 52.3 tokens/s | 8 |
| With thinking mode | 5.24 s | 47.0 tokens/s | 244 (877 characters of reasoning) |

**Conclusion:** with the model loaded and thinking mode off, the local brain answers a short sentence in **0.21 s**. That leaves almost all of the < 1 s budget for listening (STT) and speaking (TTS). Thinking mode costs **25 times more time** on the same question. **Local brain approved for v0.1.0.** ✅

## 2. whisper.cpp (transcription)

Left for the start of v0.1.0, together with the voice code: we will compile or download whisper.cpp with Vulkan and measure how long it takes to transcribe a few seconds of speech. The instructions come here at that stage.
