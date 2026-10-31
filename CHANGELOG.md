# Changelog

Todas as mudanças relevantes do projeto ficam aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`vMAIOR.MENOR.CORREÇÃO`).

## [Não lançado]

Versão em desenvolvimento: `0.2.0.dev0`.

### Adicionado

- **Memória entre conversas** (v0.2.0): depois de cada resposta, em segundo plano, o modelo local anota fatos duradouros sobre a pessoa; antes de responder, a Nora busca os fatos parecidos com a pergunta e os lê junto. Fica em `data/memoria.db` (SQLite), com busca por significado (embeddings `bge-m3` pelo Ollama, índice `sqlite-vec` opcional). Fatos quase iguais são juntados. Guia em `docs/MEMORIA.md`.
- **Memória total:** além dos fatos anotados, cada pergunta e resposta fica guardada inteira, com seu vetor; antes de responder, a Nora também lê os trechos de conversas antigas mais parecidos com a pergunta (`[memoria] trocas_por_pergunta`, padrão 3). O `importar` guarda também as trocas antigas.
- **Áreas da memória:** cada fato ganha uma área (saúde, trabalho, estudos...). A curadoria recebe as áreas que já existem, reaproveita a que couber e cria uma nova quando o assunto é novo; "Saude" e "saúde" contam como a mesma. `nora memoria areas` e `listar --area saúde`; `lembrar --area`. Bancos antigos ganham a coluna sozinhos.
- `nora memoria listar | buscar | lembrar | esquecer | importar`. O `listar` mostra 20 por página (`--pagina`, `--contendo`, `--todos`). O `importar` tira fatos das conversas antigas de `data/historico/` e continua de onde parou.
- Config `[memoria]` (`ativa`, `modelo_embeddings`, `curadoria`, `fatos_por_pergunta`, `similaridade_minima`) e extra de instalação `.[memoria]`.
- **Digitar em vez de falar** (acessibilidade): `nora conversar --voz` (só teclado, resposta falada) e `nora ouvir` aceitando texto digitado a qualquer momento, sem precisar do nome dela.
- `[voz] realce_pergunta` (`duplo` "??", `invertido` "¿...?", `exclamado` "?!") reescreve as perguntas para vozes que não sobem a entonação no "?"; `nora voz comparar "Tudo bem?"` gera a frase em cada jeito para escolher de ouvido.
- Uma pergunta sempre fecha o pedido à voz (o "?" fica no fim, onde a entonação sobe), mesmo quando frases são juntadas.
- `[voz.pronuncias]`: palavras reescritas só na fala (ex.: `"amanhã" = "amanhãn"`), para qualquer motor de voz.
- Lista de frases de treino com 154 frases, incluindo 46 perguntas e quase 50 com sons nasais (ã, ão, õe).
- O conjunto de treino é convertido para 22.050 Hz com corte de frequências (FFT, numpy), sem abafar nem gerar chiado; antes era uma interpolação simples.
- `nora voz gerar-dataset`: fala muitas frases com a voz principal (ex.: o fluxo do ComfyUI) e salva no formato de treino do Piper (`wavs/` mono 22.050 Hz + `metadata.csv`), continuando de onde parou; aceita lista de frases ou texto corrido (`--texto`). Lista inicial em `recursos/frases_pt.txt` e guia em `docs/TREINAR_VOZ.md` (ComfyUI → conjunto → treino no Colab → Piper na Nora).
- Frases que já estão esperando vão juntas num pedido só à voz (até 400 caracteres): com vozes lentas, como o ComfyUI, há menos pedidos e menos pausas entre as frases.
- **Voz pelo ComfyUI** (`[voz] motor = "comfyui"`): a Nora manda cada frase para um fluxo seu do ComfyUI (exportado em "Export (API)", com `{{texto}}` no nó de texto), espera pela API local e toca o áudio gerado (WAV, FLAC ou MP3, convertidos com `soundfile`). `config/voz_comfyui.json` fica fora do Git. Em vez de `{{texto}}`, dá para indicar o nó e o campo da frase em `[voz.comfyui] campo` (ex.: `"12.text"`); se errar, a Nora lista os nós e campos de texto do fluxo.
- `nora voz salvar "texto" [--pasta] [--nome] [--ouvir]`: a Nora fala o texto com a voz configurada e salva em .wav (padrão: `data/audios/`).
- **Laboratório de voz:** `nora voz listar` e `nora voz testar "pf_dora:0.7 + af_heart:0.3"` misturam vozes do Kokoro para criar uma voz nova, de graça e no PC; a receita vai em `[voz.kokoro] voz`.
- **Prioridade da voz** (`[audio] prioridade`, padrão `true`; `volume_outros`, padrão 0.2): no Windows, enquanto a Nora fala, os outros programas ficam mais baixos e depois voltam (pycaw).
- A curadoria também anota animais de estimação e acontecimentos marcantes, com a data (antes só fatos duradouros: o susto com o cachorro ficava de fora).
- A Nora mostra o que anotou na memória (`[memória] anotei: ...`) e sabe que tem memória: sem lembrança sobre o assunto, diz que não se lembra, em vez de dizer que não tem memória.
- `nora --verificar` confere o modelo de embeddings; `--medir` mostra quantos fatos foram usados em cada resposta.

### Corrigido

- Se a saída de som escolhida em `[audio] alto_falante` não abrir (sumiu, mudou de número, ou está ocupada por outro programa), a Nora toca na saída padrão e avisa, em vez de ficar muda.
- CHANGELOG da 0.1.0: a ativação aceita "Nora", "Norah" e "Nóra" (não "Ela").

## [0.1.0] - 2026-10-30

**Conversa por voz.** A Nora acorda com o nome, ouve, pensa no modelo local (Qwen 3.5 9B na RX 9060 XT) e responde falando, frase por frase. Critério da etapa atingido: no teste com fone Bluetooth e voz do ElevenLabs, a voz começou entre 1,4 e 2,4 s depois do fim da fala (transcrição ~0,7 s no processador; primeira frase ~0,9 a 1,5 s), sem contar a pausa de 0,7 s que encerra a fala.

### Alterado

- **O projeto e a assistente passam a se chamar Nora** (antes "Ella"): pacote `nora`, comando `nora`, config padrão `config/nora.toml`, variável `NORA_CONFIG`. O nome "Ella" ("Élha") era transcrito como "Elia", "Ilha" ou "ele" e a palavra de ativação quase nunca funcionava.

### Corrigido

- O som é tocado em modo callback (entregando o áudio aos pedaços), que funciona em todas as APIs de áudio do Windows. O modo anterior não existe no WDM-KS, a única API que mostra a saída do modo chamada de fones Bluetooth ("Blocking API not supported yet").
- Erros de conexão mostram o motivo real (ex.: tempo esgotado, sem internet); para serviços na internet, a dica é conferir a conexão em vez de "Ele está aberto?".
- `nora ouvir` pausa o microfone enquanto a Nora fala (`[escuta] pausar_microfone`, padrão `true`; com fone Bluetooth, use `false` e a saída "Headset" do fone). Com fone Bluetooth, o microfone aberto deixa o fone no modo chamada e a voz dela não saía no fone.

### Adicionado

- Voz reserva (`[voz] reserva`, padrão `kokoro`): se a voz principal falhar (ex.: ElevenLabs sem internet), a Nora fala com a reserva e avisa.
- `nora conversar`: conversa digitada com o modelo local, com a resposta aparecendo enquanto é gerada (parte 1 da v0.1.0). `--medir` mostra o tempo até a primeira palavra e a velocidade.
- Persona: prompt de sistema montado da config (humor, formalidade, respostas curtas, data e hora, nome do usuário), com regras para fala em voz alta (sem markdown nem emojis).
- `nora conversar` carrega o modelo na memória ao abrir, para a primeira pergunta não pagar os ~18 s de carga.
- `nora falar`: conversa por voz com Enter para falar (parte 2 da v0.1.0). Ouvido pelo whisper-server (whisper.cpp), voz pelo servidor HTTP do Piper, cada um como programa separado. A resposta é falada frase por frase enquanto o modelo ainda escreve. `--medir` mostra o tempo de transcrição, da primeira frase e até começar a falar.
- Scripts `instalar_voz_windows.ps1` e `iniciar_voz_windows.ps1`, e guia em `docs/VOZ.md`.
- Config `[ouvido]` e `url` em `[voz]`; voz padrão `pt_BR-faber-medium` (uso pessoal, baixada à parte).
- `nora --verificar` também checa o whisper-server e o Piper.
- Voz configurável em `[voz] motor`: **`kokoro`** (novo padrão, voz feminina pt-BR `pf_dora`, local), `piper` ou **`elevenlabs`** (nuvem, chave em `ELEVENLABS_API_KEY`, voz em `[voz.elevenlabs] voz_id`).
- `nora servidor-kokoro`: servidor de voz local com o Kokoro-82M, no mesmo formato do Piper (`POST /synthesize`). Extra de instalação `.[kokoro]`.
- Scripts de voz instalam o Kokoro e iniciam a voz escolhida (`-Voz kokoro|piper|nenhuma`).
- `nora ouvir`: conversa mãos livres (parte 3 da v0.1.0). O Silero VAD (MIT, baixado do PyPI na primeira vez) detecta começo e fim da fala; a fala vira pergunta quando começa com a palavra de ativação ("Nora", aceitando "Norah" e "Nóra"); depois de responder, dá para continuar por `janela_s` segundos sem dizer o nome; "tchau" encerra. Config `[escuta]` (`limiar`, `silencio_ms`, `janela_s`).
- Pronúncia do nome: `[assistente] pronuncia` muda só como a voz fala o nome (a tela continua mostrando o nome).
- O ouvido envia ao Whisper uma dica com o nome da assistente ("Conversa com a assistente Nora."), para ele escrever "Nora" do jeito certo.
- `nora ouvir --gravar-falas` salva cada fala ouvida em `data/falas/`, para diagnóstico. O detector guarda 0,5 s antes do começo da fala, para não cortar a primeira sílaba.
- Persona mais objetiva: sem repetir a pergunta, sem elogios de abertura, sem inventar fatos sobre a pessoa e sem terminar toda resposta com pergunta.
- Config `[modelos.local] temperatura` (padrão 0.6), enviada ao Ollama.
- `nora audio`: lista microfones e alto-falantes, grava alguns segundos e toca de volta. Config `[audio]` para escolher os dispositivos.

### Corrigido

- O microfone agora grava na taxa que ele aceita (ex.: 48 kHz) e converte para 16 kHz, em vez de exigir 16 kHz (causava `MME error 11` no Windows). Erros do microfone viram mensagem clara em vez de derrubar o programa.
- Se o microfone não abrir, a Nora tenta o mesmo microfone pelas outras APIs de áudio do Windows (WASAPI, DirectSound, WDM-KS) e em estéreo, convertendo para mono.
- O microfone também tenta outras taxas (48, 44,1, 16, 32, 22,05 e 8 kHz): fones Bluetooth anunciam 44,1 kHz, mas o microfone deles só abre a 16 ou 8 kHz. Se nada abrir, o erro lista cada tentativa. No WASAPI, pede ao Windows para converter o formato (`auto_convert`); e acha também a versão WDM-KS de fones Bluetooth, que tem outro nome. O teste de cada opção inclui começar a gravar: um microfone que abre mas não grava (ex.: "dispositivo não conectado") passa para a próxima opção em vez de derrubar o programa.
- Descrições de som do Whisper (ex.: `[MÚSICA DE FUNDO]`, `(risos)`) não viram mais pergunta para a Nora.
- A voz pede a fala ao Piper em `POST /synthesize`, o endereço do servidor HTTP do piper-tts atual (antes `POST /` dava erro 405).
- Histórico bruto: cada pergunta e resposta é gravada em `data/historico/AAAA-MM-DD.jsonl`, fora do Git.

## [0.0.1] - 2026-10-30

### Adicionado

- Opção `pensar` em `[modelos.local]` para ligar ou desligar o modo "pensando" do modelo local (desligado por padrão).
- Resultados do primeiro teste de GPU em `docs/TESTE_GPU.md`.

### Alterado

- `scripts/teste_gpu_windows.ps1` mede pela API do Ollama: tempo total, carga e velocidade, com e sem modo pensando, sem os caracteres de animação do terminal no relatório.

## [0.0.0] - 2026-10-30

### Adicionado

- Estrutura do repositório: núcleo Python em `src/nora/`, pastas `hud/`, `mcp_servers/`, `scripts/`, `docs/`.
- Config em TOML (`config/nora.toml`) com nome, persona (humor e formalidade), voz e modelos; sobreposição pessoal por `config/local.toml` e segredos por `.env`, ambos fora do Git.
- Comando `nora` (saudação) e `nora --verificar` (mostra a config e checa Ollama e chave da API).
- Script `scripts/teste_gpu_windows.ps1` para testar o Ollama na GPU AMD, preparando a v0.1.0.
- Testes (pytest), lint (ruff) e CI no GitHub Actions para Windows e Linux.
- Documentação: objetivo, mapa mental (Mermaid e Obsidian Canvas), estudo de referência, guia do Obsidian, `CLAUDE.md`.
- Licença MIT.
