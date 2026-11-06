# Andamento da Nora (para revisão)

Resumo do estado do projeto para uma revisão de código. Atualizado em 05/11/2026 (preparação do release `v0.3.0`), branch `Pull_code`.

## O que é

Assistente de voz pessoal em pt-BR, local primeiro, todos os direitos reservados (até a v0.3.0, MIT). Python 3.11–3.13. Regras do projeto em `CLAUDE.md`; visão completa em `PROJETO_ASSISTENTE_IA.md`.

## Versões

- `v0.2.0` lançada (tag): conversa por voz e memória.
- `v0.3.0` lançada (05/11/2026): roteador de modelos. Release, qualidade e homologação em [`RELEASE_v0.3.0.md`](RELEASE_v0.3.0.md).
- Próximo: `v0.3.1` (voz sem troca de tom entre frases e ouvido mais preciso) e `v0.4.0` (HUD, no branch `feat/v0.4.0-hud`).

## Caminho de uma pergunta

1. **Ouvir:** Silero VAD (`vad.py`) → whisper.cpp HTTP (`ouvido.py`) → palavra "Nora" (`ativacao.py`). Ou texto digitado. Laços: `conversa_voz.py`, `maos_livres.py`.
2. **Lembrar:** `conversa.py::_lembrar` junta preferências, fatos e trechos (`memoria.py`: SQLite + sqlite-vec, embeddings bge-m3 pelo Ollama), agenda (`agenda.py`) e notas do Obsidian (`notas.py`).
3. **Classificar:** `roteador.py`. Comandos (cérebro, modo jogo), triagem por palavras-chave, `{pensar}` do modelo local e segunda chance quando a pessoa reclama.
4. **Executar:** local Ollama (`cerebro.py`); nuvem ChatGPT (`cerebro_openai.py`, API Responses) → Claude (`cerebro_nuvem.py`) → local. Sem trocar de cérebro se a resposta já começou a sair.
5. **Falar:** marcas de emoção (`emocao.py`) → voz (`voz.py`: ElevenLabs, Kokoro, Piper, ComfyUI, com reserva). Troca de voz por comando em `troca_voz.py`.
6. **Registrar:** histórico JSONL (`historico.py`) e curadoria em segundo plano (`curadoria.py`), que anota, corrige e esquece fatos. Respostas que não terminaram vão para `respostas_pendentes` (`memoria.py`).
7. **Observar e propor:** `observador.py` anota métricas e categorias (sem texto); `melhorias.py` fecha o dia, gera propostas e o relatório e guarda as decisões.

## Feito na v0.3.0 (commits desde a v0.2.0)

- Emoção automática na voz (`emocao.py`, `[emocao]`).
- Roteador local ↔ nuvem, modo jogo, frase de espera, reservas, avisos `[cérebro]`.
- Triagem e segunda chance (`[roteador] triagem`).
- Apagar e corrigir fatos pela conversa (campo `esquecer` na curadoria).
- ChatGPT como padrão das perguntas complexas, Claude de reserva (`[roteador] complexas`, `[modelos.openai]`).
- Troca de voz falando ("troque para a voz do Piper").
- Índice das notas do Obsidian (`[notas] pasta`, `nora notas ler|buscar|status`, `data/notas.db`).
- Correção: texto digitado no `nora ouvir` agora é lido com o microfone ativo (`vad.py::falas`).
- Teste que mantém o `.env.example` em dia (`tests/test_env_exemplo.py`).

## Correções da revisão de 03/11/2026 (relatório de próximas ações)

| ID | Correção | Teste |
|---|---|---|
| A1 | Modo jogo não chama o cérebro local quando a nuvem falha; avisa (`FRASE_JOGO_SEM_NUVEM`) | `test_modo_jogo_sem_nuvem_nao_reacende_o_cerebro_local` |
| A2 | Esquecer = deixar de usar (tabela `esquecidos`: filtra `buscar_trocas` e bloqueia o `importar`); `nora memoria apagar` = apagar de vez (memória + `data/historico`, com prévia e `--confirmar`) | `test_esquecido_nao_volta_...`, `test_apagar_de_vez_...`, `test_comando_apagar_...` |
| A3 | Comando com conteúdo responde o conteúdo (`achar_comando` devolve se é puro) | `test_comando_com_pergunta_responde_a_pergunta` |
| A4 | Local que cai depois de falar não recebe outra resposta emendada | `test_falha_do_local_no_meio_nao_emenda_outra_resposta` |
| A5 | `Roteador.situacao` (completa, interrompida, sem resposta) vai para o histórico; só as completas vão para a curadoria | `test_resposta_interrompida_fica_marcada_...`, `test_falha_da_nuvem_no_meio_fica_marcada` |
| A6 | Troca de voz exige verbo de troca e ignora perguntas/comparações | `test_perguntas_sobre_vozes_nao_trocam_a_voz` |

Os seis foram reproduzidos por teste antes da correção (A1: local chamado no modo jogo; A3: `comando_em` devolvia "nuvem" e a pergunta se perdia; A4: saída "Uma reResposta do Claude."; A2: trecho esquecido voltava com similaridade 0,79; A6: "qual voz é melhor..." virava pedido).

## Revisão consolidada de 04/11/2026 (plano de auto-melhoria supervisionada)

| Etapa | Entregue | Testes |
|---|---|---|
| P1 · A1 | Sair do modo jogo pede "sim" (regra em `confirmacao.py`, sem modelo); "como sair do modo jogo?" não muda nada; trocas de modo ficam como `situacao: "comando"` e não vão para a curadoria | `test_sair_do_modo_jogo_pede_confirmacao_...` |
| P1 · A5 | Tabela `respostas_pendentes`: uma linha "aberta" por resposta vira pendência se o programa cair; também stream interrompido, sem resposta, Ctrl+C; retomada identificada ("termina a resposta que ficou pela metade"), 3 tentativas; `nora pendencias`; esquecer/apagar tiram as pendências do assunto | `test_resposta_interrompida_vira_pendencia_...`, `test_pendencia_de_cancelamento_...`, `test_respostas_completas_e_comandos_...`, `test_comando_pendencias_...` |
| P1 · A4 | `CerebroIndisponivel.categoria` e `categoria_do_erro`; `Roteador.tentativas` (motor, resultado, tempo até o 1º pedaço); reserva só antes do conteúdo | `test_tentativas_ficam_anotadas_...` |
| P2 | `observador.py` (sem texto) e `melhorias.py`: diagnóstico por regras, propostas com evidência, relatório diário, um por dia, recuperação do dia perdido, agendador que espera a Nora desocupada, notificação do Windows, decisões (aprovar gera tarefa; publicar exige `--autorizo-publicar`), `nora melhorias` e pela voz com "sim" | `tests/test_auto_melhoria.py` (12 testes) |

### Auditoria de 04/11/2026 (`AUDITORIA_NORA_PULL_CODE_2026-11-03.md`)

Os cinco pontos foram conferidos no código e reproduzidos por teste antes da correção.

| Ponto | Correção | Teste |
|---|---|---|
| P0 Ctrl+C | `conversa.py::_responder` trata `KeyboardInterrupt` junto com `GeneratorExit`: pendência gravada na hora, uma vez só | `test_ctrl_c_no_meio_vira_pendencia_na_hora` |
| P1 retomada ocupada | `perguntar` marca `ocupada` também durante `_retomar` (`try/finally`) | `test_retomada_marca_a_nora_ocupada_e_o_relatorio_espera` |
| P1 privacidade | `_relatorio` não escreve a pergunta; `_limpar_perguntas_dos_relatorios` limpa os antigos | `test_relatorio_nao_mostra_perguntas_e_limpa_os_antigos` |
| P1 apresentação | `apresentar()` abre o .md ou mostra o texto inteiro; `marcar_mostrado` só depois; `falha_aviso` registrada; espera o modo jogo; `[auto_melhoria] apresentar` | `test_inicio_da_sessao_abre_...`, `test_se_nao_abrir_...`, `test_relatorio_do_meio_da_sessao_...`, `test_no_modo_jogo_o_relatorio_espera` |
| P2 modo jogo | Regra `sem_resposta` reescrita; `_oferecer_retomada_do_jogo` ao sair do modo jogo (só oferece) | `test_sem_resposta_no_modo_jogo_nao_sugere_usar_o_local` |

**Não implementado (decisão pendente):** P3, a pesquisa técnica na web (opcional, desligada por padrão), e P4, levar a tarefa aprovada ao Codex numa branch isolada (hoje é manual). A auto-melhoria é escopo novo: a tag `v0.3.0` não depende dela.

## Pendente

- **Validação no PC real** (Windows, AMD), que a CI não cobre:
  - [ ] `nora --verificar` com tudo ok (Ollama, whisper, voz, Claude, ChatGPT, notas).
  - [ ] `nora ouvir`: falar e digitar; "troque para a voz do Piper" e "volta pro ElevenLabs"; "o Piper é melhor que o Kokoro?" não troca.
  - [ ] "modo jogo" libera a VRAM (Gerenciador de Tarefas); sem internet, ela avisa e a VRAM continua livre.
  - [ ] "use o Claude para explicar fotossíntese" responde pelo Claude; o modo continua automático.
  - [ ] "esquece que eu ..." e depois `nora memoria apagar "..."` (prévia e `--confirmar`).
  - [ ] Por voz: "apaga de vez ..." → ela diz o que sairia → "sim, pode apagar"; e um "não" cancela.
  - [ ] `nora notas ler` e uma pergunta sobre uma nota.
  - [ ] "sai do modo jogo" pergunta antes; "como sair do modo jogo?" só explica.
  - [ ] Ctrl+C no meio de uma resposta → na próxima conversa aparece o aviso → "termina a resposta que ficou pela metade".
  - [ ] `nora melhorias fechar-dia` gera o relatório; a notificação do Windows aparece e abre o arquivo (o PowerShell da notificação ainda não foi testado num Windows real).
  - [ ] Com a Nora aberta depois das 20:00 (ou mudando `hora_relatorio`), o relatório abre sozinho no programa do .md; com a Nora fechada, abre na próxima sessão.
  - [ ] Ctrl+C enquanto ela ainda está pensando (antes de falar) → `nora pendencias` já mostra a pergunta, na mesma hora.
  - [ ] Modo jogo sem internet → uma pergunta → "sai do modo jogo" → "sim" → aparece a oferta de retomar.
  - [ ] Conferir com o bge-m3 real os limites `TROCA_ESQUECIDA` e os de latência em `[auto_melhoria]`.
- Feito em 05/11/2026: auditoria final, regressão do Enter no `nora falar` corrigida, issue #3 corrigida, documentação revisada e versão `0.3.0`. A lista atualizada de testes manuais, os riscos e os passos de homologação estão em [`RELEASE_v0.3.0.md`](RELEASE_v0.3.0.md); merge, tag e release esperam a autorização do mantenedor.
- Próximo (proposta, ainda não decidida): classificador com confiança no roteador, primeiro com bge-m3 e exemplos por rota; testar o `Mapika/decider-2b` (Apache-2.0, GGUF) como alternativa.
- Roadmap: v0.4.0 HUD, v0.5.0 ferramentas MCP (com permissões), v0.6.0 rotinas, v0.7.0 agentes, v0.8.0 modo distribuído.

## Regras que a revisão deve conferir

- Nada pessoal no Git: chaves só no `.env`, config pessoal em `config/local.toml`, `data/` ignorado.
- Toda dependência nova em `docs/LICENCAS.md` (testado por `tests/test_licencas.py`); nada AGPL; ferramentas GPL (Piper, espeak) só como processo separado.
- Toda variável de ambiente lida pelo código no `.env.example`, sem valor.
- Os testes passam sem `anthropic`, `openai`, `numpy` ou `sqlite_vec` instalados (dependências opcionais).
- Antes de commitar: `ruff format .`, `ruff check .`, `pytest`. Commits em inglês (Conventional Commits); textos e nomes em pt-BR.
- Alvo: Windows com GPU AMD (Vulkan); nada que só funcione com CUDA.

## Pontos para olhar com atenção

- `roteador.py::_nuvem`: ordem das nuvens, avisos e o caso de falha no meio da resposta.
- `notas.py`: atualização incremental (data de modificação e tamanho), índice vetorial opcional e a linha em segundo plano que lê as notas ao abrir a conversa (`conversa.py::nova_conversa`).
- `troca_voz.py`: a lista de palavras de pergunta (`_PERGUNTA`) pode barrar algum pedido legítimo pouco comum.
- `memoria.py`: os limites `TROCA_ESQUECIDA` (0,6) e `FATO_ESQUECIDO` (0,85) foram calibrados com vetores de teste; vale conferir com o bge-m3 real.
- Concorrência: curadoria, notas e o agendador da auto-melhoria rodam em linhas separadas, cada um com sua conexão SQLite e trava (`check_same_thread=False`); observador e melhorias dividem o mesmo arquivo `auto_melhoria.db`.
- `melhorias.py::notificar`: o script do PowerShell (notificação com `activationType="protocol"` e o caminho do .md) só foi testado com `subprocess.run` simulado.
- `melhorias.py::diagnosticar`: as regras e os limites são um ponto de partida; os textos das propostas são genéricos por categoria.
- A triagem por palavras-chave é frágil por natureza; a substituição está na seção Pendente.

## Como testar

```bash
pip install -e ".[dev,memoria]"
ruff check . && pytest
```

Na máquina real: `nora --verificar` (confere chaves, pacotes, Ollama, notas e vozes), `nora conversar --medir` e `nora ouvir`.
