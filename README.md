# Ella

Assistente de IA pessoal que **conversa por voz em tempo real**, roda **principalmente no seu computador**, lembra do que vocês conversaram e evolui com o uso. Inspirado nos assistentes da ficção, com nome, voz e personalidade próprios e configuráveis.

> **Status:** construindo a `v0.1.0`. Já dá para conversar **por texto** com o modelo local; a voz vem a seguir. Veja o [roadmap](docs/MAPA_MENTAL.md#2-roadmap-por-etapas).

## Requisitos

- Python 3.11 ou mais novo
- [Ollama](https://ollama.com) para o modelo local (a partir da v0.1.0)
- Windows ou Linux. Desenvolvido numa GPU AMD (Vulkan); CUDA e CPU também estão nos planos.

## Começando

```bash
git clone https://github.com/gabitoprof/ella.git
cd ella
python -m venv .venv
```

Ative o ambiente (Windows: `.venv\Scripts\activate`; Linux/macOS: `source .venv/bin/activate`) e instale:

```bash
pip install -e ".[dev]"
```

```bash
ella
```

Deve aparecer a saudação com a versão. Para ver a config carregada e checar o ambiente (Ollama, chave da API):

```bash
ella --verificar
```

### Conversar (por texto, por enquanto)

Com o [Ollama](https://ollama.com) aberto e o modelo baixado (`ollama pull qwen3.5:9b`):

```bash
ella conversar
```

Digite `sair` para encerrar e `/limpar` para começar do zero. Com `--medir`, mostra o tempo de cada resposta. As conversas ficam em `data/historico/`, só na sua máquina.

## Personalizando

- **`config/ella.toml`**: config padrão (nome, persona, voz, modelos). Não coloque nada pessoal aqui.
- **`config/local.toml`**: crie este arquivo só com o que quiser mudar. Ele é ignorado pelo Git. Exemplo:

  ```toml
  [usuario]
  nome = "Seu nome"

  [persona]
  humor = 0.7
  ```

- **`.env`**: copie de `.env.example` para guardar chaves de API. Também é ignorado pelo Git.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `src/ella/` | Núcleo em Python |
| `config/` | Config padrão |
| `hud/` | Interface visual (web, a partir da v0.4.0) |
| `mcp_servers/` | Ferramentas no padrão MCP (a partir da v0.5.0) |
| `scripts/` | Utilitários, como o teste de GPU |
| `docs/` | Documentação, mapa mental e referências |
| `data/` | Memória e dados pessoais. **Criada na sua máquina, nunca vai para o Git.** |

## Documentação

- [Objetivo do projeto](docs/OBJETIVO.md)
- [Mapa mental e roadmap](docs/MAPA_MENTAL.md)
- [Documento completo do projeto](PROJETO_ASSISTENTE_IA.md)
- [Teste de GPU](docs/TESTE_GPU.md)
- [Usando no Obsidian](docs/OBSIDIAN.md)

## Licença

[MIT](LICENSE). Modelos de IA e vozes usados pelo projeto têm licenças próprias e são baixados à parte.
