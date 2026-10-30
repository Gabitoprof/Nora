# Changelog

Todas as mudanças relevantes do projeto ficam aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`vMAIOR.MENOR.CORREÇÃO`).

## [Não lançado]

### Alterado

- **O projeto e a assistente passam a se chamar Nora** (antes "Ella"): pacote `nora`, comando `nora`, config padrão `config/nora.toml`, variável `NORA_CONFIG`. O nome "Ella" ("Élha") era transcrito como "Elia", "Ilha" ou "ele" e a palavra de ativação quase nunca funcionava.

Versão em desenvolvimento: `0.1.0.dev0` (mostrada como "0.1.0 (em desenvolvimento)"). Vira `0.1.0` quando o critério da etapa for confirmado: falar o nome, perguntar e ouvir a resposta em menos de 2 s.

### Corrigido

- `nora ouvir` pausa o microfone enquanto a Nora fala. Com fone Bluetooth, o microfone aberto deixa o fone no modo chamada e a voz dela não saía no fone.

### Adicionado

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
- `nora ouvir`: conversa mãos livres (parte 3 da v0.1.0). O Silero VAD (MIT, baixado do PyPI na primeira vez) detecta começo e fim da fala; a fala vira pergunta quando começa com a palavra de ativação ("Nora", aceitando "Ela"); depois de responder, dá para continuar por `janela_s` segundos sem dizer o nome; "tchau" encerra. Config `[escuta]` (`limiar`, `silencio_ms`, `janela_s`).
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
