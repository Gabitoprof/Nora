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

As evidências manuais informadas pelo proprietário estão preservadas abaixo. “Sem registro”
indica apenas ausência de evidência para aquele módulo, sem invalidar testes anteriores.
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
| Instalação e dependências | HUD anterior à retomada acústica de 06/11/2026 | Windows, Python 3.13 | Instalação editável concluída e `pip check` aprovado, conforme capturas do proprietário | Repetir somente se dependências/ambiente forem alterados |
| Entrada oficial e diagnóstico | HUD anterior à retomada acústica de 06/11/2026 | Windows, `python -m nora --verificar` | Módulo executado; diagnóstico mostrou Ollama e memória disponíveis, STT indisponível. Não é aprovação integral do diagnóstico | Retestar STT quando seu serviço estiver disponível |
| Abertura e conexão da HUD | HUD anterior à retomada acústica de 06/11/2026 | Windows, navegador conectado ao núcleo | Captura posterior do proprietário confirma interface aberta e núcleo conectado | Mudanças acústicas exigem sua própria validação, sem repetir instalação aprovada |

## Homologação final integrada — Windows/AMD

- [ ] Definir o commit candidato e confirmar a CI Windows/Linux desse commit.
- [ ] Reunir aprovações manuais anteriores e identificar os componentes diretamente afetados.
- [ ] Executar os cenários pendentes por módulo com todos os serviços integrados.
- [ ] Validar conversa, memória, voz, interrupções, modo jogo, relatórios e decisões supervisionadas
  no mesmo fluxo; conferir reinício e recuperação após falhas.
- [ ] Registrar resultados reais, limitações e falhas encontradas; corrigir e retestar as afetadas.
- [ ] Obter aceite do proprietário para integração à `main` e autorização separada para publicação.

## v0.4.0 — preparação da homologação no Windows (branch `integracao/v0.4.0`)

Correções da revisão aplicadas e cobertas por testes automatizados (CI Windows e Linux):
- **Paleta dentro do pacote** (`src/nora/paleta.json`): a HUD e o Second Brain leem o mesmo arquivo; um teste proíbe cópia.
- **Instalação limpa:** `scripts/testar_instalacao_limpa.py` gera o wheel, instala num venv fora do checkout e confere a paleta, o Second Brain e os arquivos do pacote (job `instalacao` no CI, só Linux).
- **Versão única:** `0.4.0.dev0` no Python e `0.4.0-dev.0` na HUD, com teste de divergência. `nora --verificar` (1ª linha) e a HUD (Ajustes) mostram versão e commit.
- **Troca de voz:** a confirmação leva o texto à HUD (teste de regressão).
- **Falhas da HUD:** contadas e registradas uma vez por tipo, sem texto nem áudio; a fala continua.
- **Paleta revisada:** serenidade, sussurro e suspiro em calma; preocupação em seriedade.

**Instalada, fora do repositório:** a config padrão vem dentro do pacote (`src/nora/nora.toml`), e a config pessoal, o `.env`, a memória e os modelos ficam em `%APPDATA%\Nora`, criada na primeira execução. O teste de instalação limpa roda `nora --verificar` assim. O build da HUD vai dentro do `.exe`; numa instalação por wheel a HUD ainda precisa de `NORA_HUD_DIST`.

**Palavras em partículas.** Com o ElevenLabs v4 (padrão), o tempo de cada palavra vem do próprio ElevenLabs (`precisao "alinhada"`). Nas outras vozes, e se o alinhamento não vier, ele é estimado a partir do áudio que toca, e a HUD mostra "tempo estimado no áudio". O passo 7 do roteiro confere o v4 na sua conta.

**ElevenLabs v4: aprovado no PC real.** Os testes automáticos usam um servidor WebSocket falso (streaming numa conexão, alinhamento, `keep_alive`, barge-in, reserva no flash, turno sem áudio, diagnóstico). No Windows, em 06/11/2026, o `eleven_v4_turbo` falou pelo diálogo em tempo real: primeiro áudio em 985 ms, tocando em 1555 ms, 0 ms de silêncio entre trechos, palavras alinhadas. Decisão do Gabriel: usar só o v4, sem comparar com outros modelos.

### 1. Automático (sem você): `scripts/homologacao_windows.ps1`

Na pasta do repositório, com o `.venv` ativado:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\homologacao_windows.ps1
```

Ele roda e grava em `data\homologacao\AAAA-MM-DD_HHMM.txt`:
- versão, commit, GPU e driver;
- `pytest`, `ruff` e a instalação limpa;
- `npm ci`, `npm test` e `npm run build` da HUD;
- `nora --verificar`;
- 30 s de medição com o modelo local carregado e a HUD aberta no navegador: uso da GPU 3D, VRAM, CPU total, CPU do navegador e CPU do Python (média, mínimo e máximo).

Leva uns 5 minutos. No fim, ele diz "Todas as etapas passaram" ou lista as que falharam. Ainda não rodou num Windows de verdade (só no PowerShell 7 para Linux): se algum passo der erro, mande o arquivo assim mesmo.

### Já executado na nuvem, sem o PC do Gabriel (06/11/2026, commit `cf519fc`)

O PC com Windows não estava disponível. Na nuvem (Linux x86_64, 4 núcleos, sem GPU):

| Verificação | Resultado |
|---|---|
| `pytest` | 457 passaram, 2 pulados |
| `ruff format --check` e `ruff check` | sem erros |
| HUD: `npm ci`, `lint`, `typecheck`, `npm test`, `build` | ok; 36 testes |
| Instalação limpa (wheel fora do checkout) | ok, `nora 0.4.0.dev0` |
| `nora --verificar` | 1ª linha: `Versão: 0.4.0.dev0 (commit cf519fc)` |
| CI #170 (Windows e Linux, 7 jobs) | todos verdes |
| HUD (Ajustes) | `Nora 0.4.0-dev.0 · commit cf519fc`, igual ao Python |

Desempenho da HUD aberta (`nora hud` real + build real, Chromium sem tela, 1600×900, 30 s por medição; script e números em [`evidencias/hud-acustica/desempenho-nuvem/`](evidencias/hud-acustica/desempenho-nuvem/)):

| Qualidade | Limite | FPS desenhado | CPU do navegador | CPU da Nora |
|---|---|---|---|---|
| Detalhada (WebGL) | 30 | 16,8 | 84% da máquina | 0% |
| Detalhada (WebGL) | 60 | 16,7 | 85% da máquina | 0% |
| Econômica (WebGL) | 30 | 23,2 | 82% da máquina | 0% |

**Como ler:** sem GPU, o WebGL é calculado na CPU (SwiftShader), então o FPS fica preso pela CPU (~17 em vez de 30) e o navegador ocupa quase toda a máquina. Isso é o pior caso, não uma medida da RX 9060 XT. O que vale como resultado:
- a Nora (Python) não gasta CPU com a HUD aberta: o desenho fica todo no navegador, outro processo;
- a qualidade Econômica rende ~40% mais quadros no mesmo hardware;
- nenhum erro de página.

**Script do Windows conferido no PowerShell 7.4 para Linux:** a sintaxe está ok, e a versão sem medição (`-SemDesempenho`) rodou de ponta a ponta, com as 7 etapas ok, a linha de versão e commit e o arquivo em UTF-8. Uma etapa que falha aparece como `FALHOU` e no resumo final; isso foi testado com um `ruff` falso. O PSScriptAnalyzer não está disponível aqui (a PowerShell Gallery é bloqueada), então a compatibilidade com o PowerShell 5.1 do Windows foi revisada à mão.

**Continua pendente no PC do Gabriel:** rodar o script num Windows de verdade, incluindo os contadores de GPU (só existem no Windows); FPS, GPU e VRAM reais; e todo o roteiro abaixo, que precisa de microfone, alto-falante e ElevenLabs.

### 2. Roteiro com você (~15 min)

Antes: `git pull`, `.venv\Scripts\activate`, Ollama aberto, ElevenLabs como voz principal, Second Brain ligado (`[segundo_cerebro] ativo = true`) e a HUD visível (`nora ouvir --hud`, abrir o endereço que aparecer).

| # | Faça | Observe | Resultado |
|---|---|---|---|
| 0 | Anote a 1ª linha de `nora --verificar` e a versão em Ajustes da HUD | Mesma versão e mesmo commit nos dois | |
| 1 | Diga "Nora, que dia vai ser daqui a 23 dias?" | Responde a data certa; a onda reage à sua voz (prata, "Ouvindo"), muda em "Pensando" e fala com outra forma | |
| 2 | Fale baixo e depois normal | O painel "Sinal de áudio" acompanha, sem ficar em 0% com a onda se mexendo | |
| 3 | Peça algo longo ("me conta uma história curta") | O áudio começa rápido (streaming); as palavras em partículas seguem a fala e param nas pausas, sem adiantar | |
| 4 | Fale por cima da Nora no meio da resposta | Ela para (barge-in) ou, se ainda não houver barge-in no seu modo, anote o que acontece | |
| 5 | "Troque para a voz do Piper" e depois "volta pro ElevenLabs" | A confirmação aparece na HUD (texto e palavras) e a voz troca | |
| 6 | "Modo jogo" → "sim, sair do modo jogo" | A HUD mostra o modo jogo; `ollama ps` sem o modelo carregado durante o jogo | |
| 7 | ElevenLabs v4: `nora --verificar` e uma resposta com `nora falar --medir` | "Modelo efetivo eleven_v4_turbo (diálogo...)", "Continuidade ElevenLabs ativa" e a linha `[voz: ...]` sem `[voz reserva]` | ✅ 06/11: 985 ms até o 1º áudio, 1555 ms tocando, 0 ms de silêncio, palavras alinhadas |
| 8 | Diga um fato novo ("eu estudo com a Ana às quartas") e depois "mostre seu segundo cérebro" | A nota aparece no vault em até ~1 min, sem pausa na fala; o mapa abre | |
| 9 | Durante tudo isso, com a HUD aberta | Alguma travada, eco ou pausa na fala? FPS (Edge/Chrome: F12 → Ctrl+Shift+P → "Show frame rate") | |

Mande o arquivo do passo 1 e a coluna Resultado (pode ser foto). Problemas viram correções com teste antes da aprovação.

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
anteriores sem impacto direto. A abertura/conexão no Windows foi informada pelo proprietário;
voz, dispositivos e GPU ainda não foram homologados.

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
  resultado posteriormente informado: módulo executado, Ollama e memória disponíveis, STT
  indisponível. Isso não homologa os serviços faltantes nem a reprodução de voz. A execução
  Linux com código 0 continua sendo uma evidência separada.
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

## Roadmap "Imagem para as falas": fases 0 e 1 (validar e corrigir)

Branch `integracao/v0.4.0`. Cada item tem commit próprio; o que depende do PC do Gabriel está marcado.

| # | Item | Estado | Evidência |
|---|---|---|---|
| 1 | Offsets do alinhamento v4 | Corrigido e testado com servidor falso (vários trechos, offsets conhecidos) | `tests/test_voz_v4.py` (referência por turno, trechos, silêncio inicial) |
| 2 | Reserva no meio da fala | Implementado: antes do áudio / depois (continua do limite) / sem limite (para e permite repetir) / sem alinhamento (segue tocando) | `tests/test_voz_v4.py` (servidor que cai no meio, cancelar e retomar sem palavras repetidas) |
| 3 | Diagnóstico (`--verificar`, `--medir`, log) | Modelo efetivo, continuidade, motivo de cada reserva, gerações por resposta, tempos (pedido, 1º PCM, reprodução, silêncio entre trechos) nos dois caminhos | `tests/test_voz_v4.py` (diagnóstico com reserva no meio, HTTP, arquivo antigo; sem texto nem chave) |
| 4 | Retenção nas pausas | Palavra até a próxima começar, teto `TETO_PAUSA_MS` = 1,5 s; some na hora em `reproducao_encerrada`, cancelamento e Privado | `hud/tests/text-particles.test.ts` |
| 5 | Relógio da fala | Medido e ajustado: 450/400 ms e recuos < 60 ms ignorados (tabela abaixo) | `hud/tests/relogio-medicao.test.ts` |
| 6 | Testes de estado (`reproducao_encerrada`) | Ordem, duplicidade, reconexão, privacidade e mensagem atrasada depois do Privado | `hud/tests/state.test.ts` |
| 7 | Privacidade no backend | Palavras só publicadas com a tela autorizada; revogar invalida a fala em curso (época) e esvazia as filas; Privado nem guarda as palavras. Leitura sem segredo de sessão: proposta abaixo | `tests/test_hud.py`, `tests/test_hud_acustica.py` |
| 8 | QA visual | Palavras longas e acentos legíveis em 1920×1080 (faixa de 1060 px) e 1366×768 (902 px); legível em ~116 ms | `docs/evidencias/palavras-1920x1080.jpg`, `palavras-1366x768.jpg`; `hud/tests/text-particles.test.ts` |
| 9 | Medição no PC (preparada) | Telemetria na HUD + `homologacao_windows.ps1` (base × HUD, contínuo) | **Pendente: Gabriel roda** |

Documentação oficial do ElevenLabs inacessível na nuvem (domínio bloqueado). O SDK oficial
(`elevenlabs` 2.77.0) documenta, no WebSocket de TTS, tempos **relativos ao trecho devolvido**; o
tipo do diálogo não descreve. O código aceita as duas referências e fixa a escolhida no turno.
**Pendente no PC:** confirmar com o v4 real (a linha `[voz: ...]` e a HUD mostram as palavras no
tempo certo em respostas longas, de vários trechos).

### Item 5: medição do relógio da fala

Simulação determinística (`hud/tests/relogio-medicao.test.ts`): 60 s de fala, palavras de 260 ms a
cada 300 ms, amostras do backend a cada 50 ms, atraso de rede de 5 a 45 ms, engasgos (nenhuma
amostra) de 150 a 450 ms em 0%, 1% ou 3% das amostras, desenho a 60 FPS.

| Idade máx. / extrapolação | Engasgos | Atraso som→palavra p50 / p95 / pior | Palavras perdidas | Recuos |
|---|---|---|---|---|
| 300 / 250 (antes) | 3% | 33 / 50 / 217 ms | 1 | ~140 (antes da tolerância) |
| **450 / 400 (agora)** | 3% | 33 / 50 / 100 ms | 0 | 0 |
| 600 / 500 | 3% | 33 / 50 / 83 ms | 0 | 0 |

Escolha: 450/400. Extrapolar mais (600/500) ganha pouco e adianta palavras quando a rede atrasa de
verdade (o backend não publica amostras durante falta de áudio). O atraso medido não inclui a
latência real da saída de áudio do Windows: **pendente no PC** (roteiro abaixo).

### Item 7: a ponte da HUD exige segredo de sessão?

**Achado:** só para **alterar** (privacidade, decisões): cabeçalho `X-Nora-Token`. A **leitura**
(`/api/eventos`, `/api/estado`, `/api/notas`, `/api/propostas`) é protegida por outras barreiras:
`Host` precisa ser `127.0.0.1:porta` (bloqueia DNS rebinding), `Origin` de outro site é recusada e
`Sec-Fetch-Site` cross-site/same-site é recusado. Contra **páginas da web** isso basta (o navegador
sempre informa a origem; testado). O ponto fraco é outro **programa local** (não navegador) no
mesmo computador: ele pode ler os eventos e até pegar o token em `/api/sessao`.

**Proposta (não aplicada: muda como a HUD é aberta):**

1. A Nora gera o token e abre a HUD com ele no **fragmento** do endereço
   (`http://127.0.0.1:8765/#sessao=TOKEN`): o fragmento não vai ao servidor nem aos logs.
2. A página guarda o token em `sessionStorage` e o manda em toda leitura (`X-Nora-Token`; nos
   eventos, num primeiro pedido que troca o token por um bilhete de uso único, porque o
   `EventSource` não manda cabeçalhos).
3. `/api/sessao` deixa de existir. Abrir `http://127.0.0.1:8765/` sem o token mostra só a página
   pedindo para abrir pela Nora (atalho do menu Iniciar ou o link que `nora ouvir --hud` imprime).

Custo: favoritos antigos para a HUD param de funcionar; o atalho e o terminal passam a mostrar o
link com o token. Decisão do Gabriel.

### Item 8: QA visual das palavras

Renderizadas com o código real da faixa (`CampoParticulasTexto`), na largura que a faixa ocupa em
cada resolução (`min(66vw, 1060px)`), com palavras já ditas à esquerda:

| Resolução | Faixa | Altura da palavra atual | Palavra de 27 letras |
|---|---|---|---|
| 1920×1080 | 1060 px | ~70 px | 54 px, legível |
| 1366×768 | 902 px | ~60 px | 46 px, legível |

Acentos (ç, ã, é, ú) e pontuação aparecem. As palavras já ditas ficam entre 13 e 16 px:
legíveis, mas discretas de propósito. **Tempo até ficar legível** (90% dos pontos a menos de 3 px
da letra, saindo da poeira longe): antes ~380 ms; agora ~116 ms (meta ≤ 150 ms).
**Pendente no PC:** a mesma conferência na HUD inteira, com a fala real e na tela do Gabriel.

### Item 9: medição no PC do Gabriel (preparado; ele executa)

Tudo com a Nora real: Qwen, Whisper e ElevenLabs ligados ao mesmo tempo.

1. Terminal 1 (em `B:\Nora`): `scripts\iniciar_voz_windows.ps1 -Voz nenhuma` (o ouvido).
2. Terminal 2, com o `.venv` ativado: `nora ouvir --hud`. Na HUD: **Visível**, qualidade
   **Detalhada**, **60 FPS**, "Palavras em partículas" marcado.
3. Terminal 3, com o `.venv` ativado:
   `powershell -ExecutionPolicy Bypass -File scripts\homologacao_windows.ps1 -SoMedir -Continuo`
   - fase 1 (60 s): ele pede para **fechar a aba da HUD** (base);
   - fase 2 (60 s): ele pede para **abrir a HUD e conversar** usando o roteiro do item 10;
   - depois, o teste contínuo de 25 min: deixe a HUD aberta e converse de vez em quando.
4. Mande o arquivo `data\homologacao\AAAA-MM-DD_HHMM.txt` e a planilha `..._continuo.csv`.

| Medida | Onde sai | Meta |
|---|---|---|
| Tempo de quadro p50 / p95 / pior | HUD (`diagnostico_hud.json`) | p95 ≤ 33,3 ms |
| Atraso som → palavra p50 / p95 | HUD | p95 ≤ 100 ms |
| CPU a mais da HUD | script (com HUD − base) | ≤ 10 pontos percentuais |
| VRAM a mais da HUD | script | ≤ 256 MB |
| Memória, VRAM, quadro e contextos WebGL no início × fim (25 min) | script `-Continuo` | sem subida contínua; contextos estáveis |

Os mesmos números aparecem nos Ajustes da HUD (linha "Quadro p50 / p95 / pior"). O atraso som →
palavra é medido pela própria HUD (quanto do áudio da palavra já tinha tocado quando ela apareceu);
não inclui a latência da placa de som.
