# Andamento da Nora (para revisão)

Resumo do estado do projeto para uma revisão de código. Atualizado em 03/11/2026 (depois das correções A1 a A6), branch `Pull_code`.

## O que é

Assistente de voz pessoal em pt-BR, local primeiro, MIT. Python 3.11–3.13. Regras do projeto em `CLAUDE.md`; visão completa em `PROJETO_ASSISTENTE_IA.md`.

## Versões

- `v0.2.0` lançada (tag): conversa por voz e memória.
- `v0.3.0` em desenvolvimento (`0.3.0.dev0`): roteador de modelos. Itens planejados e correções da revisão (A1 a A6) no código e testados; falta a validação no PC real, a revisão completa da documentação e a tag.

## Caminho de uma pergunta

1. **Ouvir:** Silero VAD (`vad.py`) → whisper.cpp HTTP (`ouvido.py`) → palavra "Nora" (`ativacao.py`). Ou texto digitado. Laços: `conversa_voz.py`, `maos_livres.py`.
2. **Lembrar:** `conversa.py::_lembrar` junta preferências, fatos e trechos (`memoria.py`: SQLite + sqlite-vec, embeddings bge-m3 pelo Ollama), agenda (`agenda.py`) e notas do Obsidian (`notas.py`).
3. **Classificar:** `roteador.py`. Comandos (cérebro, modo jogo), triagem por palavras-chave, `{pensar}` do modelo local e segunda chance quando a pessoa reclama.
4. **Executar:** local Ollama (`cerebro.py`); nuvem ChatGPT (`cerebro_openai.py`, API Responses) → Claude (`cerebro_nuvem.py`) → local. Sem trocar de cérebro se a resposta já começou a sair.
5. **Falar:** marcas de emoção (`emocao.py`) → voz (`voz.py`: ElevenLabs, Kokoro, Piper, ComfyUI, com reserva). Troca de voz por comando em `troca_voz.py`.
6. **Registrar:** histórico JSONL (`historico.py`) e curadoria em segundo plano (`curadoria.py`), que anota, corrige e esquece fatos.

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

## Pendente

- **Validação no PC real** (Windows, AMD), que a CI não cobre:
  - [ ] `nora --verificar` com tudo ok (Ollama, whisper, voz, Claude, ChatGPT, notas).
  - [ ] `nora ouvir`: falar e digitar; "troque para a voz do Piper" e "volta pro ElevenLabs"; "o Piper é melhor que o Kokoro?" não troca.
  - [ ] "modo jogo" libera a VRAM (Gerenciador de Tarefas); sem internet, ela avisa e a VRAM continua livre.
  - [ ] "use o Claude para explicar fotossíntese" responde pelo Claude; o modo continua automático.
  - [ ] "esquece que eu ..." e depois `nora memoria apagar "..."` (prévia e `--confirmar`).
  - [ ] `nora notas ler` e uma pergunta sobre uma nota.
- Depois da validação: revisão completa da documentação (`CLAUDE.md`), versão `0.3.0` em `src/nora/__init__.py` e tag `v0.3.0`.
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
- Concorrência: curadoria e notas rodam em linhas separadas, cada uma com sua conexão SQLite e trava (`check_same_thread=False`).
- A triagem por palavras-chave é frágil por natureza; a substituição está na seção Pendente.

## Como testar

```bash
pip install -e ".[dev,memoria]"
ruff check . && pytest
```

Na máquina real: `nora --verificar` (confere chaves, pacotes, Ollama, notas e vozes), `nora conversar --medir` e `nora ouvir`.
