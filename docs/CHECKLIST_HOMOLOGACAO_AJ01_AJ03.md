# Homologação AJ-01, AJ-02 e AJ-03 — resultado no ambiente Linux

Base conferida: `Pull_code`, `ee5a82e742d95843b0cbfc674c17779d8427eab7` (igual à auditoria).
Branch de correção: `fix/relatorios-aj01-aj03`.

Legenda: `[x]` = verificado no código/testes automatizados deste ambiente;
`[ ] WINDOWS` = exige homologação no computador real;
`[ ] EXTERNO` = depende do GitHub/acesso externo. Uma simulação de abertura/notificação
não comprova a integração real com o Windows.

Validação: `ruff format --check .`, `ruff check .`, `pytest -q -ra` e
`nora --verificar`. Resultado: Ruff aprovado; **265 testes passaram e 1 foi ignorado** (Kokoro real).
`nora --verificar` terminou com código 0, com os serviços externos ausentes listados abaixo.
P3, P4, HUD e integração pessoal Claude Code ficaram fora do escopo.

# Nora — Checklist de testes e homologação da branch `Pull_code`

**Documento de apoio ao Codex e à homologação local.**
**Base:** `REVISAO_NORA_PULL_CODE_POS_CORRECOES.md`, auditoria sobre o commit `ee5a82e` de `Gabitoprof/Nora`.
**Objetivo:** corrigir apenas AJ-01, AJ-02 e AJ-03, preservar o restante, comprovar os testes e preparar um PR para `Pull_code` **sem merge automático**.

## 1. Antes de alterar

- [x] Conferir o HEAD atual de `Pull_code` e comparar com `ee5a82e`; não reaplicar correções já presentes.
- [x] Ler `CLAUDE.md`, `docs/ANDAMENTO.md`, `docs/AUTO_MELHORIA.md` e o relatório de revisão anexo.
- [x] Criar uma branch de trabalho separada, derivada de `Pull_code`.
- [x] Confirmar que P3 (pesquisa na web), P4 (integração de desenvolvimento) e integração pessoal Claude Code estão fora deste PR.

## 2. AJ-01 — Apresentação automática do relatório

- [x] Com `apresentar = "terminal"`, gerar o relatório após `hora_relatorio`: o **texto inteiro** aparece ainda na sessão atual, quando a Nora estiver desocupada, sem pergunta nova e sem reinício.
- [x] Com `apresentar = "abrir"`, o arquivo `.md` é aberto automaticamente no aplicativo associado, quando permitido pelo sistema. **Automatizado com chamadas simuladas; confirmar integração em Windows real.**
- [x] Se a abertura do arquivo falhar, a Nora mostra o conteúdo no terminal na mesma sessão, quando possível, sem derrubar a conversa.
- [x] Enquanto a Nora estiver respondendo ou retomando uma resposta, **não** exibir o relatório nem interromper a interação.
- [x] Durante o modo jogo, não abrir relatórios, não reativar o Ollama e não ocupar a GPU; apresentar posteriormente, ao sair do modo jogo e ficar livre. **Automatizado com chamadas simuladas; confirmar integração em Windows real.**
- [x] Depois de exibido com sucesso, o relatório não é reapresentado na próxima inicialização.
- [x] Se o relatório do dia já foi gerado, não criar uma proposta duplicada por reiniciar o programa.

## 3. AJ-02 — Arquivo ausente

- [x] Criar um relatório de teste e **apagar apenas a cópia temporária**, não dados pessoais nem relatórios de produção.
- [x] O relatório ausente permanece `mostrado = 0` / pendente; a Nora informa a falha.
- [x] Existe procedimento de recuperar/regenerar o relatório com os dados persistidos, ou informar claramente quando a recuperação não for possível.
- [x] Após recuperação e exibição efetiva, atualizar `mostrado = 1`.
- [x] Evitar tentativas infinitas e notificações repetidas a cada minuto.

## 4. AJ-03 — Falhas de leitura

- [x] Simular `PermissionError` na leitura do arquivo.
- [x] Simular arquivo com codificação inválida (`UnicodeDecodeError`).
- [x] Simular falha de I/O (`OSError`) e arquivo removido entre a verificação e a leitura.
- [x] Em todos os casos, a conversa continua funcionando, o erro técnico é registrado sem texto pessoal e o relatório não é marcado como exibido se não foi apresentado.
- [x] O agendador não encerra silenciosamente diante de erro recuperável; existe registro técnico para diagnóstico.

## 5. Regressão — preservar comportamentos anteriores

- [x] Ctrl+C durante a geração registra a pergunta incompleta em `nora pendencias` na mesma sessão, sem duplicar. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] A retomada (`termina a resposta que ficou pela metade`) produz uma nova resposta completa e não é confundida com um fato permanente incompleto. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] A retomada mantém `conversa.ocupada = True` até terminar; o agendador aguarda. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] No modo jogo, falha das nuvens não chama o cérebro local; sair do modo jogo exige confirmação. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] Ao sair do modo jogo, a Nora apenas oferece retomar perguntas sem resposta, sem executar sozinha. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] Comandos de troca de voz e perguntas sobre vozes não se confundem. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] Apagar/esquecer impede que fatos e pendências excluídos reapareçam; exclusão definitiva exige confirmação. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] Relatório `.md` não contém texto das perguntas, áudio, chaves, tokens nem dados pessoais do usuário. **Regressão automatizada; não substitui o teste manual correspondente.**
- [x] As ações `aprovar`, `recusar` e `adiar` exigem a decisão do usuário; aprovação só gera tarefa, sem alterar automaticamente o código. **Regressão automatizada; não substitui o teste manual correspondente.**

## 6. Automação de qualidade — Codex / GitHub

Executar na raiz do repositório:

```bash
python -m pip install -e ".[dev,memoria]"
ruff format --check .
ruff check .
pytest
```

- [x] Os três comandos de qualidade passam localmente no ambiente do Codex.
- [x] Criar testes determinísticos para AJ-01/AJ-02/AJ-03 sem depender de relógio real ou notificação real do Windows.
- [ ] **EXTERNO:** CI do GitHub Actions aprovada em **Windows e Ubuntu**, Python **3.11 e 3.13**.
- [ ] **EXTERNO:** Criar PR contra `Pull_code`, com arquivos alterados, descrição dos testes e riscos residuais.
- [x] Não fazer merge, não criar tag `v0.3.0` e não publicar release automaticamente.

## 7. Homologação manual — Windows com GPU AMD

Esses testes **não são substituídos por CI**. Fazer após aprovação técnica do PR ou em um ambiente de testes do computador real.

- [ ] **WINDOWS:** `nora --verificar` informa corretamente o estado de Ollama, whisper.cpp, voz e credenciais disponíveis (sem mostrar segredos).
- [ ] **WINDOWS:** `nora ouvir`: ativação por voz, transcrição, resposta falada e digitação com microfone ativo.
- [ ] **WINDOWS:** Testar troca para Piper/ElevenLabs e pergunta sobre motores sem troca indevida.
- [ ] **WINDOWS:** Ativar modo jogo, confirmar liberação da VRAM no Gerenciador de Tarefas e verificar que falha de nuvem não reativa Ollama.
- [ ] **WINDOWS:** `sai do modo jogo` solicita confirmação; após `sim`, verificar oferta de retomada de pendências.
- [ ] **WINDOWS:** Simular interrupção real com Ctrl+C e verificar `nora pendencias`; retomar uma pergunta e conferir que o registro é resolvido.
- [ ] **WINDOWS:** Ajustar temporariamente `hora_relatorio` para alguns minutos adiante no **ambiente de teste** e testar modo `terminal` com Nora aberta e ociosa.
- [ ] **WINDOWS:** Repetir modo `abrir` e confirmar que o arquivo se abre no aplicativo padrão do Windows.
- [ ] **WINDOWS:** Testar apresentação após Nora ocupada, após modo jogo e após iniciar o computador/aplicativo depois da hora agendada.
- [ ] **WINDOWS:** Confirmar notificação do Windows e ação de clique que abre o relatório; testes automatizados atuais simulam o sistema operacional.
- [ ] **WINDOWS:** Confirmar que relatórios armazenados em `data/auto_melhoria/relatorios/` não expõem o conteúdo de perguntas pessoais.
- [ ] **WINDOWS:** Calibrar tempos de latência e busca com GPU AMD, STT e TTS reais, sem enviar dados pessoais a serviços externos.

## 8. Aceite final

- [x] AJ-01, AJ-02 e AJ-03 corrigidos e cobertos por testes de regressão.
- [x] Correções anteriores A1–A6 preservadas; nenhum componente reimplementado desnecessariamente.
- [x] Relatório automaticamente entregue quando Nora estiver livre, no modo escolhido, sem reinício obrigatório.
- [x] Falha de arquivo não provoca perda silenciosa nem bloqueia conversas.
- [ ] **EXTERNO:** CI verde e PR revisado; **homologação manual realizada** para os itens que dependem de Windows, áudio e GPU AMD.
- [x] Merge e release somente com aprovação explícita.

**Nota de escopo:** P3, P4 e HUD não entram neste conjunto de correções. A implementação de desenvolvimento por Codex deve continuar supervisionada.

## Evidências e limitações desta execução

- AJ-01: testes determinísticos do relógio, da espera de entrada e dos loops de texto,
  voz digitada e escuta sem fala comprovam entrega na sessão atual. O loop principal
  apresenta o conteúdo; o agendador fecha/notifica. Modo jogo e resposta em curso bloqueiam.
- AJ-02: o arquivo temporário removido permanece pendente. O aviso orienta restauração de
  backup e reinício; o teste restaura o arquivo e comprova a apresentação e `mostrado = 1`.
  Não foi implementada regeneração automática: não há cópia histórica integral garantida.
- AJ-03: PermissionError, UnicodeDecodeError, OSError e remoção entre verificação/leitura
  são simulados. A conversa segue respondendo, e o diagnóstico persiste sem a mensagem
  potencialmente pessoal da exceção. O agendador registra a classe técnica e segue ativo.
- Tentativas de apresentação com falha limitadas a uma por relatório por sessão.
- `nora --verificar`: executado; não comprova inferência/voz. Ollama, Whisper e Kokoro
  ausentes; SDKs/chaves opcionais de nuvem e pasta pessoal de notas não configurados.
- Teste de Kokoro real ignorado por ausência de `ELLA_KOKORO_PASTA`/modelo local.
- Windows/Ubuntu com Python 3.11 e 3.13: matriz existente preservada, execução remota
  desta branch ainda não confirmada. Ambiente local: Linux, Python 3.12.
- API GitHub (`api.github.com`) respondeu `Forbidden`: `gh pr create` também falhou com `Forbidden` no GraphQL; PR não criado nesta execução.
  A branch foi enviada ao GitHub com sucesso.
  Domínio adicional salvo no rascunho de rede para revisão, sem publicação automática.
- Merge, tags e releases não executados. O aceite final permanece pendente da CI remota,
  revisão do PR e homologação Windows/AMD.
