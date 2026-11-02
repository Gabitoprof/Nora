# Nora

Assistente de IA pessoal que **conversa por voz em tempo real**, roda **principalmente no seu computador**, lembra do que vocês conversaram e evolui com o uso. Inspirado nos assistentes da ficção, com nome, voz e personalidade próprios e configuráveis.

> **Status:** `v0.2.0` lançada (**memória**): a Nora acorda com o nome, ouve, pensa no modelo local, responde falando e lembra de você entre conversas. Em desenvolvimento: `v0.3.0` (roteador de modelos), que já traz **emoção automática na voz**. Veja o [roadmap](docs/MAPA_MENTAL.md#2-roadmap-por-etapas).

## O que ela já faz

- **Conversa por voz, mãos livres:** comece a frase com "Nora" e ela responde falando, frase por frase, enquanto ainda pensa. Também dá para digitar e ouvir a resposta.
- **Pensa no seu PC:** modelo local pelo [Ollama](https://ollama.com) (Qwen 3.5 9B numa GPU de 16 GB), sem pagar por uso.
- **Várias vozes:** Kokoro (local, grátis, padrão), Piper (local; dá para treinar a sua), ElevenLabs (nuvem, a mais natural) e ComfyUI (vozes que você cria). Uma voz de reserva entra sozinha se a principal falhar.
- **Emoção na voz:** ela escolhe sozinha o tom de cada frase (alegre, carinhosa, calma, risada, sussurro...) pelo contexto; no ElevenLabs v3, ri, suspira e sussurra de verdade.
- **Memória:** anota fatos sobre você por área (saúde, estudos, trabalho...), guarda cada conversa inteira, acha compromissos pelo dia ("o que tenho amanhã?") e aprende como você quer que ela fale (pronúncias, jeito de responder, o tom que funciona com você).
- **Respeita o resto do PC:** abaixa o som dos outros programas enquanto fala.
- **Privada:** memória, histórico e configurações pessoais ficam em `data/` e `config/local.toml`, só na sua máquina.

## Requisitos

- Python 3.11 a 3.13 (**recomendado: 3.13**). A voz (onnxruntime) ainda não tem pacotes para o Python 3.15.
- [Ollama](https://ollama.com) com o modelo de conversa e o de memória: `ollama pull qwen3.5:9b` e `ollama pull bge-m3`.
- Windows ou Linux. Desenvolvido numa GPU AMD (Vulkan); CUDA e CPU também funcionam.

## Começando

```bash
git clone https://github.com/gabitoprof/nora.git
cd nora
python -m venv .venv
```

Ative o ambiente (Windows: `.venv\Scripts\activate`; Linux/macOS: `source .venv/bin/activate`) e instale com voz e memória:

```bash
pip install -e ".[voz,memoria]"
```

```bash
nora --verificar
```

Mostra a config carregada e confere o Ollama, o ouvido, a voz e a memória.

### 1. Conversar por texto

```bash
nora conversar
```

`sair` encerra e `/limpar` começa do zero; `--medir` mostra o tempo de cada resposta.

### 2. Conversar por voz

Instale e abra o ouvido (whisper.cpp) e uma voz local, uma vez só (passo a passo para Windows em [docs/VOZ.md](docs/VOZ.md)):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\instalar_voz_windows.ps1
```

```powershell
.\scripts\iniciar_voz_windows.ps1
```

Depois, mãos livres (comece a frase com "Nora"; também dá para digitar):

```bash
nora ouvir
```

Ou digite e ouça a resposta falada: `nora conversar --voz`.

### 3. Memória

Já vem ligada. Ela anota sozinha o que vale lembrar e mostra `[memória] anotei: ...` na conversa.

| Comando | O que faz |
|---|---|
| `nora memoria listar` | O que ela lembra de você (20 por página) |
| `nora memoria agenda` | Compromissos e datas dos próximos 30 dias |
| `nora memoria marcar 21/11/2026 prova` | Põe algo na agenda à mão |
| `nora memoria pronuncias` | As pronúncias que ela aprendeu |
| `nora memoria preferencias` | Como você pediu que ela fale |
| `nora memoria esquecer 12` | Apaga um fato |

Tudo em [docs/MEMORIA.md](docs/MEMORIA.md).

## Personalizando

- **`config/nora.toml`**: config padrão (nome, persona, voz, emoção, memória, modelos). Não coloque nada pessoal aqui.
- **`config/local.toml`**: crie este arquivo só com o que quiser mudar. Ele é ignorado pelo Git. Exemplo:

  ```toml
  [usuario]
  nome = "Seu nome"

  [persona]
  humor = 0.6

  [voz]
  motor = "elevenlabs"   # kokoro, piper, elevenlabs ou comfyui
  reserva = "kokoro"

  [emocao]
  intensidade = 0.5      # 0 = sem emoção, 1 = bem expressiva
  ```

- **`.env`**: copie de `.env.example` para guardar chaves de API (ElevenLabs, Anthropic). Também é ignorado pelo Git.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `src/nora/` | Núcleo em Python (conversa, voz, memória, agenda, emoção) |
| `config/` | Config padrão |
| `recursos/` | Frases de treino de voz |
| `scripts/` | Instalar e iniciar a voz, teste de GPU, notebooks de treino do Piper (Kaggle e Colab) |
| `tests/` | Testes automáticos (`pytest`) |
| `docs/` | Documentação, mapa mental e referências |
| `hud/` | Interface visual (web, a partir da v0.4.0) |
| `mcp_servers/` | Ferramentas no padrão MCP (a partir da v0.5.0) |
| `data/` | Memória e dados pessoais. **Criada na sua máquina, nunca vai para o Git.** |

## Documentação

- [Objetivo do projeto](docs/OBJETIVO.md)
- [Mapa mental e roadmap](docs/MAPA_MENTAL.md)
- [Documento completo do projeto](PROJETO_ASSISTENTE_IA.md)
- [Voz: instalar, motores, emoção, pronúncia](docs/VOZ.md)
- [Memória: fatos, agenda, aprender pela conversa](docs/MEMORIA.md)
- [Treinar uma voz própria (Piper)](docs/TREINAR_VOZ.md)
- [Teste de GPU](docs/TESTE_GPU.md)
- [Usando no Obsidian](docs/OBSIDIAN.md)
- [Licenças de terceiros](docs/LICENCAS.md)
- [Histórico de versões](CHANGELOG.md)

## Licença

O código da Nora é [MIT](LICENSE). Programas, modelos de IA e vozes que ela usa têm licenças próprias e são baixados à parte: veja [docs/LICENCAS.md](docs/LICENCAS.md) antes de redistribuir qualquer coisa.
