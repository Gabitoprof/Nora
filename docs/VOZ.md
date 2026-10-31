# Conversa por voz (v0.1.0)

A Nora conversa por voz usando programas locais, cada um no seu processo, e fala com eles pela rede local:

| Papel | Programa | Porta | Licença |
|---|---|---|---|
| Cérebro | Ollama (`qwen3.5:9b`) | 11434 | MIT |
| Ouvido | whisper.cpp (`whisper-server`) | 8178 | MIT |
| Voz (padrão) | Kokoro (`nora servidor-kokoro`) | 5001 | pesos Apache-2.0; usa phonemizer/espeak-ng (GPL-3.0) |
| Voz (opcional) | Piper (`piper.http_server`) | 5000 | GPL-3.0 |
| Voz (opcional, nuvem) | ElevenLabs | — | serviço pago |

Separar em processos mantém o núcleo da Nora em MIT, deixa cada peça trocável e prepara o modo distribuído (v0.8.0).

## Motores de voz

Escolha em `[voz] motor` (no `config/local.toml`, para valer só na sua máquina):

| Motor | Voz | Onde roda | Custo | Para quem |
|---|---|---|---|---|
| **`kokoro`** (padrão) | `pf_dora` (feminina pt-BR); também `pm_alex`, `pm_santa` | seu PC (processador) | grátis | quem baixa o projeto e quer testar |
| `piper` | `pt_BR-faber-medium` (masculina) | seu PC | grátis | alternativa; uso pessoal (a base da voz é não comercial) |
| `elevenlabs` | a que você escolher ou criar | nuvem | pago por uso | a voz definitiva, com mais qualidade |

## Instalar (uma vez)

Na pasta do repositório, com o ambiente ativado (`.venv\Scripts\activate`) e **Python 3.12 ou 3.13**:

```powershell
git pull
```

```powershell
pip install -e ".[dev,voz]"
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1
```

O script baixa (tudo fora do Git, em `ferramentas\` e `models\`):

- o **whisper.cpp** oficial para processador e o modelo **`ggml-small.bin`** (~470 MB);
- o **Kokoro** (`pip install -e .[kokoro]`), o modelo e as vozes (~330 MB) em `models\kokoro\`;
- o **Piper** e a voz `pt_BR-faber-medium`. Para pular: `-SemPiper`.

## Usar

1. Inicie o ouvido e a voz (abrem janelas; deixe-as abertas):

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1
   ```

   O padrão é o Kokoro. Com `-Voz piper` inicia o Piper; com `-Voz nenhuma` (para o ElevenLabs) só o ouvido. O motor escolhido no script tem que ser o mesmo de `[voz] motor`.

2. Teste o microfone e o alto-falante (lista os dispositivos, grava 3 segundos e toca de volta):

   ```powershell
   nora audio
   ```

   Para usar outro microfone ou alto-falante, ponha o número ou o nome da lista em `config\local.toml`:

   ```toml
   [audio]
   microfone = "23"
   ```

3. Confira se está tudo no ar:

   ```powershell
   nora --verificar
   ```

4. Converse:

   ```powershell
   nora falar --medir
   ```

   Aperte **Enter**, fale, aperte **Enter** de novo. Também dá para digitar a pergunta. `sair` encerra.

Com `--medir`, cada resposta mostra três tempos, contados a partir do momento em que você para de gravar:

| Tempo | O que é | Meta |
|---|---|---|
| transcrição | o Whisper transformar sua fala em texto | o menor possível |
| primeira frase | a primeira frase da resposta ficar pronta | |
| **começou a falar** | o som da Nora começar a sair | **< 2 s** (MVP), < 1 s (final) |

## Digitar em vez de falar

Para quem tem dificuldade na fala, ou em lugares onde não dá para falar, a Nora aceita **texto digitado** e responde **falando**:

| Comando | Você | Ela |
|---|---|---|
| `nora conversar --voz` | só digita (não usa microfone) | responde falando e escrevendo |
| `nora ouvir` | fala "Nora, ..." **ou** digita a qualquer momento | responde falando |
| `nora falar` | aperta Enter e fala, **ou** digita a pergunta | responde falando |
| `nora conversar` | digita | responde só escrevendo |

No `nora ouvir`, o que você digita não precisa do nome dela. Digitar `sair` encerra.

## Mãos livres (`nora ouvir`)

Em vez de apertar Enter, a Nora fica ouvindo o tempo todo e responde quando a frase **começa com o nome dela**:

```powershell
nora ouvir --medir
```

- **"Nora, que horas são?"** → ela responde.
- Depois da resposta, por **8 segundos** dá para continuar **sem dizer o nome** ("E amanhã?").
- **"Nora"** sozinho → ela diz "Oi, pode falar." e espera.
- **"Tchau"**, **"é só isso"** → ela se despede e volta a esperar o nome.
- **Ctrl+C** encerra.

Como funciona: o **Silero VAD** (licença MIT, baixado sozinho do PyPI na primeira vez para `models\silero_vad.onnx`) percebe quando você começa e para de falar; cada fala vai para o Whisper; se o texto começa com a palavra de ativação, vira pergunta.

Ajustes em `config\local.toml`:

```toml
[assistente]
palavra_de_ativacao = "Nora"   # ou "Oi Nora", se ela acordar sem querer

[escuta]
limiar = 0.5        # suba (ex.: 0.6) se ruído vira fala; desça se ela não percebe você
silencio_ms = 700   # pausa que encerra a sua fala; menor responde mais rápido, mas corta pausas
janela_s = 8.0      # segundos para continuar sem dizer o nome
```

Limites desta versão:

- **Por que "Nora":** o nome antigo, "Ella" (pronunciado "Élha"), virava "Elia", "Ilha" ou "ele" na transcrição, e ela quase nunca acordava. "Nora" o Whisper reconhece bem e quase nunca começa uma frase por acaso. A ativação aceita "Nora", "Norah" e "Nóra". Se ela acordar sem querer, use `palavra_de_ativacao = "Oi Nora"`. Para mudar como a voz fala o nome, use `[assistente] pronuncia`. Uma palavra de ativação de verdade (openWakeWord treinado com o nome dela, rodando antes do Whisper) fica para depois.
- **Toda fala passa pelo Whisper**, mesmo as que não são para ela. Com TV ou conversa no ambiente, o processador trabalha mais. `--mostrar-ignoradas` mostra o que ela ouviu e ignorou.
- **Enquanto ela fala, ela não ouve** (o microfone fica pausado), porque ainda não há cancelamento de eco. Com **fone Bluetooth** isso também é necessário: com o microfone aberto, o fone fica no modo chamada e a saída de som normal fica muda. Ao reabrir o microfone, o fone pode levar um instante para trocar de modo. Interromper falando por cima (barge-in) fica para depois; com fone de ouvido isso fica mais fácil.

## Música tocando junto (prioridade da voz)

Quando outro programa está tocando som (música, vídeo), a Nora fala por cima assim:

```toml
[audio]
prioridade = true     # enquanto ela fala, os outros programas ficam mais baixos e depois voltam
volume_outros = 0.2   # quanto sobra do volume deles (0 = mudo, 1 = sem mudança)
```

Com `prioridade = false`, ela fala misturada com o resto, no volume normal. Para respostas só escritas, use `nora conversar`.

Funciona no Windows (biblioteca `pycaw`, instalada com `.[voz]`). Se a saída escolhida em `alto_falante` não abrir (o aparelho sumiu, mudou de número ou está ocupado por outro programa), a Nora usa a saída padrão do Windows e avisa com `[som] ...`.

## Fone Bluetooth (microfone e som no mesmo fone)

Fones Bluetooth têm dois modos: **música** (som bom, sem microfone) e **chamada** (microfone ligado, som com qualidade de telefone). Quando o microfone abre, o fone vai para o modo chamada e a saída "Fones de ouvido" fica **muda**; cada troca de modo leva cerca de 1 segundo de silêncio.

Para o som não sumir, deixe o fone sempre no modo chamada:

1. Rode `nora audio` e procure, entre os **alto-falantes**, o "Headset" do fone (no Windows costuma aparecer como `Headset (@System32\drivers\bthhfenum.sys...(NOME DO FONE))`, na API WDM-KS). Anote o número.
2. No `config\local.toml`:

   ```toml
   [audio]
   alto_falante = "17"   # o número do "Headset" do fone

   [escuta]
   pausar_microfone = false
   ```

Os números mudam quando você conecta ou desconecta aparelhos; confira com `nora audio`. Com microfone separado (ou caixa de som), volte para `alto_falante = ""` e `pausar_microfone = true`.

## Laboratório de voz (criar a sua voz, de graça)

Cada voz do Kokoro é um "DNA" numérico, e dá para **misturar vozes** para criar uma voz nova, no seu PC e de graça:

```powershell
nora voz listar
```

```powershell
nora voz testar "pf_dora:0.7 + af_heart:0.3" --velocidade 0.95
```

Ela fala uma frase de teste (ou a sua, com `--frase "..."`) e salva a amostra em `data\vozes\`. Quando gostar, ponha a receita no `config\local.toml`:

```toml
[voz]
motor = "kokoro"

[voz.kokoro]
voz = "pf_dora:0.7 + af_heart:0.3"
velocidade = 0.95
```

Dicas: mantenha a `pf_dora` (português do Brasil) com o **maior peso**, para o sotaque e a pronúncia; misture pequenas porções de outras vozes para mudar o timbre (mais grave, mais suave, mais brilhante). Os pesos não precisam somar 1; a Nora ajusta.

## Usar o ElevenLabs

1. Crie uma conta em elevenlabs.io e uma chave de API (perfil → API Keys). Defina um limite de gasto.
2. Escolha uma voz na biblioteca ou crie uma no **Voice Design**. Na página da voz, copie o **voice ID**.
3. No `.env` (fora do Git):

   ```
   ELEVENLABS_API_KEY=sua_chave
   ```

4. No `config\local.toml` (fora do Git):

   ```toml
   [voz]
   motor = "elevenlabs"

   [voz.elevenlabs]
   voz_id = "cole_o_voice_id_aqui"
   ```

5. Inicie o ouvido e o Kokoro, que serve de **voz reserva** quando o ElevenLabs falha (ex.: sem internet): `iniciar_voz_windows.ps1 -Voz kokoro`. Sem reserva, use `-Voz nenhuma` e `reserva = ""` em `[voz]`.
6. Rode `nora --verificar` (deve mostrar `ElevenLabs configurado` e `Kokoro (reserva) ok`) e `nora falar --medir`.

O modelo padrão é o `eleven_flash_v2_5`, o mais rápido do ElevenLabs, com o idioma fixado em português. Cada frase é um pedido à API: a conversa por voz consome créditos.

## Escolhas e pendências

- **Whisper no processador, por enquanto.** O projeto oficial não publica versão pronta para Windows com Vulkan; ela precisa ser compilada (Vulkan SDK, CMake e Visual Studio Build Tools) ou viria de terceiros. No primeiro teste, o `small` no 9800X3D transcreveu em 0,72 s. Se ficar lento, os próximos passos são o modelo `base` (`-ModeloWhisper base` nos dois scripts) ou compilar com Vulkan.
- **Voz `pt_BR-faber-medium` (Piper) só para uso pessoal.** Foi ajustada a partir de uma voz em inglês treinada com uma base **só para uso não comercial**. É baixada à parte e nunca distribuída.
- **Dois modos:** `nora falar` (Enter para falar, bom para ambiente barulhento) e `nora ouvir` (mãos livres).
- **Sem interrupção ainda.** Falar por cima da Nora (barge-in) precisa de cancelamento de eco e vem depois; por enquanto, Ctrl+C interrompe.

## Se algo der errado

- **O pip instala em `...\pythoncore-3.xx\Scripts` e avisa "not on PATH":** o ambiente não estava ativado. Rode `.venv\Scripts\activate` (o terminal passa a mostrar `(.venv)`) e repita o `pip install`.
- **O `pip install` falha com "conflicting dependencies" e "no matching distributions" para `onnxruntime`:** o Python é novo demais (aconteceu com o 3.15). Veja as versões com `py -0`, instale o 3.13 (`py install 3.13`) e recrie o ambiente: `deactivate`, `Remove-Item -Recurse -Force .venv`, `py -3.13 -m venv .venv`, `.venv\Scripts\activate`, `pip install -e ".[dev,voz]"`.
- **"Acesso negado" ao instalar:** algum `nora` está aberto (feche os terminais ou rode `Stop-Process -Name nora -Force`).
- **"Não consegui abrir o microfone" (ex.: `MME error 11`):** a Nora já tenta o mesmo microfone pelas outras APIs do Windows. Se nada abrir, confira em Configurações → Privacidade e segurança → Microfone se "Permitir que aplicativos da área de trabalho acessem o microfone" está ligado, e rode `nora audio`.
- **A Nora responde a `[MÚSICA DE FUNDO]` ou não ouve nada:** a gravação ficou baixa; fale mais perto do microfone, depois de aparecer "(gravando...)".
- **Kokoro, Piper ou whisper-server "não respondeu"** no `nora --verificar`: veja a janela correspondente aberta pelo script de iniciar; a mensagem de erro aparece lá. Me mande um print.
- **O Piper recusa o pedido (405 ou 404):** a versão mudou o endereço. Rode `Select-String -Path .venv\Lib\site-packages\piper\http_server.py -Pattern "route"` e me mande o resultado.
