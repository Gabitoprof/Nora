# Andamento da Nora (para revisão)

Resumo do estado do projeto para uma revisão de código. Atualizado em 03/11/2026, branch `Pull_code`.

## O que é

Assistente de voz pessoal em pt-BR, local primeiro, MIT. Python 3.11–3.13. Regras do projeto em `CLAUDE.md`; visão completa em `PROJETO_ASSISTENTE_IA.md`.

## Versões

- `v0.2.0` lançada (tag): conversa por voz e memória.
- `v0.3.0` em desenvolvimento (`0.3.0.dev0`): roteador de modelos. Todos os itens planejados estão no código; falta revisar a documentação inteira e criar a tag.

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

## Pendente

- Fechar a v0.3.0: revisar toda a documentação, conforme a regra do `CLAUDE.md`; versão `0.3.0`; tag.
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
- `troca_voz.py`: falsos positivos na detecção do comando ("fale sobre o Kokoro" não pode trocar a voz).
- Concorrência: curadoria e notas rodam em linhas separadas, cada uma com sua conexão SQLite e trava (`check_same_thread=False`).
- A triagem por palavras-chave é frágil por natureza; a substituição está na seção Pendente.

## Como testar

```bash
pip install -e ".[dev,memoria]"
ruff check . && pytest
```

Na máquina real: `nora --verificar` (confere chaves, pacotes, Ollama, notas e vozes), `nora conversar --medir` e `nora ouvir`.
