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

## A Nora lendo as suas notas (v0.3.0)

A Nora pode ler as notas do **seu** vault do Obsidian (o pessoal, não precisa ser o do projeto) e usar o que você escreveu para responder: "o que eu anotei sobre a prova de cálculo?", "qual era a receita do bolo?". Ela **só lê**: nunca cria, altera nem apaga nota.

### Ligar (uma vez)

1. No `config/local.toml`, ponha o caminho do vault. Use barras `/` (ou aspas simples), porque a barra invertida do Windows tem outro sentido no TOML:

   ```toml
   [notas]
   pasta = "C:/Users/voce/Documents/Obsidian"
   # pastas que ela não deve ler (as ocultas, como .obsidian e .trash, já ficam de fora)
   ignorar = ["Diário", "Privado"]
   ```

2. Leia as notas pela primeira vez (pode levar alguns minutos num vault grande; usa o `bge-m3` do Ollama, o mesmo da memória):

   ```bash
   nora notas ler
   ```

3. Confira: `nora --verificar` mostra a linha `Notas (Obsidian)` com quantas notas estão no índice.

Depois disso, toda vez que você abre uma conversa, ela lê em segundo plano só as notas novas ou alteradas (e esquece as apagadas), sem atrasar o começo. Para desligar isso: `atualizar_ao_abrir = false`.

### Como ela usa

- Cada nota é dividida em trechos (por título e parágrafos). Antes de responder, ela busca os trechos mais parecidos com a pergunta (`trechos_por_pergunta`, padrão 3, acima de `similaridade_minima`, padrão 0.5) e lê junto, como faz com a memória.
- Quando usa uma nota, ela diz de qual veio ("na sua nota Cálculo, a prova é dia 21").
- Com `--medir`, cada resposta mostra quantas notas ela leu.
- Links `[[...]]`, propriedades (frontmatter), imagens e comentários `%%...%%` são limpos antes.

| Comando | O que faz |
|---|---|
| `nora notas ler` | Lê as notas novas ou alteradas agora |
| `nora notas buscar prova de cálculo` | Mostra os trechos que ela acharia para esse texto |
| `nora notas status` | Quantas notas e trechos estão no índice |

### Privacidade

- O índice fica em `data/notas.db`, só no seu PC (fora do Git). Dá para apagar o arquivo e rodar `nora notas ler` de novo quando quiser.
- Os trechos usados numa resposta vão junto com a pergunta para quem responde. Se a pergunta for para o ChatGPT ou o Claude, esses trechos vão para a nuvem também. Coloque em `ignorar` as pastas que nunca devem sair do PC, ou use "use o cérebro local".
