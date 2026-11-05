# Homologação cumulativa da Nora

## Estratégia de desenvolvimento e aceite

A homologação final será integrada, ao término da implementação planejada, no Windows
com GPU AMD, cobrindo todos os módulos em conjunto. Durante o desenvolvimento:

- Criar e executar testes de unidade, integração e regressão adequados a cada alteração.
  Preservar os testes das funcionalidades existentes; não desabilitar testes para passar CI.
- Exigir CI verde em Windows e Linux no commit avaliado antes de considerar um PR pronto.
  A matriz atual usa Ubuntu e Windows com Python 3.11 e 3.13.
- Fazer testes manuais pontuais somente quando indispensáveis para hardware ou integração
  externa. Registrar os demais na homologação final, sem interromper o desenvolvimento.
- Atualizar este checklist por módulo com evidência, commit/ambiente, resultados automatizados,
  testes manuais aprovados, falhos e pendentes. Registrar também testes ignorados ou não executados.
- CI verde comprova os checks executados; uma funcionalidade só será considerada homologada
  após os critérios funcionais aplicáveis e a homologação integrada final.
- Preservar aprovações manuais já registradas. Repetir somente quando uma alteração afetar
  diretamente o componente validado, registrando a mudança e o motivo da repetição.
- Integração à `main` e publicação de releases exigem aprovação explícita do proprietário.
  Permanecem as restrições de não fazer merge, criar tags ou publicar automaticamente.

## Evidências automatizadas de referência

- Commit `77905e6`: [CI aprovada nos quatro ambientes](https://github.com/Gabitoprof/Nora/actions/runs/41758193076).
- Linux/Python 3.12.14 no código de `71cf727` (seguido de documentação em `77905e6`):
  `ruff format --check .` e `ruff check .` aprovados; `pytest`: **266 aprovados, 1 ignorado**
  (Kokoro real, sem modelo). `nora --verificar`: código 0, com serviços reais ausentes.
- Estes resultados são históricos dos commits indicados, não aprovação automática de commits futuros.
- Casos detalhados AJ-01–AJ-03 e A1–A6: [checklist da correção](CHECKLIST_HOMOLOGACAO_AJ01_AJ03.md).

## Checklist por módulo

Nenhuma aprovação manual foi informada nesta sessão. “Sem registro” não significa que o
proprietário nunca tenha testado; uma evidência fornecida deve ser incorporada e preservada.
A coluna automatizada refere-se à suíte de referência acima, não a modelos ou dispositivos reais.

| Módulo | Resultado automatizado / cobertura | Manual aprovado registrado | Pendente para homologação integrada |
|---|---|---|---|
| Configuração e CLI | Suíte aprovada: configuração, `.env.example`, comandos e diagnóstico | Sem registro | Conferir diagnóstico com os serviços/configuração reais, sem expor segredos |
| Conversa e roteamento | Suíte aprovada: streaming, reservas, erros e continuidade | Sem registro | Conversa com Ollama e provedores externos configurados |
| Memória e pendências | Suíte aprovada: fatos, curadoria, agenda, esquecer/apagar, Ctrl+C e retomada | Sem registro | Persistência entre sessões, interrupção real e busca com bge-m3 |
| Notas do Obsidian | Suíte aprovada: índice e consulta | Sem registro | Indexar e consultar pasta de teste representativa no Windows |
| Entrada, ativação e STT | Suíte aprovada: VAD, ativação, teclado e loops de conversa | Sem registro | Microfone/whisper.cpp, silêncio prolongado, teclado durante alerta, Ctrl+C, acentos e entradas seguidas |
| Voz e TTS | Suíte aprovada com simulações e arquivos de áudio; Kokoro real ignorado | Sem registro | Kokoro/Piper/ElevenLabs disponíveis, pronúncia, emoções, troca de voz, reserva e reprodução |
| Modo jogo e GPU | Suíte aprovada: confirmação de saída, sem fallback local e oferta de retomada | Sem registro | Liberação de VRAM na GPU AMD, falha de nuvem sem reativar Ollama e retomada após confirmação |
| Autoaperfeiçoamento supervisionado | Suíte aprovada: métricas, propostas, decisões, privacidade e geração de tarefa | Sem registro | Ciclo diário integrado e decisões sem mudança automática de código |
| Relatórios e notificações | Suíte aprovada: AJ-01–AJ-03, LF/CRLF, recuperação manual, leitura e espera | Sem registro | Horário agendado com Nora ociosa/ocupada/em jogo, reinício, abertura do Markdown e toast/clique reais |

P3 e P4 seguem fora do escopo. A HUD v0.4.0 foi autorizada posteriormente pelo proprietário,
conforme plano técnico e PNG oficial; não amplia o escopo para MCP, rotinas ou operação distribuída.

## Registro cumulativo de testes manuais

Ao receber ou executar um teste manual, acrescentar uma linha sem apagar o histórico.
Dados de teste devem ser sintéticos; não guardar perguntas pessoais, áudio, chaves ou tokens.

| Módulo/caso | Commit ou versão testada | Ambiente e configuração relevante | Resultado e evidência | Alteração que exige repetir |
|---|---|---|---|---|
| Nenhuma execução manual registrada nesta sessão | — | — | Pendente de evidência | — |

## Homologação final integrada — Windows/AMD

- [ ] Definir o commit candidato e confirmar a CI Windows/Linux desse commit.
- [ ] Reunir aprovações manuais anteriores e identificar os componentes diretamente afetados.
- [ ] Executar os cenários pendentes por módulo com todos os serviços integrados.
- [ ] Validar conversa, memória, voz, interrupções, modo jogo, relatórios e decisões supervisionadas
  no mesmo fluxo; conferir reinício e recuperação após falhas.
- [ ] Registrar resultados reais, limitações e falhas encontradas; corrigir e retestar as afetadas.
- [ ] Obter aceite do proprietário para integração à `main` e autorização separada para publicação.

## HUD v0.4.0 — execução atual

Branch `feat/v0.4.0-hud`, base `Pull_code` no commit `70d39b7`.
O PNG fornecido na conversa é a referência oficial; comparação visual qualitativa por
agentes de design e QA. Sem medição de diferença pixel a pixel por ausência do arquivo
PNG local. Mock de teste não representa estado real em runtime.

| Módulo HUD | Automatizado nesta entrega | Manual aprovado registrado | Pendente Windows/AMD |
|---|---|---|---|
| Contrato Python/TypeScript | JSON compartilhado, validação versão/ordem/Unicode; testes Python e TypeScript aprovados | Sem registro | Não exige repetição manual por si só |
| Ponte SSE local, reconexão e limites | HTTP/SSE real e reconexão aprovados; filas/cliente lento e limites testados | Sem registro | Reconexão com serviços reais em uso |
| Host/Origin/token e privacidade | 14 verificações HTTP de QA aprovadas, além de testes persistidos; opt-in/out ponta a ponta aprovado | Sem registro | Conferir tela compartilhada e opt-in |
| Ondas/partículas WebGL e Canvas | Capturas desktop/ultrawide/móvel revisadas; fallback automático sem WebGL aprovado | Sem registro | Aparência no monitor alvo, desempenho com LLM/STT/TTS |
| Estados, voz e amplitude do pipeline único | RMS/callback de reprodução, CLI e regressões aprovados com dispositivos simulados | Sem registro | Microfone/alto-falante e reserva reais, sem segundo dispositivo |
| Texto e palavras estimadas | Consentimento, escape de HTML, fim de fala e estimativa visual verificados no browser | Sem registro | Legibilidade e conforto; não alegar sincronismo fonético |
| Propostas e decisões supervisionadas | Domínio Melhorias real: cancelar não decide, confirmar decide sem alterar código | Sem registro | Ciclo integrado com auto-melhoria ativa e relatório diário |
| Notas usadas e autorizadas | Filtragem de pasta/consentimento testada; painel usa somente notas da resposta | Sem registro | Pasta real explicitamente configurada, sem exposição indesejada |
| Responsividade, acessibilidade e movimento reduzido | Quatro viewports sem overflow, campos móveis 12px, zero pageerrors; movimento reduzido e página oculta sem desenhos | Sem registro | Tela cheia ultrawide e preferências de acessibilidade no Windows |

Não liberar v0.4.0 antes da homologação final integrada. Não repetir aprovações manuais
anteriores sem impacto direto; nenhuma aprovação física foi registrada nesta conversa.

### Evidências de QA da HUD

- Browser Chromium headless, via Playwright, com dados sintéticos de teste; servidor Python
  e domínio de melhorias reais no teste ponta a ponta. Não usa hardware nem serviços de IA reais.
- 13 verificações ponta a ponta aprovadas: SSE, estado/emocão/nível, XSS escapado, consentimento,
  palavras estimadas, limpeza ao ocultar/fim de fala, confirmação/cancelamento, reinício e
  reconexão com sequência reiniciada, sem persistência no navegador ou falso núcleo conectado.
- Desktop 1672×941, ultrawide 2560×1080, móvel 390×844 e movimento reduzido: sem overflow
  horizontal, sem erros de página, localStorage/sessionStorage vazios.
- Fallback Canvas forçado sem WebGL: 33 desenhos em 1500ms (~22 FPS observados, limite 30)
  neste ambiente headless concorrente. Modo jogo: 11/1500ms (~7,3 FPS, limite 8).
  Página oculta: 0 desenhos/500ms; movimento reduzido: 0/1500ms. Não extrapolar para GPU AMD.
- Arquivos de captura e harness desta sessão em `/workspace/scratch/qa-hud/` (fora do Git).
  A comparação com o PNG foi qualitativa, pelos agentes de design/QA e pela revisão principal.
- Correções durante QA: snapshot desconectado não finge núcleo ativo; toggle privacidade
  usa resposta autoritativa sem reverter SSE mais recente, com duas regressões persistidas; legibilidade móvel;
  largura/assimetria dos filamentos; proxy de desenvolvimento local; limites Unicode e MIME.
- Empacotamento wheel conferido: `nora/hud.py` e `nora/hud_contrato.json` presentes.
- CI da nova branch deve ser confirmada no commit enviado antes de declarar o PR pronto.
  Aprovação antiga de `77905e6` não valida a implementação da HUD.

### Resultado automatizado local da implementação HUD

- Python 3.12.14/Linux: **295 aprovados e 1 ignorado** (`pytest -ra`), incluindo 29 testes
  novos da ponte, HTTP/SSE, domínio, áudio, CLI, Unicode e MIME. O ignorado continua sendo
  Kokoro real sem modelo; não é aprovação de TTS físico.
- `ruff format --check .` e `ruff check .`: aprovados. `nora --verificar`: código 0,
  com Ollama, Whisper e Kokoro indisponíveis; credenciais opcionais não configuradas.
- Frontend: `npm ci`, lint, typecheck, **15 testes Vitest** e build aprovados.
  Inclui contrato compartilhado, eventos fora de ordem, Unicode, reconexão/token e duas
  condições de corrida entre o consentimento HTTP e eventos SSE mais recentes.
- Desenho usa Three.js/WebGL, Canvas automático se WebGL não existir ou perder contexto.
  Capturas de QA verificam responsividade e identidade; aprovação estética final pertence
  ao proprietário e a medição de GPU/latência integrada permanece pendente.

### CI e revisão final da entrega

- Commit de implementação `a81065f`: seis jobs aprovados na
  [execução 41911978525](https://github.com/Gabitoprof/Nora/actions/runs/41911978525):
  núcleo Windows/Ubuntu com Python 3.11/3.13 e frontend Windows/Ubuntu com Node 22.
- QA final reaprovou 13 verificações ponta a ponta, a corrida HTTP/SSE determinística e
  5 verificações de notas autorizadas/latência. Sem erros de página ou storage pessoal.
- Último ajuste visual: painel móvel ampliado para não cortar “Conteúdo protegido” após
  incluir a linha de latência; verificação de geometria no browser e captura atualizadas.
- Proxy Vite: configuração implementada; smoke final específico não confirmado nesta rodada.
  O caminho principal homologado automaticamente usa build servida pelo Python na mesma origem.
- Criação de PR ainda bloqueada externamente: API GraphQL retornou `Forbidden`.
  [Formulário com branches preenchidas](https://github.com/Gabitoprof/Nora/compare/Pull_code...feat/v0.4.0-hud?expand=1).
- Isso não aprova merge, tag, release nem homologação física Windows/AMD.

### Evidência manual informada pelo proprietário — instalação Windows

- Capturas do proprietário confirmam criação do ambiente Python 3.13 e instalação
  editável dos extras `dev,voz,memoria` concluída com sucesso.
- `pip check`: **aprovado**, com `No broken requirements found`. Não pedir repetição
  dessa verificação sem alteração direta no ambiente/dependências.
- `nora.exe --verificar`: **bloqueado pelo Controle de Aplicativos do Windows**;
  não classificar como erro da Nora nem como diagnóstico funcional aprovado.
- Orientada a entrada oficial `python -m nora --verificar`, sem alterar políticas;
  resultado no computador do proprietário ainda pendente. A forma como módulo foi
  executada no ambiente Linux, código 0; isso não substitui a confirmação local.
- Instalação aprovada não homologa microfone, STT/TTS, GPU ou integração completa.

### Correção de abertura por link e ferramentas da HUD

- Evidência do proprietário: `npm ci` e build da HUD concluídos no Windows; não repetir
  investigação de compilação como se ela tivesse falhado. Servidor iniciou, mas navegador
  recebeu HTTP 403 `Origem local obrigatória`; abertura da interface **reprovada nessa versão**.
- Reproduzido antes da correção: quatro cliques Chromium em páginas de outra origem
  para `/` e `/index.html` retornaram 403 com `Sec-Fetch-Site` cross-site/same-site,
  `Sec-Fetch-Mode: navigate`, `Sec-Fetch-Dest: document` e sem Origin.
- Corrigido somente o documento público inicial. Quatro casos de navegador passaram
  após a mudança, incluindo assets/SSE/consentimento na própria origem e zero pageerrors.
  API de estado/token, POST externo, iframe e link diretamente à API continuam 403.
- Novas regressões HTTP: 12 casos; suíte HUD: **41 aprovados**. Suíte completa Linux/Python
  3.12: **307 aprovados e 1 ignorado** (Kokoro real). Ruff format/check aprovados e
  `python -m nora --verificar` executado com código 0, sem serviços físicos nesta máquina.
- QA repetiu as 13 verificações ponta a ponta e a corrida HTTP/SSE de privacidade:
  aprovadas. Não substitui integração física Windows/AMD.
- Auditoria npm inicial confirmou os 10 alertas do proprietário (8 moderados, 2 críticos).
  Vitest/ESLint atualizados explicitamente; minimatch transitivo fixado no intervalo
  vulnerável com testes das APIs consumidas. Sem `audit fix --force` ou testes desabilitados.
- Requisito das ferramentas atualizado para Node LTS 22.13+ ou 24 (ver engines exatos no
  package.json). Manter a matriz CI Windows/Ubuntu e confirmar o commit enviado.
- Evidências de navegador desta sessão: `/workspace/scratch/qa-hud/navigation-before-results.json`,
  `navigation-fixed-results.json`, `external-link-fixed.png` e `FINAL_QA.md`.
- Reteste manual necessário somente da abertura corrigida no navegador do proprietário;
  aprovações anteriores de instalação/pip check permanecem registradas, sem repetir módulos
  não afetados. Voz/GPU e homologação final integrada continuam pendentes.

- Ferramentas após atualização: `npm ci`, lint, typecheck, **19 testes Vitest** e build
  aprovados tanto com Node 24.22.1 quanto com Node 22.23.4. Quatro novos casos verificam
  as APIs minimatch consumidas pelo ESLint/parser, inclusive dotfiles, extensões e negação.
- Auditoria npm completa: **0 vulnerabilidades**; auditoria somente produção: **0**.
  Os avisos anteriores de instalação não foram usados para explicar o HTTP 403: as duas
  causas foram investigadas e corrigidas separadamente. Nenhuma política Windows foi alterada.
