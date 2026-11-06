# Voz da Nora

A Nora conversa por voz usando programas locais, cada um no seu processo, e fala com eles pela rede local:

| Papel | Programa | Porta | Licença |
|---|---|---|---|
| Cérebro | Ollama (`qwen3.5:9b`) | 11434 | MIT |
| Ouvido | whisper.cpp (`whisper-server`) | 8178 | MIT |
| Voz (padrão) | Kokoro (`nora servidor-kokoro`) | 5001 | pesos Apache-2.0; usa phonemizer/espeak-ng (GPL-3.0) |
| Voz (opcional) | Piper (`piper.http_server`) | 5000 | GPL-3.0 |
| Voz (opcional, nuvem) | ElevenLabs | — | serviço pago |

Separar em processos mantém o núcleo da Nora livre de licenças de terceiros, deixa cada peça trocável e prepara o modo distribuído (v0.8.0).

## Motores de voz

Escolha em `[voz] motor` (no `config/local.toml`, para valer só na sua máquina):

| Motor | Voz | Onde roda | Custo | Para quem |
|---|---|---|---|---|
| **`kokoro`** (padrão) | `pf_dora` (feminina pt-BR); também `pm_alex`, `pm_santa` | seu PC (processador) | grátis | quem baixa o projeto e quer testar |
| `piper` | `pt_BR-faber-medium` (masculina) ou uma voz treinada por você ([TREINAR_VOZ.md](TREINAR_VOZ.md)) | seu PC | grátis | voz própria, leve; uso pessoal (bases não comerciais) |
| `elevenlabs` | a que você escolher ou criar | nuvem | pago por uso | a voz mais natural; padrão `eleven_v4_turbo`, em tempo real ([ElevenLabs v4](#elevenlabs-v4-diálogo-em-tempo-real)) |
| `comfyui` | a que você montar num fluxo do ComfyUI | seu PC | grátis | vozes próprias, criadas ou clonadas com autorização |

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

## Trocar a voz falando

Nos modos com voz (`nora ouvir`, `nora falar`, `nora conversar --voz`), dá para trocar a voz no meio da conversa, sem mexer na config:

| Diga | O que acontece |
|---|---|
| "troque para a voz do Piper" / "usa o Piper" | passa a falar com o Piper (a voz que estiver aberta no servidor, como a sua treinada) |
| "volta pro ElevenLabs" | volta para o ElevenLabs |
| "usa a voz do Kokoro" | troca para o Kokoro |
| "volta para a voz normal" | volta para a voz de `[voz] motor` |
| "qual voz você está usando?" | ela diz qual está falando |

- A confirmação ("Pronto, agora falo com a voz do Piper.") já sai com a voz nova, então você ouve na hora como ela ficou.
- Se a voz pedida não responder (janela do Piper fechada, falta a chave do ElevenLabs), ela diz o motivo e **continua com a voz de antes**.
- A reserva continua valendo: se a voz escolhida falhar no meio da conversa, entra a `[voz] reserva`. Se você escolheu justamente a voz que era a reserva, a principal da config passa a ser a reserva.
- A troca vale até fechar a Nora. Para mudar de vez, use `[voz] motor` no `config/local.toml`.
- O servidor da voz precisa estar aberto (o `iniciar_voz_windows.ps1` abre o Kokoro ou o Piper; o ElevenLabs é na nuvem). O script abre uma voz local por vez: com o ElevenLabs de principal, abra com `-Voz piper` para poder trocar para o Piper.
- No `nora conversar` (só texto) não há voz: ela avisa em vez de fingir que trocou.
- Só troca com pedido claro (um verbo como usar, trocar, mudar, voltar, ou "fala com a voz do..."). Perguntas e comparações ("o Piper é melhor que o Kokoro?", "usa o Kokoro ou o Piper?") vão para o cérebro, sem mudar a voz. Com dois motores na frase, vale o que vem depois do "para": "troca do Kokoro para o Piper".

## Salvar uma fala da Nora em .wav

A Nora fala um texto com a voz configurada (ElevenLabs, Kokoro, mistura...) e salva o áudio:

```powershell
nora voz salvar "Bom dia! Hoje é dia de prova, boa sorte." --pasta "C:\Users\voce\Music\Nora" --nome bom-dia --ouvir
```

Sem `--pasta`, salva em `data\audios\`; sem `--nome`, usa a data e o começo do texto. Com `--ouvir`, também toca. (Pedir isso conversando com ela, sem comando, chega com as ferramentas da v0.5.0.)

## Usar uma voz feita no ComfyUI

Qualquer voz que você monte no ComfyUI (clonagem a partir de uma amostra sua, ou outro nó de voz) pode ser a voz da Nora. Ela manda cada frase para o seu fluxo, pela API local do ComfyUI, e toca o áudio gerado.

1. **Prepare o fluxo no ComfyUI:** no nó onde vai a frase, escreva **`{{texto}}`** no lugar do texto (ou, sem mexer no fluxo, diga o nó e o campo em `[voz.comfyui] campo = "12.text"`: o número é o ID do nó no JSON exportado; se errar, a Nora lista os nós e campos de texto do fluxo). O fluxo precisa terminar num nó que salve o áudio (ex.: **Save Audio**). Teste uma vez no próprio ComfyUI.
2. **Exporte no formato da API:** menu **Workflow → Export (API)** (se não aparecer, ligue **Enable dev mode options** nas configurações do ComfyUI). O formato normal (com `widgets_values`) não serve: a Nora avisa se for ele. Salve o arquivo como `B:\Nora\config\voz_comfyui.json` (ele fica fora do Git).
3. **No `config\local.toml`:**

   ```toml
   [voz]
   motor = "comfyui"
   reserva = "kokoro"   # se o ComfyUI estiver fechado ou demorar, ela fala com o Kokoro

   [voz.comfyui]
   url = "http://127.0.0.1:8188"   # o endereço que o ComfyUI mostra ao abrir
   espera_s = 120.0
   ```

4. **Deixe o ComfyUI aberto**, rode `nora --verificar` (deve mostrar `ComfyUI ok`) e teste: `nora voz salvar "Oi! Esta é a minha voz nova." --ouvir`.

O áudio pode sair em WAV, FLAC ou MP3: a Nora converte (precisa do `soundfile`, que vem com `.[voz]`). Dependendo do modelo e da GPU, o ComfyUI leva alguns segundos por frase: a conversa fica mais lenta que com o ElevenLabs ou o Kokoro. Use só vozes suas ou de quem autorizou, e confira a licença do modelo de voz usado no fluxo.

> Para ter a voz do ComfyUI **rápida e leve** no dia a dia, gere um conjunto de frases com ela e treine um Piper: veja [TREINAR_VOZ.md](TREINAR_VOZ.md).

## Perguntas que soam como afirmação

Alguns modelos de voz não sobem a entonação no "?". Dá para testar jeitos de escrever a pergunta que ajudam o modelo a perceber:

```powershell
nora voz comparar "Amanhã você vai à academia?" --ouvir
```

Ela gera a mesma frase normal, `duplo` ("??"), `invertido` ("¿...?") e `exclamado` ("?!"), salva em `data\vozes\pergunta_*.wav` e toca cada uma. Escolha a melhor e ponha no `config\local.toml`:

```toml
[voz]
realce_pergunta = "invertido"
```

Vale também para o `nora voz gerar-dataset`, então o conjunto de treino sai com as perguntas no jeito escolhido.

## Começo da fala cortado ou rápido demais

Se a primeira palavra sai engolida ("Oi" rápido demais), teste nesta ordem, no `config/local.toml`:

1. **Silêncio antes da fala.** Fones Bluetooth e algumas placas de som "acordam" depois que o som começou e cortam o início:

   ```toml
   [audio]
   silencio_inicial_ms = 200
   ```

   Para saber se é isso: `nora voz salvar "Oi! Tudo bem?"` e abra o arquivo em `data\audios\` num player qualquer. Se ali o "Oi" estiver normal, o corte é na saída de som, e o silêncio resolve.
2. **Velocidade do Piper** (vale para toda a fala):

   ```toml
   [voz.piper]
   velocidade = 0.9   # 1.0 normal; menor = mais devagar
   ```

## Voz que muda de tom ou pausa entre frases

Cada pedido à voz é feito em separado, enquanto o modelo ainda escreve. Uma primeira frase curta ("Hahaha, esse atchim!") virava um áudio curto: ele acabava antes de a frase seguinte ficar pronta (a pausa), e a voz começava a seguinte sem saber como a anterior soou (a mudança de tom). Isso pesa mais no ElevenLabs v3, que é o mais expressivo e o mais lento.

Desde a v0.3.1:

- **Frase curta vai junto com a próxima.** Um pedido com menos de `juntar_curta` caracteres espera até 1,5 s pela frase seguinte e vai num pedido só. Se a resposta acabar, ele vai na hora. Uma pergunta nunca espera: o "?" no fim garante a entonação.
- **ElevenLabs com semente fixa.** O mesmo `semente` em todos os pedidos deixa a voz mais parecida de uma frase para a outra.
- **ElevenLabs em streaming.** A Nora pede o áudio pelo endereço de streaming e começa a tocar quando chega a primeira parte (~150 ms de áudio), sem esperar a frase inteira. Os pedidos continuam um por vez. Se a internet cair no meio da frase, ela toca o que chegou e avisa `[erro na voz] A voz parou no meio da frase`.
- **ElevenLabs com a frase anterior.** O pedido leva a frase anterior (`previous_text`), para a entonação continuar de onde parou. Vale por até 1 minuto depois da última fala. Se o modelo recusar o campo, a Nora fala sem ele e não manda mais até fechar.

```toml
[voz]
juntar_curta = 60        # 0 = cada frase vai sozinha, como antes

[voz.elevenlabs]
semente = 42             # -1 = a API sorteia a cada pedido
continuidade = true      # false = não manda a frase anterior
```

Se a primeira fala ainda demorar para começar, baixe `juntar_curta` (ex.: 30). Se o tom ainda mudar, troque a `semente`: cada número dá uma leitura um pouco diferente da mesma voz.

## Voz do Piper robótica ou monótona

O Piper tem dois controles de naturalidade, no `config/local.toml`:

```toml
[voz.piper]
variacao = 0.75        # variação do som (padrão do modelo: ~0.667). Mais alto = mais expressivo
variacao_ritmo = 1.0   # variação do ritmo (padrão: ~0.8). Mais alto = menos monótono
```

Mude um de cada vez, em passos pequenos, e compare com `nora voz salvar "frase" --ouvir`. Se começar a chiar, embolar ou falar de um jeito estranho, desça. `0` volta ao padrão do modelo.

Se a voz for metálica ou chiada (não só monótona), o ajuste não resolve: é treino de menos. Treine mais épocas ou com mais frases (veja [TREINAR_VOZ.md](TREINAR_VOZ.md)).

## Emoção na voz

A Nora escolhe sozinha a emoção de cada frase, olhando o que você disse e como disse, o que ela lembra de você, a agenda e a hora do dia. Você não marca nada.

| Motor | O que acontece |
|---|---|
| ElevenLabs **v3** (`modelo = "eleven_v3"`) | Vira audio tag: ela ri, suspira, sussurra, fala animada ou triste. Mais expressivo, mas começa a falar um pouco mais devagar |
| ElevenLabs Flash, Turbo ou Multilingual | Esses modelos não entendem as tags: a emoção vira ajuste de tom por frase (mais ou menos estável, mais ou menos ênfase, um pouco mais rápida ou mais lenta) |
| Piper, Kokoro, ComfyUI | A marca é tirada; a voz fala normal (inclusive quando entra como reserva) |

Ajustes no `config/local.toml`:

```toml
[emocao]
ativa = true
intensidade = 0.5          # 0 = sem emoção, 1 = bem expressiva
reacoes_por_resposta = 1   # no máximo quantas risadas ou suspiros por resposta
```

Ela também aprende com as suas reações: se você ri de uma brincadeira, reclama de exagero ou se abre depois de um tom carinhoso, a curadoria guarda isso como preferência (`nora memoria preferencias`). Para mudar na hora, diga: "não precisa rir tanto", "pode ser mais animada".

## Corrigir a pronúncia de uma palavra

Se a voz fala mal alguma palavra, reescreva como ela deve soar, só na fala (a tela continua mostrando o texto original). Vale para qualquer motor de voz:

```toml
[voz.pronuncias]
"amanhã" = "amanhãn"
"PUCMG" = "puque eme gê"
```

Teste com `nora voz salvar "Até amanhã!" --ouvir` e ajuste até soar bem.

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

O modelo padrão é o `eleven_v4_turbo`, pelo diálogo em tempo real (próxima seção). Se o diálogo falhar, a Nora fala com o `eleven_flash_v2_5` (o `modelo_reserva`), o mais rápido do ElevenLabs, pelo caminho de sempre: um pedido por frase, com o idioma fixado em português. As duas formas consomem créditos. Para o tom não mudar entre as frases no flash, veja [Voz que muda de tom ou pausa entre frases](#voz-que-muda-de-tom-ou-pausa-entre-frases).

> Se o seu `config\local.toml` tiver um `modelo` antigo (ex.: `eleven_v3`), é ele que vale. Para usar o v4, troque para `modelo = "eleven_v4_turbo"` ou apague a linha.

## ElevenLabs v4 (diálogo em tempo real)

O v4 não funciona no text-to-speech comum (o ElevenLabs responde `400 unsupported_model`): só no **Text to Dialogue**, por WebSocket (`wss://api.elevenlabs.io/v1/text-to-dialogue/stream-input`). A Nora usa assim:

- **Uma conexão por conversa.** Ela abre enquanto o modelo pensa e fica aberta entre as respostas (`keep_alive` a cada 10 s, porque o servidor fecha depois de 20 s sem mensagem). Fecha sozinha depois de `manter_conexao_s` sem falar.
- **O texto vai conforme o modelo escreve**, frase por frase, na mesma conexão: a primeira de cada resposta com `new_turn`, e um `flush` no fim. Não há um pedido por frase.
- **O áudio toca conforme chega**, numa reprodução só, sem pausa entre as frases.
- **Palavras alinhadas na HUD.** O ElevenLabs manda o tempo de cada letra (`sync_alignment`); a HUD recebe as palavras com `precisao "alinhada"`. Se o alinhamento não vier, ela estima pelo som, como nas outras vozes.
- **Interromper** (Ctrl+C) corta o áudio e fecha a conexão; a próxima resposta abre uma nova, sem sobra da anterior.
- **Reserva.** Se a conexão não abrir ou o ElevenLabs recusar (ex.: modelo não liberado na sua conta), a Nora fala a resposta inteira com o `modelo_reserva` pelo HTTP, avisa `[voz reserva] ...` com o motivo e tenta o diálogo de novo depois de 5 minutos.
- Do `voice_settings`, o diálogo só usa a **estabilidade**. A voz é a do `voz_id`, uma só.

```toml
[voz.elevenlabs]
modelo = "eleven_v4_turbo"          # ou "eleven_v4" (mais lento, mais expressivo)
modelo_reserva = "eleven_flash_v2_5"
estabilidade = 0.5                  # 0 = mais variada, 1 = mais estável
continuidade = true                 # false = fecha a conexão depois de cada resposta
manter_conexao_s = 120              # tempo sem falar até fechar a conexão
```

Precisa do pacote `websockets` (vem com `pip install -e ".[voz]"` e no `nora.exe`).

**Diagnóstico.** `nora --verificar` mostra o **modelo efetivo** (o que vai falar de fato: sem o `websockets`, é a reserva), a **Continuidade ElevenLabs** (`ativa`, `desativada`, `não suportada` ou `erro`) e os tempos da última fala. O `nora falar --medir` mostra o mesmo a cada resposta:

- **primeiro áudio:** do envio do primeiro texto até o primeiro PCM chegar;
- **tocando:** do envio até o som começar a sair;
- **silêncio entre trechos:** buracos por falta de áudio da rede (soma e o maior).

Os números também vão para o log e para `data\diagnostico_voz.json`, sem o texto da conversa e sem a chave.

**Medido no PC do Gabriel (06/11/2026, `eleven_v4_turbo`):** primeiro áudio em 985 ms, tocando em 1555 ms, 0 ms de silêncio entre trechos e palavras alinhadas. A Nora usa só o v4; não há comparação planejada com outros modelos. O `eleven_flash_v2_5` fica apenas como reserva automática quando o diálogo falha.

## Ouvido entendendo errado

Quando você fala rápido, baixo ou longe do microfone, o `small` erra mais. Há três ajustes, do mais leve ao mais pesado:

1. **Vocabulário.** Nomes e termos que ele costuma errar vão como dica para o Whisper, no `nora falar` e no `nora ouvir`, junto com o nome da assistente:

   ```toml
   [ouvido]
   vocabulario = ["Obsidian", "Ollama", "Kokoro"]
   ```

2. **Modelo maior.** O `large-v3-turbo` erra bem menos que o `small` em fala pouco clara. A versão `q5_0` (~550 MB) cabe bem na memória. Baixe uma vez e inicie com ele:

   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1 -ModeloWhisper large-v3-turbo-q5_0 -SemPiper
   ```

   ```bash
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_voz_windows.ps1 -ModeloWhisper large-v3-turbo-q5_0
   ```

   No processador, ele é mais lento que o `small` (o `small` levou 0,72 s no 9800X3D). Meça com `nora falar --medir`: se a transcrição passar de ~1,5 s, a auto-melhoria vai apontar. O ganho de velocidade de verdade vem com o whisper.cpp compilado com Vulkan (veja abaixo).

3. **Busca em feixe.** Com `-Feixe 5` no `iniciar_voz_windows.ps1`, o Whisper testa 5 caminhos em vez de 1: erra menos, demora mais. Teste depois do modelo maior, se ainda errar.

Antes de tudo, confira o microfone: o volume de entrada do Windows perto de 80% e o fone perto da boca já resolvem boa parte dos erros.

## Escolhas e pendências

- **Whisper no processador, por enquanto.** O projeto oficial não publica versão pronta para Windows com Vulkan; ela precisa ser compilada (Vulkan SDK, CMake e Visual Studio Build Tools) ou viria de terceiros. No primeiro teste, o `small` no 9800X3D transcreveu em 0,72 s. Se ficar lento, os próximos passos são o modelo `base` (`-ModeloWhisper base` nos dois scripts) ou compilar com Vulkan. Para errar menos, o caminho é o contrário: o `large-v3-turbo-q5_0` (veja [Ouvido entendendo errado](#ouvido-entendendo-errado)), que fica rápido de verdade só com Vulkan.
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
