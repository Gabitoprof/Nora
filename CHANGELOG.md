# Changelog

Todas as mudanças relevantes do projeto ficam aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`vMAIOR.MENOR.CORREÇÃO`).

## [Não lançado]

Versão em desenvolvimento: `0.3.0.dev0`.

### Adicionado

- **HUD v0.4.0 em desenvolvimento:** cliente web TypeScript com ondas e partículas conforme
  referência visual aprovada e ponte local opcional de eventos do núcleo. Não cria outro
  microfone ou TTS; conteúdo privado oculto por padrão. Guia: `docs/HUD.md`.
  Homologação integrada Windows/AMD pendente; sem lançamento v0.4.0.

- **Auto-melhoria supervisionada** (`[auto_melhoria]`, guia em `docs/AUTO_MELHORIA.md`):
  - um observador anota, sem o texto das conversas, as tentativas de cada cérebro, as falhas por categoria, os tempos de ouvido, cérebro e voz, as reclamações e os comandos;
  - uma vez por dia (`hora_relatorio`, padrão 20:00), as regras agrupam o que se repetiu em propostas com evidência, causa provável, solução, impacto, risco e testes, num relatório em `data/auto_melhoria/relatorios`;
  - o relatório aparece na próxima conversa e numa notificação do Windows que abre o arquivo;
  - você aprova, recusa ou adia por número (`nora melhorias`, ou pela voz com confirmação). Aprovar gera a especificação para desenvolver; nada muda no código nem é publicado sem você.
  - Sem internet e sem modelo nesta versão; com o PC desligado na hora, o relatório sai na próxima vez.
- **Respostas pela metade viram pendências:** resposta que caiu, ficou sem resposta, foi cancelada (Ctrl+C) ou foi cortada pelo programa fechar fica guardada (nunca como fato). "Termina a resposta que ficou pela metade" responde de novo, inteira e identificada; `nora pendencias` lista e cancela.
- **Sair do modo jogo pede confirmação** ("sim"); perguntar "como sair do modo jogo?" não muda nada.
- O roteador anota cada tentativa (cérebro, resultado e tempo) e as falhas por categoria (`erro_provedor`, `timeout`, `resposta_vazia`, `stream_interrompido`).
- **Roteador de modelos** (v0.3.0): o cérebro local (Ollama) conversa e, quando acha a pergunta difícil demais, passa para o **Claude** (API da Anthropic), com uma frase de espera na mesma voz; "pensa com calma" ou "usa o Claude" na pergunta vão direto. Comandos falados: "use o cérebro local", "use o Claude", "modo automático", "modo jogo" (libera a placa de vídeo e responde pela nuvem), "sair do modo jogo". Reserva nos dois sentidos (sem Ollama responde o Claude; sem Claude, o local), com aviso `[cérebro]`. O Claude recebe a mesma persona, memória, agenda, preferências e emoção. Config `[modelos.nuvem]` (modelos e esforço) e `[roteador]`; extra `.[nuvem]` (SDK `anthropic`); `--medir` e o histórico mostram quem respondeu. Guia em `docs/CEREBRO.md`.
- **Apagar e corrigir pela conversa:** "apaga isso", "esquece que eu disse X" ou "não é X, é Y" agora tiram o fato errado da memória e da agenda (`[memória] esqueci: ...`) e, numa correção, guardam o certo; antes, a Nora dizia que tinha apagado, mas a memória regravava o fato e até anotava o pedido de apagar.
- **Notas do Obsidian:** com `[notas] pasta` apontando para o seu vault, a Nora lê as notas (só leitura), divide em trechos por título e parágrafo e, antes de responder, usa os trechos parecidos com a pergunta, dizendo de qual nota veio. `nora notas ler | buscar | status`; ao abrir a conversa, lê em segundo plano só as notas novas ou alteradas e esquece as apagadas. Pastas ocultas (`.obsidian`, `.trash`) e as de `ignorar` ficam de fora. Índice em `data/notas.db` (sqlite-vec quando instalado). Guia em `docs/OBSIDIAN.md`.
- **Trocar a voz falando:** "troque para a voz do Piper", "volta pro ElevenLabs", "usa o Kokoro", "volta para a voz normal" e "qual voz você está usando?" nos modos com voz. A confirmação já sai com a voz nova; se ela não responder, a Nora diz o motivo e continua com a de antes. Vale até fechar a Nora; no modo só texto, ela avisa que não tem voz em vez de fingir que trocou. Guia em `docs/VOZ.md`.
- `.env.example` conferido por teste: toda variável lida pelo código precisa estar nele, sem chave preenchida.
- **ChatGPT (API da OpenAI) como padrão das perguntas complexas:** as difíceis vão primeiro para o ChatGPT; se ele falhar, recusar ou não responder, a mesma pergunta vai para o Claude, e se os dois falharem, para o local (aviso `[cérebro] ... Pedi ao Claude.`). Uma resposta que caiu no meio não é repetida em outro cérebro. "pergunta pro ChatGPT" ou "usa o Claude" na pergunta escolhem quem responde; "use o ChatGPT" e "use o Claude" mandam a conversa toda. Sem a `OPENAI_API_KEY`, o Claude responde calado. Config `[modelos.openai]` e `[roteador] complexas` ("openai" ou "anthropic"); o extra `.[nuvem]` traz o SDK `openai`; `--verificar` confere a chave, o pacote e a conexão com o ChatGPT.
- O pedido direto ao Claude também entende "utilize", "chama" e "consulta" ("utilize o Claude e me dê um plano").
- **Triagem e segunda chance** (`[roteador] triagem`): perguntas com cara de pesadas (código, contas, análises, planos, textos para escrever, perguntas longas) vão direto para o Claude, sem depender do modelo local se julgar capaz; se o local respondeu e você reclamar ("tá errado", "explica melhor"), a pergunta vai para o Claude. Quando o Claude não está configurado, a Nora avisa uma vez o que falta, em vez de responder pelo local calada.

- **Emoção na voz** (`[emocao]`): a Nora escolhe sozinha a emoção de cada frase (alegre, empolgada, carinhosa, calma, séria, triste, curiosa, sussurro, risada, suspiro) pelo contexto: o que você disse, o que ela lembra, a agenda e a hora. No ElevenLabs v3 vira audio tag (ela ri, suspira, sussurra); no Flash, ajuste de tom por frase (estabilidade, estilo, velocidade); nas vozes locais e na reserva, a marca só é tirada. A tela, o histórico e a memória nunca mostram as marcas. `intensidade` (0 a 1) e `reacoes_por_resposta` controlam o exagero.
- **Aprende com as suas reações:** a curadoria vê o tom da resposta anterior e, quando você reage ("kkkk", "calma, menos", se abre depois de um tom carinhoso), guarda como preferência de tom, sem você precisar pedir.

### Corrigido

- **Ctrl+C no meio de uma resposta** guarda a pendência na hora; antes, se a Nora estava esperando o cérebro, ela só aparecia na sessão seguinte.
- **Retomar uma resposta** também conta como "ocupada": o relatório diário não fecha no meio da retomada.
- **Privacidade do relatório diário:** ele não traz mais o texto das perguntas pendentes (só número, motivo e data); relatórios antigos são limpos ao abrir a Nora.
- **Relatório diário aparece inteiro, sozinho:** abre o `.md` (ou mostra o texto na conversa, `[auto_melhoria] apresentar`), sem interromper uma resposta nem o modo jogo; só conta como mostrado depois de aparecer, e falhas da notificação ou da abertura ficam registradas para tentar de novo.
- A proposta para "pedidos sem resposta" não sugere mais usar o cérebro local no modo jogo; ao sair do modo jogo, a Nora oferece retomar o que ficou sem resposta.
- **Modo jogo:** se nenhuma nuvem responder, a Nora não volta a usar o cérebro local (que ocuparia a placa de vídeo liberada); ela avisa e sugere "sair do modo jogo".
- **Comando com pedido:** "use o Claude para explicar fotossíntese" agora responde a pergunta pelo Claude, sem só trocar o modo; "use o cérebro local para ..." responde aquela pergunta no PC. Comandos sozinhos continuam trocando o modo.
- **Resposta que cai no meio:** se o cérebro local parar depois de começar a falar, a Nora não emenda outra resposta da nuvem; avisa que ficou pela metade. Respostas interrompidas ficam marcadas no histórico (`"situacao"`) e não vão para a memória.
- **Esquecer:** "esquece isso" também tira das buscas os trechos de conversas antigas sobre o assunto e impede o `importar` de trazê-lo de volta; o aviso diz que o registro da conversa continua no histórico. Novo `nora memoria apagar "assunto"` (com `--confirmar`) apaga de vez da memória e do histórico, falando antes o que vai sair.
- **Apagar de vez pela conversa:** "apaga de vez a prova de cálculo" mostra o que sairia (fatos e trechos de conversa) e só apaga depois de "sim, pode apagar"; "não" cancela e mudar de assunto expira o pedido. O próprio pedido também sai do histórico.
- **Troca de voz:** perguntas e comparações sobre vozes ("o Piper é melhor que o Kokoro?") não trocam mais a voz.
- No `nora ouvir`, o texto digitado só era lido depois que o microfone detectava alguém falando (com o microfone captando sem parar, o laço nunca olhava o teclado). Agora é lido em até ~0,3 s.

## [0.2.0] - 2026-11-02

**Memória.** A Nora lembra de você entre uma conversa e outra: anota fatos em áreas (saúde, estudos, trabalho...), guarda cada troca inteira, acha compromissos pelo dia ("o que tenho amanhã?") e aprende como você quer que ela fale (pronúncias e preferências). Critério da etapa atingido: no teste, fatos ditos numa conversa (a prova, o aniversário) foram lembrados em conversas novas, inclusive pela data ("foi ontem, 31 de outubro"). Junto vieram a digitação no lugar da fala, a prioridade da voz sobre outros programas e o caminho para criar uma voz própria (dataset, verificador e treino do Piper no Kaggle ou no Colab).

### Adicionado

- **Memória entre conversas** (v0.2.0): depois de cada resposta, em segundo plano, o modelo local anota fatos duradouros sobre a pessoa; antes de responder, a Nora busca os fatos parecidos com a pergunta e os lê junto. Fica em `data/memoria.db` (SQLite), com busca por significado (embeddings `bge-m3` pelo Ollama, índice `sqlite-vec` opcional). Fatos quase iguais são juntados. Guia em `docs/MEMORIA.md`.
- **Aprender pela conversa:** quando você corrige a pronúncia ("o certo é ôje") ou pede outro jeito de falar ("não repita minha pergunta"), a curadoria guarda: as pronúncias valem na hora para qualquer voz (e para o `gerar-dataset`), e as preferências vão junto em toda resposta. `nora memoria pronuncias | preferencias` para ver, ensinar à mão e esquecer.
- **Agenda da memória:** fatos com data (prova, consulta, aniversário) vão também para uma agenda; a curadoria converte "amanhã", "sexta", "dia 21" e "21/11" em datas, e aniversários repetem todo ano. Antes de responder, a Nora lê o que está marcado para os próximos 7 dias (`[memoria] agenda_dias`) e para o período de que a pergunta fala ("o que tenho amanhã?", "e na sexta?", "em dezembro"), o que a busca por significado sozinha não achava. `nora memoria agenda | marcar | desmarcar`. Fatos antigos com data entram na agenda sozinhos.
- **Memória total:** além dos fatos anotados, cada pergunta e resposta fica guardada inteira, com seu vetor; antes de responder, a Nora também lê os trechos de conversas antigas mais parecidos com a pergunta (`[memoria] trocas_por_pergunta`, padrão 3). O `importar` guarda também as trocas antigas.
- **Áreas da memória:** cada fato ganha uma área (saúde, trabalho, estudos...). A curadoria recebe as áreas que já existem, reaproveita a que couber e cria uma nova quando o assunto é novo; "Saude" e "saúde" contam como a mesma. `nora memoria areas` e `listar --area saúde`; `lembrar --area`. Bancos antigos ganham a coluna sozinhos.
- `nora memoria listar | buscar | lembrar | esquecer | importar`. O `listar` mostra 20 por página (`--pagina`, `--contendo`, `--todos`). O `importar` tira fatos das conversas antigas de `data/historico/` e continua de onde parou.
- Config `[memoria]` (`ativa`, `modelo_embeddings`, `curadoria`, `fatos_por_pergunta`, `similaridade_minima`) e extra de instalação `.[memoria]`.
- **Digitar em vez de falar** (acessibilidade): `nora conversar --voz` (só teclado, resposta falada) e `nora ouvir` aceitando texto digitado a qualquer momento, sem precisar do nome dela.
- `[voz] realce_pergunta` (`duplo` "??", `invertido` "¿...?", `exclamado` "?!") reescreve as perguntas para vozes que não sobem a entonação no "?"; `nora voz comparar "Tudo bem?"` gera a frase em cada jeito para escolher de ouvido.
- Uma pergunta sempre fecha o pedido à voz (o "?" fica no fim, onde a entonação sobe), mesmo quando frases são juntadas.
- `[voz.piper] velocidade` (0.5 a 2.0), `variacao` e `variacao_ritmo` (naturalidade: menos robótica e menos monótona) e `[audio] silencio_inicial_ms`: um pouco de silêncio antes de cada fala, para fones e placas de som que cortam o começo (o "Oi" saía engolido).
- `[voz.pronuncias]`: palavras reescritas só na fala (ex.: `"amanhã" = "amanhãn"`), para qualquer motor de voz.
- Lista de frases de treino com 204 frases, incluindo 46 perguntas, quase 50 com sons nasais (ã, ão, õe) e 50 saudações e respostas curtas ("Oi!", "Tá bom.", "Tchau, até amanhã!"), que a voz treinada sem elas falava picotado.
- O conjunto de treino é convertido para 22.050 Hz com corte de frequências (FFT, numpy), sem abafar nem gerar chiado; antes era uma interpolação simples.
- `docs/LICENCAS.md`: o que é MIT (o código) e a licença de cada dependência, programa, modelo, voz e serviço que a Nora usa, conferida na fonte; um teste falha se uma dependência do `pyproject.toml` não estiver listada.
- `nora voz conferir-dataset --nome X [--descartar]`: o Whisper ouve cada frase do conjunto de treino e compara com o texto; o áudio é medido (ritmo, silêncios, pausas, volume, distorção). Cada frase vira "boa", "conferir" ou "ruim", com uma planilha `conferencia.csv`; `--descartar` tira as ruins do conjunto e o `gerar-dataset` não as refaz; `--tirar 0079 0088` tira frases escolhidas de ouvido.
- **Notebook de treino do Piper no Kaggle** (`scripts/treinar_piper_kaggle.ipynb`): 30 h de GPU grátis por semana e treino em segundo plano (até 12 h, com o PC desligado); para antes do limite, exporta a voz e uma frase de teste, e continua de um treino anterior.
- **Notebook de treino do Piper no Colab** (`scripts/treinar_piper_colab.ipynb`): confere o conjunto, faz o ajuste fino a partir de uma voz pt-BR do Piper (piper1-gpl, baixado no Colab), salva o progresso no Google Drive (a cada 5 minutos, com aviso na tela) para continuar se o Colab desconectar, para quando não há GPU, exporta o `.onnx` e toca uma frase de teste. Passo a passo em `docs/TREINAR_VOZ.md`.
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
