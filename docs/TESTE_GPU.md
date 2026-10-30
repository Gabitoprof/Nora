# Teste de GPU (preparação da v0.1.0)

Antes de construir a conversa por voz, precisamos saber se a **RX 9060 XT** acelera os modelos no Windows. Este teste roda **no seu PC**.

## 1. Ollama (o cérebro local)

1. Instale o Ollama: https://ollama.com/download (versão mais recente).
2. Abra o PowerShell na pasta do repositório (`B:\ELLA`) e rode:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\teste_gpu_windows.ps1
   ```

   Na primeira vez ele baixa o modelo `qwen3.5:9b` (~7,6 GB). Para testar outro modelo: `-Modelo gemma4:12b`. Se o modelo já estiver baixado: `-PularDownload`.

3. Me mande o relatório salvo em `data\teste-gpu-<data>.txt` (ou um print do final).

**Como ler o resultado:**

| Linha | Bom sinal |
|---|---|
| `PROCESSOR` (em `ollama ps`) | `100% GPU` |
| `eval rate` | acima de ~30 tokens/s |
| `load duration` | alguns segundos na primeira vez; quase zero depois |

### Se rodar na CPU

A RX 9060 XT é uma placa nova (RDNA 4), e o suporte depende da versão do Ollama e do driver. Nesta ordem:

1. Atualize o driver AMD Adrenalin e o Ollama, reinicie o PC e rode o teste de novo.
2. Ative o modo Vulkan do Ollama: feche o Ollama (ícone perto do relógio → Quit), rode no PowerShell `setx OLLAMA_VULKAN 1`, abra o Ollama de novo e repita o teste.
3. Se ainda assim não usar a GPU, me mande o relatório: as alternativas são o LM Studio (backend Vulkan) ou o plano B com Linux.

## 2. whisper.cpp (a transcrição)

Fica para o início da v0.1.0, junto com o código de voz: vamos compilar ou baixar o whisper.cpp com Vulkan e medir quanto tempo ele leva para transcrever alguns segundos de fala. As instruções entram aqui nessa etapa.
