# Changelog

Todas as mudanças relevantes do projeto ficam aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o [Versionamento Semântico](https://semver.org/lang/pt-BR/) (`vMAIOR.MENOR.CORREÇÃO`).

## [Não lançado]

### Adicionado

- `ella conversar`: conversa digitada com o modelo local, com a resposta aparecendo enquanto é gerada (parte 1 da v0.1.0). `--medir` mostra o tempo até a primeira palavra e a velocidade.
- Persona: prompt de sistema montado da config (humor, formalidade, respostas curtas, data e hora, nome do usuário), com regras para fala em voz alta (sem markdown nem emojis).
- Histórico bruto: cada pergunta e resposta é gravada em `data/historico/AAAA-MM-DD.jsonl`, fora do Git.

## [0.0.1] - 2026-10-30

### Adicionado

- Opção `pensar` em `[modelos.local]` para ligar ou desligar o modo "pensando" do modelo local (desligado por padrão).
- Resultados do primeiro teste de GPU em `docs/TESTE_GPU.md`.

### Alterado

- `scripts/teste_gpu_windows.ps1` mede pela API do Ollama: tempo total, carga e velocidade, com e sem modo pensando, sem os caracteres de animação do terminal no relatório.

## [0.0.0] - 2026-10-30

### Adicionado

- Estrutura do repositório: núcleo Python em `src/ella/`, pastas `hud/`, `mcp_servers/`, `scripts/`, `docs/`.
- Config em TOML (`config/ella.toml`) com nome, persona (humor e formalidade), voz e modelos; sobreposição pessoal por `config/local.toml` e segredos por `.env`, ambos fora do Git.
- Comando `ella` (saudação) e `ella --verificar` (mostra a config e checa Ollama e chave da API).
- Script `scripts/teste_gpu_windows.ps1` para testar o Ollama na GPU AMD, preparando a v0.1.0.
- Testes (pytest), lint (ruff) e CI no GitHub Actions para Windows e Linux.
- Documentação: objetivo, mapa mental (Mermaid e Obsidian Canvas), estudo de referência, guia do Obsidian, `CLAUDE.md`.
- Licença MIT.
