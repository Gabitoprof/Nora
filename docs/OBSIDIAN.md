# Usando o repositório no Obsidian

O repositório inteiro funciona como um **vault** do Obsidian: documentação, mapa mental e notas de cada etapa ficam nos mesmos arquivos `.md` que vão para o GitHub.

## Configuração (uma vez)

1. Clone o repositório no PC.
2. No Obsidian: **Open folder as vault** → escolha a pasta do repositório.
3. Instale o plugin da comunidade **Git** (de Vinzent03) para fazer commit, pull e push sem sair do Obsidian.
   - Sugestão: ativar *auto pull* ao abrir o vault, para receber o que for feito no Claude Code.

## O que abrir

| Arquivo | O que é | Onde aparece |
|---|---|---|
| `docs/MAPA_MENTAL.canvas` | Mapa mental visual e editável (Canvas) | Só no Obsidian |
| `docs/MAPA_MENTAL.md` | Mapa mental, roadmap e fluxo em Mermaid | Obsidian **e** GitHub |
| `PROJETO_ASSISTENTE_IA.md` | Documento completo do projeto | Obsidian e GitHub |

## Convenções

- **Links:** usar links Markdown padrão (`[texto](caminho.md)`) em vez de `[[wikilinks]]`, para funcionarem também no GitHub.
- **A cada etapa concluída:** atualizar o status no `MAPA_MENTAL.md` e no `MAPA_MENTAL.canvas` (⬜ → 🔄 → ✅).
- **Notas pessoais** (que não devem ir para o GitHub): colocar em `data/` ou numa pasta ignorada pelo Git.
