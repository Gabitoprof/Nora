# Conversa por voz (v0.1.0, parte 2)

A Ella conversa por voz usando três programas locais, cada um no seu processo:

| Papel | Programa | Porta | Licença |
|---|---|---|---|
| Cérebro | Ollama (`qwen3.5:9b`) | 11434 | MIT |
| Ouvido | whisper.cpp (`whisper-server`) | 8178 | MIT |
| Voz | Piper (`piper.http_server`) | 5000 | **GPL-3.0** |

O núcleo da Ella só fala com eles pela rede local. Por isso a licença GPL do Piper não contamina o nosso código (MIT), e cada peça pode ser trocada ou rodar em outra máquina depois (v0.8.0).

## Instalar (uma vez)

Na pasta do repositório, com o ambiente ativado (`.venv\Scripts\activate`):

```powershell
git pull
```

```powershell
pip install -e ".[dev,voz]"
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1
```

O script baixa:

- o **whisper.cpp** oficial para processador (`whisper-bin-x64.zip`) em `ferramentas\whisper\`;
- o modelo **`ggml-small.bin`** (~470 MB, multilíngue) em `models\`;
- o **Piper** (`pip install piper-tts[http]`) e a voz **`pt_BR-faber-medium`** em `models\piper\`.

## Usar

1. Inicie o ouvido e a voz (abrem duas janelas; deixe-as abertas):

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
   ```

2. Confira se está tudo no ar:

   ```powershell
   ella --verificar
   ```

3. Converse:

   ```powershell
   ella falar --medir
   ```

   Aperte **Enter**, fale, aperte **Enter** de novo. Também dá para digitar a pergunta. `sair` encerra.

Com `--medir`, cada resposta mostra três tempos, contados a partir do momento em que você para de gravar:

| Tempo | O que é | Meta |
|---|---|---|
| transcrição | o Whisper transformar sua fala em texto | o menor possível |
| primeira frase | a primeira frase da resposta ficar pronta | |
| **começou a falar** | o som da Ella começar a sair | **< 2 s** (MVP), < 1 s (final) |

## Escolhas e pendências

- **Whisper no processador, por enquanto.** O projeto oficial não publica versão pronta para Windows com Vulkan; ela precisa ser compilada (Vulkan SDK, CMake e Visual Studio Build Tools) ou viria de terceiros. Começamos com a versão oficial para processador, que o 9800X3D deve aguentar com o modelo `small`. Se a transcrição ficar lenta, os próximos passos são: modelo `base` (`-ModeloWhisper base` nos dois scripts), ou compilar com Vulkan.
- **Voz `pt_BR-faber-medium` só para uso pessoal.** Ela foi ajustada a partir de uma voz em inglês treinada com uma base de dados **só para uso não comercial**. Serve para testar e para uso pessoal; é baixada à parte e nunca distribuída com o projeto. A voz definitiva e original da Ella fica para depois.
- **Enter para falar.** A palavra de ativação ("Ella") e a detecção automática de quando você para de falar entram na parte 3.
- **Sem interrupção ainda.** Falar por cima da Ella (barge-in) precisa de cancelamento de eco e vem depois; por enquanto, Ctrl+C interrompe.

## Se algo der errado

- **O pip instala em `...\pythoncore-3.xx\Scripts` e avisa "not on PATH":** o ambiente não estava ativado. Rode `.venv\Scripts\activate` (o terminal passa a mostrar `(.venv)`) e repita o `pip install`.
- **O `pip install piper-tts` falha com "conflicting dependencies" e "no matching distributions" para `onnxruntime`:** o Python é novo demais (aconteceu com o 3.15). Veja as versões instaladas com `py -0`, instale o 3.13 se precisar e recrie o ambiente: `deactivate`, `Remove-Item -Recurse -Force .venv`, `py -3.13 -m venv .venv`, `.venv\Scripts\activate`, `pip install -e ".[dev,voz]"`.

- **`ella falar` diz que falta a parte de áudio:** rode `pip install -e ".[dev,voz]"`.
- **`whisper-server` ou `Piper` "não respondeu"** no `ella --verificar`: veja a janela correspondente aberta pelo script de iniciar; a mensagem de erro aparece lá. Me mande um print.
- **O Piper não aceita `--data-dir` ou `--port`:** rode `python -m piper.http_server --help` e me mande o resultado; as opções mudam entre versões.
- **A gravação não pega o microfone:** o Windows usa o microfone padrão (Configurações → Sistema → Som → Entrada).
