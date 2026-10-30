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

## Resultados

### 29/10/2026: RX 9060 XT, Windows, Ollama 0.40.13, `qwen3.5:9b`

| Medida | Resultado |
|---|---|
| Processador | **100% GPU** (5,6 GB na VRAM, contexto 4096) |
| Velocidade de geração | **46,8 tokens/s** |
| Leitura do prompt | 345,6 tokens/s |
| Carga do modelo (primeira vez) | 17,6 s |
| Tempo total, **com** modo pensando | 23,8 s, incluindo a carga |

**Conclusões:**

- A GPU AMD funciona no Windows com o Ollama, sem configuração extra. ✅
- A velocidade passa com folga da meta de ~30 tokens/s.
- O **modo pensando** do Qwen 3.5 escreve um raciocínio longo antes de responder, mesmo em perguntas simples. Na voz, fica **desligado** (`pensar = false` no config); para tarefas difíceis, o caminho é o roteador da v0.3.0.
- A carga de ~18 s só acontece quando o modelo não está na memória: o `keep_alive` mantém ele carregado entre as falas.
- Pendente: medir o tempo de resposta **sem** o modo pensando, com o script atualizado.

## 2. whisper.cpp (a transcrição)

Fica para o início da v0.1.0, junto com o código de voz: vamos compilar ou baixar o whisper.cpp com Vulkan e medir quanto tempo ele leva para transcrever alguns segundos de fala. As instruções entram aqui nessa etapa.
