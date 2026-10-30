# Nora

Assistente de IA pessoal que **conversa por voz em tempo real**, roda **principalmente no seu computador**, lembra do que vocês conversaram e evolui com o uso. Inspirado nos assistentes da ficção, com nome, voz e personalidade próprios e configuráveis.

> **Status:** `v0.1.0`, conversa por voz. A Nora acorda com o nome, ouve, pensa no modelo local e responde falando. Próxima etapa: memória (`v0.2.0`). Veja o [roadmap](docs/MAPA_MENTAL.md#2-roadmap-por-etapas).

## Requisitos

- Python 3.11 a 3.13 (**recomendado: 3.13**). O núcleo roda em versões mais novas, mas a voz (Piper/onnxruntime) ainda não tem pacotes para o Python 3.15.
- [Ollama](https://ollama.com) para o modelo local (a partir da v0.1.0)
- Windows ou Linux. Desenvolvido numa GPU AMD (Vulkan); CUDA e CPU também estão nos planos.

## Começando

```bash
git clone https://github.com/gabitoprof/nora.git
cd nora
python -m venv .venv
```

Ative o ambiente (Windows: `.venv\Scripts\activate`; Linux/macOS: `source .venv/bin/activate`) e instale:

```bash
pip install -e ".[dev]"
```

```bash
nora
```

Deve aparecer a saudação com a versão. Para ver a config carregada e checar o ambiente (Ollama, chave da API):

```bash
nora --verificar
```

### Conversar (por texto, por enquanto)

Com o [Ollama](https://ollama.com) aberto e o modelo baixado (`ollama pull qwen3.5:9b`):

```bash
nora conversar
```

Digite `sair` para encerrar e `/limpar` para começar do zero. Com `--medir`, mostra o tempo de cada resposta. As conversas ficam em `data/historico/`, só na sua máquina.

### Conversar por voz

Precisa do ouvido (whisper.cpp) e de uma voz (Kokoro local por padrão, Piper ou ElevenLabs) instalados e rodando. Passo a passo em [docs/VOZ.md](docs/VOZ.md). Depois:

```bash
nora falar --medir
```

Ou mãos livres, começando a frase com "Nora":

```bash
nora ouvir --medir
```

### Memória

A Nora lembra de você entre conversas (fatos, preferências, datas), tudo em `data/memoria.db`, só na sua máquina. Para ligar: `ollama pull bge-m3` e `pip install -e ".[memoria]"`. Ver e editar: `nora memoria listar`. Detalhes em [docs/MEMORIA.md](docs/MEMORIA.md).

## Personalizando

- **`config/nora.toml`**: config padrão (nome, persona, voz, modelos). Não coloque nada pessoal aqui.
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
| `src/nora/` | Núcleo em Python |
| `config/` | Config padrão |
| `hud/` | Interface visual (web, a partir da v0.4.0) |
| `mcp_servers/` | Ferramentas no padrão MCP (a partir da v0.5.0) |
| `scripts/` | Utilitários: teste de GPU, instalar e iniciar a voz |
| `docs/` | Documentação, mapa mental e referências |
| `data/` | Memória e dados pessoais. **Criada na sua máquina, nunca vai para o Git.** |

## Documentação

- [Objetivo do projeto](docs/OBJETIVO.md)
- [Mapa mental e roadmap](docs/MAPA_MENTAL.md)
- [Documento completo do projeto](PROJETO_ASSISTENTE_IA.md)
- [Teste de GPU](docs/TESTE_GPU.md)
- [Conversa por voz](docs/VOZ.md)
- [Memória](docs/MEMORIA.md)
- [Usando no Obsidian](docs/OBSIDIAN.md)

## Licença

[MIT](LICENSE). Modelos de IA e vozes usados pelo projeto têm licenças próprias e são baixados à parte.
