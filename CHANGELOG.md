# Changelog

Todas as mudanças relevantes do projeto ficam aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`vMAIOR.MENOR.CORREÇÃO`).

## [Não lançado]

### Alterado

- **Licença:** a partir de 06/11/2026, o código passa a ser de **todos os direitos reservados** (público só para consulta). As versões até a `v0.3.0` continuam em MIT.

### Corrigido (roadmap "Imagem para as falas", fases 0 e 1)

- **Voz que cai no meio da resposta (v4):** antes do 1º áudio, a reserva fala tudo; depois de começar, a reserva (flash) continua do último limite de palavra que o alinhamento cobriu, sem repetir o que já foi ouvido e só depois que o áudio recebido termina de tocar; sem alinhamento, a fala para com aviso claro e "repete a resposta que caiu" fala a resposta inteira de novo, sem perguntar ao cérebro. Áudio sem alinhamento continua tocando (as palavras viram estimativa).
- **Diagnóstico da voz:** além do modelo efetivo, da continuidade e dos tempos, registra o número de gerações (pedidos de síntese) por resposta e o motivo de cada troca para a reserva; o caminho HTTP também mede pedido → primeiro áudio, início da reprodução e silêncio entre trechos. Sem texto da conversa nem chaves.
- **Palavras nas pausas (HUD):** a palavra fica até a próxima começar, inclusive nas pausas, com teto de 1,5 s para silêncios longos (antes sumia depois de 320 ms). No fim da reprodução, no cancelamento e ao passar para "Privado", some na hora.
- **Relógio da fala (HUD):** medido em simulação (amostras a 20 Hz, atraso de rede de 5 a 45 ms, engasgos de 150 a 450 ms). A configuração anterior (300/250 ms) perdia palavras e atrasava até 217 ms com engasgos; agora aceita amostras de até 450 ms e extrapola até 400 ms (pior caso 100 ms, nenhuma palavra perdida) e ignora recuos menores que 60 ms (a palavra não pisca quando chega uma amostra nova).
- **Estado da HUD com `reproducao_encerrada`:** o fim apaga a fala daquela reprodução e o sinal da voz; fim antigo, repetido ou fora de ordem é ignorado; uma fala atrasada de reprodução já encerrada não volta; na reconexão os ids voltam a valer (o servidor pode ter reiniciado).
- **Alinhamento das palavras do ElevenLabs v4:** a referência dos tempos (relativa ao trecho de áudio ou ao turno) é decidida uma vez por turno e não muda no meio da fala; cada palavra fica na posição real do PCM. O silêncio inicial configurável (`[audio] silencio_inicial_ms`) agora desloca as palavras junto com o som.

### Corrigido (revisão da v0.4.0, branch `integracao/v0.4.0`)

- **Paleta dentro do pacote:** `src/nora/paleta.json`, lido pela HUD e pelo Second Brain. Antes ficava em `hud/` e uma instalação por wheel quebrava ao importar o Second Brain.
- **Versão única do produto:** `0.4.0.dev0` (Python) e `0.4.0-dev.0` (HUD), com teste que falha se divergirem. `nora --verificar` e a HUD (Ajustes) mostram versão e commit. `hud/package.json` com `"license": "UNLICENSED"`.
- **Falhas da HUD no caminho do áudio** deixam de ser engolidas em silêncio: são contadas por lugar e tipo, com uma linha de log por tipo, sem texto da conversa nem áudio. A fala nunca para por isso.
- **Cores:** serenidade, sussurro e suspiro passam para calma (turquesa); preocupação, para seriedade (azul).
- **Documentação de licença:** o mapa mental troca "Open source" por "Licença e distribuição"; `LICENCAS.md` só registra que o Kokoro (espeak-ng, GPL-3.0) roda em processo separado e que distribuir junto com ele exige cumprir a GPL.

### Adicionado (distribuição no Windows)

- **Nora instalada, fora do repositório** (`caminhos.py`): a config padrão vai dentro do pacote (`src/nora/nora.toml`); a config pessoal, o `.env`, a memória e os modelos ficam em `%APPDATA%\Nora`, criada na primeira execução (`NORA_HOME` troca a pasta). No repositório, nada muda.
- **`nora.exe` sem assinatura e instalador** (`scripts/empacotar_windows.ps1`, PyInstaller em pasta e Inno Setup). O instalador não pede administrador e não apaga `%APPDATA%\Nora` ao desinstalar. O workflow **Empacotar** gera os dois no Windows a cada push na `main`, na `integracao/...` e nas tags, testa o `.exe` (versão, pasta do usuário, HUD) e publica os arquivos por 14 dias. Os avisos de licença dos componentes vão na pasta `licencas` do programa.
- **Pacote de dependências da Nora** (`instalar_dependencias.ps1`): Visual C++, Ollama e modelos, whisper.cpp e modelo do Whisper, pelo `winget` e pelos sites oficiais, com resumo `ok`/`FALHOU`. Atalho **Nora** no menu Iniciar (liga o Ollama e o ouvido, abre a HUD e escuta). Guia em `docs/INSTALACAO.md`.
- Instalada, a voz padrão é o ElevenLabs: as vozes locais (Kokoro, Piper) usam programas GPL e não vão no `.exe`.

### Adicionado (voz)

- **ElevenLabs v4 como voz principal** (`modelo = "eleven_v4_turbo"`; `"eleven_v4"` opcional), pelo diálogo em tempo real (WebSocket do Text to Dialogue), porque o v4 não aceita o text-to-speech comum. Medido no Windows com o `eleven_v4_turbo`: primeiro áudio em ~1 s, sem silêncio entre trechos. Uma conexão por conversa, com `keep_alive`; o texto vai conforme o modelo escreve e o áudio toca conforme chega, sem um pedido por frase. Interromper fecha a conexão sem misturar áudio.
- **Palavras alinhadas na HUD:** o tempo real de cada palavra vem do ElevenLabs (`precisao "alinhada"`); a estimativa fica só de reserva.
- **Reserva no flash:** se o diálogo falhar, a resposta sai com o `eleven_flash_v2_5` pelo HTTP, com o motivo no aviso.
- **Diagnóstico da voz** no `nora --verificar`, no `--medir` e no log: modelo efetivo, continuidade (ativa, desativada, não suportada, erro), tempo até o primeiro áudio e até tocar, e silêncio entre trechos. Sem texto da conversa nem chave.
- Dependência nova: `websockets` (BSD-3-Clause), no extra `voz`.

### Adicionado (revisão da v0.4.0)

- **Teste de instalação limpa** (`scripts/testar_instalacao_limpa.py`, job `instalacao` no CI): gera o wheel, instala fora do checkout e confere a paleta, o Second Brain e os arquivos do pacote.
- **Teste de regressão** da troca de voz: a confirmação leva o texto à HUD.
- **`scripts/homologacao_windows.ps1`:** testes, build, `nora --verificar` e medição de CPU, GPU e VRAM com a HUD aberta, gravados num arquivo. Roteiro de ~15 min em `docs/HOMOLOGACAO.md`.

### Adicionado (Second Brain, branch `feat/v0.3.1-second-brain`)

- **Second Brain no Obsidian** (`[segundo_cerebro]`, desligado por padrão; guia em `docs/SEGUNDO_CEREBRO.md`):
  - as memórias consolidadas viram notas em `Nora Brain/`, com propriedades YAML, tags e `[[links]]` para a área, os nomes que aparecem em 2 memórias ou mais, os meses da agenda e as preferências;
  - a sincronização é incremental, idempotente e retomável depois de uma queda (escrita atômica);
  - correções, esquecer e apagar de vez saem do vault;
  - as notas que você criou ou editou nunca são sobrescritas nem apagadas: viram conflito;
  - as áreas privadas (saúde e finanças, por padrão) não saem do banco;
  - a pasta fica de fora do leitor de notas, para não haver ciclo.
- **Fora do caminho da fala:**
  - a conversa só levanta um sinal; uma linha própria espera a Nora parar de responder e de falar (`conversa.falando`), lê a memória em modo só leitura e para no meio se ela voltar a falar;
  - nenhuma chamada nova a modelo;
  - medição em `scripts/medir_segundo_cerebro.py`.
- **Mapa da memória:** "Nora, mostre seu segundo cérebro" ou `nora cerebro mapa --abrir`. É uma página sem internet, com cor por área, halo pelo tom da conversa (as cores da HUD), tamanho por ligações, pulso de recência, ligações que surgem ao abrir, busca, filtros, foco, a ficha com o porquê de cada ligação e o link para o Obsidian. O texto das memórias abre escondido.
- **Tom da conversa no fato** (`fatos.emocao`): o tom predominante das etiquetas da resposta, guardado em segundo plano pela curadoria. É o tom da Nora, não um sentimento da pessoa.
- **Cores dos tons** lidas de `hud/paleta.json` (`nora.paleta`), o mesmo arquivo da HUD: calma turquesa, tristeza lavanda, curiosidade terracota, como na tabela da HUD v0.4.0.
- **Contrato versionado** `segundo_cerebro_contrato.json` (v1) para uma HUD de memória futura, com os mesmos nomes de emoção da HUD.
- **Comandos novos:** `nora cerebro sincronizar | status | mapa`.

### Corrigido

- HUD: o painel "Sinal de áudio" usa o mesmo sinal da onda central, em escala de decibéis. Antes mostrava "0%" com fala baixa (RMS 0,004) enquanto a onda já se mexia, e mantinha o último nível da escuta durante "Pensando". Com teste de regressão.
- HUD: navegação inicial por link externo/same-site deixa de retornar HTTP 403; APIs,
  iframe, Host/Origin e confirmação por token permanecem protegidos, com regressões HTTP/browser.
- Ferramentas da HUD: dependências de teste/lint atualizadas para corrigir alertas de auditoria,
  com override limitado às versões vulneráveis de minimatch e testes de compatibilidade.
- **Voz que mudava de tom e pausava depois de uma primeira frase curta** (ex.: "Hahaha, esse atchim!" no ElevenLabs v3):
  - um pedido à voz com menos de `[voz] juntar_curta` caracteres (padrão 60) espera até 1,5 s pela próxima frase e vai junto com ela. Perguntas não esperam, e o fim da resposta libera na hora;
  - o ElevenLabs recebe uma semente fixa (`[voz.elevenlabs] semente`, padrão 42) e a frase anterior (`previous_text`, `continuidade = true`), para a entonação continuar. Se o modelo recusar o campo, ela segue sem ele.
- **Datas erradas em "daqui a N dias":** o modelo local errava o dia e o dia da semana. Agora as contas ("daqui a 23 dias", "e daqui a 24?", que usa a unidade da última pergunta que tinha uma, "há 2 semanas", "3 meses atrás", o dia da semana de "25/12") são feitas pelo código e vão prontas para o modelo.
- **Preferências inventadas a partir de erro de transcrição:** uma fala curta e sem sentido ("Aqui assim.") virava preferência copiada dos exemplos da instrução ("Seja mais direta."). Agora a preferência só vale se a fala tiver relação com ela, for uma risada ou tiver 6 palavras ou mais, e a curadoria é avisada de que fala sem sentido é erro de transcrição.
- **Ouvido errando nomes no `nora falar`:** a dica com o nome da assistente, que só ia no `nora ouvir`, agora vai também no `nora falar`.

### Adicionado

- **HUD v0.4.0 em desenvolvimento:** cliente web TypeScript com ondas e partículas conforme
  referência visual aprovada e ponte local opcional de eventos do núcleo. Não cria outro
  microfone ou TTS; conteúdo privado oculto por padrão. Guia: `docs/HUD.md`.
  Homologação integrada Windows/AMD pendente; sem lançamento v0.4.0.
- HUD acústica em retomada: medidas derivadas do PCM, animações de ondas e partículas,
  palavras somente com temporização válida e integração com reprodução em streaming.
  Implementação validada por regressões e checklist em `docs/HOMOLOGACAO.md`.
- Paleta de emoções com uma fonte só (`hud/paleta.json`), lida também pelo Python (`nora.paleta`), para o Second Brain usar as mesmas cores.
- **Voz do ElevenLabs em streaming:** a fala começa a tocar com a primeira parte do áudio, sem esperar a frase inteira chegar. As vozes locais não mudam.
- `[ouvido] vocabulario`: nomes e termos que o Whisper deve escrever certo, mandados como dica nos dois modos.
- Os scripts de voz aceitam o modelo `large-v3-turbo-q5_0` (mais preciso em fala pouco clara) e `-Feixe N` (busca em feixe no `whisper-server`). Guia em `docs/VOZ.md`, "Ouvido entendendo errado".

## [0.3.0] - 2026-11-05

**Roteador de modelos.** A conversa do dia a dia continua no PC, e as perguntas difíceis vão para a nuvem e voltam com a mesma voz, a mesma persona e a mesma memória. Critério da etapa atingido nos testes automatizados: a pergunta difícil sobe para a API (ChatGPT, com o Claude de reserva) e a resposta volta falada pela voz da Nora. Junto vieram a emoção na voz, a troca de cérebro e de voz por comando, as notas do Obsidian, o esquecer e apagar de vez, as respostas pela metade recuperáveis e uma auto-melhoria supervisionada. Homologação no Windows com GPU AMD registrada em `docs/RELEASE_v0.3.0.md`.

### Adicionado

- **Roteador de modelos** (`[roteador]`, guia em `docs/CEREBRO.md`):
  - o cérebro local (Ollama) conversa; as perguntas difíceis vão para a nuvem, na ordem **ChatGPT → Claude → local** (`[roteador] complexas`), com uma frase de espera na mesma voz;
  - a nuvem é acionada pela triagem (código, contas, análises, planos, textos, perguntas longas), pelo `{pensar}` do modelo local e pela segunda chance quando você reclama;
  - pedido direto: "pensa com calma", "pergunta pro ChatGPT ...", "use o Claude para ...". O pedido é respondido por quem foi chamado e o modo não muda;
  - comandos falados: "use o cérebro local", "use o ChatGPT", "use o Claude", "modo automático", "modo jogo" (libera a placa de vídeo e responde pela nuvem) e "sair do modo jogo" (pede confirmação);
  - reservas nos dois sentidos, com avisos `[cérebro]`. Uma resposta que caiu no meio não é emendada com a de outro cérebro;
  - `--medir` e o histórico mostram quem respondeu;
  - config `[modelos.openai]`, `[modelos.nuvem]` e `[roteador]`; extra `.[nuvem]` (SDKs `openai` e `anthropic`); o `--verificar` confere chaves, pacotes e conexão.
- **Emoção na voz** (`[emocao]`): a Nora escolhe o tom de cada frase pelo contexto. No ElevenLabs v3 vira audio tag (ela ri, suspira, sussurra); no Flash, ajuste de tom; nas vozes locais, a marca é tirada. A curadoria aprende com as suas reações.
- **Trocar a voz falando:** "troque para a voz do Piper", "volta pro ElevenLabs", "qual voz você está usando?". Perguntas e comparações sobre vozes não trocam nada.
- **Notas do Obsidian** (`[notas] pasta`, guia em `docs/OBSIDIAN.md`): leitura incremental do vault, só leitura, com os trechos parecidos usados na resposta e citados pelo nome da nota. Comandos `nora notas ler | buscar | status`.
- **Esquecer e apagar de vez** (guia em `docs/MEMORIA.md`):
  - "esquece que eu disse X" deixa de usar o assunto, inclusive os trechos de conversas antigas e o `importar`;
  - "apaga de vez X" (pela conversa, com "sim") ou `nora memoria apagar "X" --confirmar` tira da memória e do histórico, mostrando antes o que vai sair.
- **Respostas pela metade viram pendências:** resposta que caiu, ficou sem resposta, foi cancelada (Ctrl+C) ou foi cortada pelo programa fechar fica guardada, nunca como fato. "Termina a resposta que ficou pela metade" responde de novo, inteira e identificada; `nora pendencias` lista e cancela.
- **Auto-melhoria supervisionada** (`[auto_melhoria]`, guia em `docs/AUTO_MELHORIA.md`):
  - um observador anota, sem o texto das conversas, tentativas, falhas por categoria, tempos e reclamações;
  - uma vez por dia, regras locais (sem internet e sem modelo) agrupam o que se repetiu em propostas com evidência, causa, solução, impacto, risco e testes;
  - o relatório aparece sozinho, sem interromper uma resposta nem o modo jogo;
  - você aprova, recusa ou adia (`nora melhorias`, ou pela voz com "sim"). Aprovar só gera a especificação; nada muda no código nem é publicado sem você.
- Testes que mantêm o `.env.example` e o `docs/LICENCAS.md` em dia.

### Corrigido

- **Enter no `nora falar` com a auto-melhoria ligada:**
  - um erro ao apresentar o relatório podia deixar para trás a thread que lê o teclado, e ela engolia o Enter seguinte (o de parar de gravar);
  - o modo `abrir` podia tirar o foco do terminal (o editor do `.md` ficava com o teclado no Windows; no Linux, o `xdg-open` herdava o terminal).
  
  Agora o relatório abre minimizado e sem foco, nem o programa aberto nem a notificação usam o teclado da sessão, e o prompt reaparece depois de um relatório.
- **Áudio que não carrega:** quando o pacote de áudio está instalado mas não carrega (o caso comum é o `.venv` recriado com outra versão do Python), a Nora mostra a causa real, em vez de "Falta a parte de áudio".
- **Busca por trecho na agenda e no `listar --contendo`** ([#3](https://github.com/Gabitoprof/Nora/issues/3)): "Álgebra" agora acha "álgebra", e `_` e `%` não funcionam mais como curingas.
- **Modo jogo:** se nenhuma nuvem responder, a Nora não volta a usar o cérebro local (que ocuparia a placa de vídeo); a pergunta vira pendência e, ao sair do modo jogo, ela oferece retomar.
- **Comando com pedido:** "use o Claude para explicar fotossíntese" responde a pergunta, em vez de só trocar o modo; "como sair do modo jogo?" é respondida, não executada.
- **Resposta que cai no meio:** nada de duas respostas emendadas. A resposta fica marcada no histórico (`"situacao"`) e não vai para a memória.
- **Ctrl+C** no meio de uma resposta guarda a pendência na hora; **retomar** uma resposta conta como "ocupada" para o relatório diário.
- **Relatório diário:** não traz o texto das perguntas (relatórios antigos são limpos); só conta como mostrado depois de aparecer; arquivo ausente ou ilegível continua pendente e não derruba a conversa.
- **Apagar pela conversa:** a memória não regrava mais o fato apagado nem anota o próprio pedido de apagar.
- No `nora ouvir`, o texto digitado é lido mesmo com o microfone captando sem parar.

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
