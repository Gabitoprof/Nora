# Release v0.3.0 — Roteador de modelos

Preparação da versão estável `v0.3.0` a partir do branch `Pull_code`, com Pull Request para `main`. **Merge, tag e publicação só com a autorização final do mantenedor.**

## 1. Notas de lançamento

**A Nora agora tem dois cérebros que trabalham juntos.** A conversa do dia a dia continua no seu PC, de graça e privada. As perguntas difíceis vão para a nuvem e voltam com a mesma voz, a mesma personalidade e a mesma memória.

### Novidades

- **Roteador de modelos:**
  - o cérebro local (Ollama) conversa; código, contas, análises, planos e textos longos vão para o **ChatGPT**, com o **Claude** de reserva, e o local é a última reserva;
  - enquanto a nuvem pensa, ela diz uma frase de espera;
  - se você reclamar de uma resposta do local ("tá errado"), a pergunta ganha uma segunda chance na nuvem.
- **Comandos falados:**
  - "use o cérebro local", "use o ChatGPT", "use o Claude", "modo automático";
  - "use o Claude para explicar fotossíntese" responde só aquela pergunta no Claude;
  - **modo jogo:** libera a placa de vídeo e responde pela nuvem. Para sair, ela pede confirmação, e nunca volta a usar a placa sozinha.
- **Emoção na voz:** ela escolhe o tom de cada frase. No ElevenLabs v3, ri, suspira e sussurra de verdade.
- **Trocar a voz falando:** "troque para a voz do Piper", "volta pro ElevenLabs".
- **Notas do Obsidian:** ela lê o seu vault (só leitura) e usa as notas para responder, dizendo de qual nota veio.
- **Esquecer e apagar de vez:** "esquece isso" faz ela parar de usar o assunto; "apaga de vez ..." mostra o que vai sair e só apaga depois do seu "sim".
- **Nenhuma resposta perdida:** se uma resposta cai no meio, é cancelada ou fica sem resposta, a pergunta fica guardada. "Termina a resposta que ficou pela metade" responde de novo, inteira.
- **Auto-melhoria supervisionada:**
  - uma vez por dia, ela junta o que deu errado (falhas, lentidão, reclamações) num relatório de propostas, sem guardar o texto das conversas;
  - você aprova, recusa ou adia; nada muda no código sem você;
  - nesta versão, sem internet e sem modelo de IA no diagnóstico.

### Correções desta preparação de release

- **Enter no `nora falar` com a auto-melhoria ligada:**
  - um erro ao apresentar o relatório deixava para trás a leitura do teclado, e o Enter seguinte (o de parar de gravar) se perdia;
  - abrir o relatório podia tirar o foco do terminal.
  
  Agora o relatório abre minimizado e sem foco, e o prompt reaparece depois dele.
- **Busca por trecho na agenda e no `listar --contendo`** ([#3](https://github.com/Gabitoprof/Nora/issues/3)): maiúsculas acentuadas ("Álgebra" acha "álgebra") e sem curingas `_`/`%`.

### Como atualizar

```bash
git pull
```

```bash
python -m pip install -e ".[voz,memoria,nuvem]"
```

```bash
nora --verificar
```

A nuvem é opcional: precisa de `OPENAI_API_KEY` e/ou `ANTHROPIC_API_KEY` no `.env`. Sem chave nenhuma, tudo continua no PC. Não há migração manual: os bancos ganham as tabelas novas sozinhos (`respostas_pendentes`, `esquecidos`, `data/auto_melhoria/`).

## 2. Relatório de qualidade

### Escopo

- **Base:** `Pull_code` em `70d39b7` (com o PR #4 já integrado), mais os commits desta preparação.
- **Fora do release:** nenhum commit do branch `feat/v0.4.0-hud`. Conferido com `git log Pull_code..feat/v0.4.0-hud`: 5 commits, nenhum no `Pull_code`. O `hud/README.md` é o marcador da fundação, já presente na `main`.
- **Fora de escopo, por decisão anterior:**
  - P3 (pesquisa técnica na web);
  - P4 (desenvolvimento automatizado);
  - integração pessoal com o Claude Code;
  - a HUD.

### Auditoria final

| Verificação | Resultado |
|---|---|
| Regras do `CLAUDE.md` (pt-BR, Conventional Commits, nada pessoal no Git, licenças, `.env.example`, nada só-CUDA) | Ok. Nenhum arquivo de `data/`, `.env` ou `config/local.toml` versionado; nenhum segredo encontrado; "Jarvis/Marvel" só nas regras que os proíbem |
| Licenças das dependências (`tests/test_licencas.py`) | Ok. Dependências novas da etapa: `openai` e `anthropic` (Apache-2.0), no extra `nuvem` |
| Variáveis de ambiente (`tests/test_env_exemplo.py`) | Ok |
| Testes sem os pacotes opcionais (anthropic, openai, numpy, sqlite-vec) | Ok |
| Regressão do Enter no `nora falar` com auto-melhoria | **Encontrada e corrigida** (seção 2.1) |
| Issue aberta [#3](https://github.com/Gabitoprof/Nora/issues/3) | **Reproduzida e corrigida** |
| Correções anteriores (A1–A6, P1/P2, auditoria, AJ-01–AJ-03) | Preservadas; todos os testes de regressão passam |
| Documentação da etapa (README, roadmap, objetivo, mapa mental `.md` e `.canvas`, guias, banco de ideias, CHANGELOG) | Revisada para o estado da v0.3.0 |

### 2.1 Regressão do Enter no `nora falar`

Com a auto-melhoria ligada (padrão), o PR #4 passou a ler o teclado numa thread de apoio (`melhorias.py::ler_entrada`), enquanto o laço da sessão apresenta os relatórios. Encontrei três caminhos em que um Enter se perdia:

| Causa | Como foi confirmada | Correção |
|---|---|---|
| Um erro ao apresentar o relatório escapava do `ler_entrada`, e a thread de leitura ficava viva e engolia o Enter seguinte (o de parar de gravar). No `nora falar`, o erro também derrubava a conversa | **Reproduzida** por teste com um teclado que bloqueia como o real (`test_falha_ao_apresentar_nao_deixa_leitor_orfao_que_engole_o_enter`) | O erro é registrado (só o tipo) e o `ler_entrada` só volta com a linha que a sua própria thread leu |
| O modo `abrir` (padrão) abria o `.md` com foco no Windows, e o Enter ia para o editor. No Linux, o `xdg-open` herdava o terminal da Nora | Leitura do código (`os.startfile` sem `show_cmd`; `Popen` herdando stdin). O foco no Windows **não pode ser reproduzido na nuvem** | Windows: abre **minimizado e sem ativar** (`SW_SHOWMINNOACTIVE`). Outros sistemas: sem stdin, stdout e stderr, em sessão própria. Teste: `test_abrir_o_relatorio_nao_rouba_o_teclado_da_sessao` |
| O PowerShell da notificação herdava o teclado do console | Leitura do código (`subprocess.run` sem `stdin`) | `stdin=DEVNULL` (mesmo teste) |
| (Usabilidade) Um relatório mostrado durante a espera escondia o "[Enter para falar]" | Teste | O prompt é reimpresso (`test_relatorio_que_aparece_na_espera_mostra_o_prompt_de_novo`) |

Também rodei o laço real do `nora falar` (`conversar_por_voz`, com o `input` verdadeiro) num **pseudo-terminal Linux**, nos modos `abrir` e `terminal`: dois ciclos de Enter para falar e Enter para parar, respondidos e com o prompt de volta, antes e depois da correção. No Linux o fluxo básico já funcionava; o Windows real continua na lista de homologação.

### 2.2 Testes automatizados

| Execução | Resultado |
|---|---|
| `ruff format --check .` | Ok |
| `ruff check .` | Ok |
| `pytest` (Linux, Python 3.12, local) | **270 passaram**, 2 pulados (Kokoro real e um teste de áudio sem dispositivo) |
| `pytest` sem anthropic, openai, numpy e sqlite-vec | **252 passaram**, 13 pulados |
| `nora --verificar` | Código 0 |
| CI GitHub Actions (Windows e Ubuntu × Python 3.11 e 3.13) | Ver seção 2.3 |

Encontrado na homologação (05/11): com o `.venv` recriado em outra versão do Python, o `nora ouvir` dizia "Falta a parte de áudio" com o pacote instalado. A mensagem agora mostra a causa real (`test_audio_que_nao_carrega_mostra_a_causa`).

Testes novos nesta preparação: `test_falha_ao_apresentar_nao_deixa_leitor_orfao_que_engole_o_enter`, `test_relatorio_que_aparece_na_espera_mostra_o_prompt_de_novo`, `test_abrir_o_relatorio_nao_rouba_o_teclado_da_sessao`, `test_busca_por_trecho_ignora_maiusculas_acentuadas_e_nao_usa_curingas`.

### 2.3 CI

Todas as execuções do candidato estão na seção 6. O critério para mudar a versão de `0.3.0.dev0` para `0.3.0` foi a CI verde nas quatro combinações no commit das correções (`389e3cc`).

## 3. Testes manuais pendentes (Windows com GPU AMD)

A CI não tem microfone, alto-falante, GPU, Ollama, whisper.cpp nem as chaves reais. Itens a validar no PC:

**Básico**
- [ ] Antes de tudo: `python --version` no `.venv` ativo mostra **3.13.x**. Na homologação de 05/11, o `.venv` estava com outra versão do Python e os pacotes de áudio compilados para a 3.13 não carregavam (`_cffi_backend`). A saída é recriar com `py -3.13 -m venv .venv --clear` e reinstalar.
- [ ] `nora --verificar` com tudo ok: Ollama, whisper-server, voz principal e reserva, chaves e conexões de ChatGPT e Claude, notas, auto-melhoria.
- [ ] `nora ouvir`: ativação por "Nora", transcrição, resposta falada; digitar com o microfone ligado.

**Regressão do Enter (prioridade)**
- [ ] `nora falar` com um relatório não mostrado (rode antes `nora melhorias fechar-dia` e feche a Nora): ao abrir, o relatório abre **minimizado** na barra de tarefas e o **primeiro Enter** já começa a gravar.
- [ ] `nora falar`: dez ciclos seguidos de Enter para falar e Enter para parar, sem nenhum Enter perdido.
- [ ] Com `hora_relatorio` a 2 minutos dali, deixe a Nora parada em "[Enter para falar]": o relatório aparece (minimizado, ou o texto na tela), o prompt volta e o Enter seguinte funciona.
- [ ] O mesmo com `apresentar = "terminal"`, e no `nora conversar` (texto).
- [ ] Ctrl+C no prompt fecha a Nora normalmente; acentos digitados chegam certos.

**Roteador e voz**
- [ ] Pergunta difícil ("escreve um script python...") → frase de espera → resposta do ChatGPT; com a chave da OpenAI errada, responde o Claude com o aviso `[cérebro]`.
- [ ] "use o Claude para explicar fotossíntese" responde pelo Claude e o modo continua automático.
- [ ] "modo jogo" libera a VRAM (Gerenciador de Tarefas); sem internet, ela avisa e a VRAM continua livre; "sai do modo jogo" pede "sim"; "como sair do modo jogo?" só explica.
- [ ] "troque para a voz do Piper" e "volta pro ElevenLabs"; "o Piper é melhor que o Kokoro?" não troca.

**Memória**
- [ ] "esquece que eu ..." e depois "apaga de vez ..." → "sim, pode apagar"; "não" cancela.
- [ ] `nora notas ler` e uma pergunta sobre uma nota.
- [ ] Ctrl+C enquanto ela pensa → `nora pendencias` mostra a pergunta na hora → "termina a resposta que ficou pela metade".

**Auto-melhoria**
- [ ] A notificação do Windows aparece e o clique abre o relatório. O script de PowerShell nunca rodou num Windows real.
- [ ] O relatório em `data/auto_melhoria/relatorios/` não tem o texto das perguntas.
- [ ] Calibrar com o bge-m3 e a GPU reais os limites `TROCA_ESQUECIDA` (0,6) e `latencia_*_ms`.

## 4. Riscos residuais

| Risco | Impacto | Mitigação |
|---|---|---|
| Alguns programas ignoram o "abrir minimizado e sem foco" (ex.: um editor que já está aberto e traz a própria janela para frente) | O Enter pode ir para o editor, como antes | Validar no PC; se acontecer, usar `[auto_melhoria] apresentar = "terminal"` |
| A notificação do Windows (PowerShell + WinRT) não foi testada em Windows real | A notificação pode não aparecer | A falha fica registrada e o relatório aparece de qualquer forma na sessão |
| Limites calibrados com vetores de teste (`TROCA_ESQUECIDA`, latências) | "Esquecer" pode esconder trechos demais ou de menos; propostas de lentidão podem sair demais ou de menos | Ajustáveis; `nora memoria apagar` mostra antes o que sai |
| A triagem do roteador é por palavras-chave | Algumas perguntas vão para o lugar errado | Segunda chance, comandos e a proposta automática de `rota_suspeita`; o classificador com confiança fica para uma próxima versão |
| O diagnóstico da auto-melhoria é por regras | Propostas genéricas por categoria | Decisão sempre humana; a pesquisa (P3) é opcional e futura |
| A leitura do teclado em thread é nova no `nora falar` | Comportamento de console varia entre terminais do Windows | Testes de regressão e o roteiro manual acima (seção 3) |

## 5. Homologação final e publicação (com autorização)

1. **Baixar o candidato** no PC (com a Nora fechada):
   ```bash
   cd B:\Nora
   ```
   ```bash
   git pull origin Pull_code
   ```
   ```bash
   B:\Nora\.venv\Scripts\python.exe -m pip install -e ".[voz,memoria,nuvem]"
   ```
2. **Fazer os testes manuais** da seção 3 e anotar o resultado de cada item. Se algum falhar, o release para e a correção entra no `Pull_code`.
3. **Revisar o Pull Request** `Pull_code` → `main` e conferir a CI verde no último commit.
4. **Autorizar** (o mantenedor): merge do PR; tag `v0.3.0` no commit do merge na `main`; release no GitHub com as notas da seção 1.
5. **Depois do release:** criar o `0.3.1.dev0` (ou começar a `0.4.0.dev0`) no branch de desenvolvimento.

## 6. Registro da CI

| Commit | Execução | Resultado |
|---|---|---|
| `389e3cc` (correções do Enter e da busca) | [42087432996](https://github.com/Gabitoprof/Nora/actions/runs/42087432996) | Verde: Windows 3.11, Windows 3.13, Ubuntu 3.11, Ubuntu 3.13 (Ruff, pytest, `nora --verificar`) |
