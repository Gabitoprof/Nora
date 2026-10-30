# CLAUDE.md

Regras do projeto Ella para o Claude Code. Detalhes em `PROJETO_ASSISTENTE_IA.md`.

## O que é

Assistente de IA pessoal por voz em tempo real, local primeiro, com memória que evolui. Desenvolvido por etapas (`v0.0.0` → `v1.0.0`), cada uma uma versão funcional. Será open source (MIT).

## Idioma

- Documentação, mensagens ao usuário e nomes no código em **português (pt-BR)**.
- Commits em inglês, no padrão **Conventional Commits** (`feat:`, `fix:`, `docs:`...).

## Arquitetura (seção 2 do documento)

- Pipeline de voz, tudo em streaming: wake word (openWakeWord) → VAD (Silero) → STT (whisper.cpp com Vulkan) → LLM → TTS (Piper), com barge-in. Meta: menos de 1 s (MVP: menos de 2 s).
- Cérebro híbrido: conversa no modelo **local** (Ollama, `keep_alive` para liberar VRAM); tarefas pesadas na **API** (Claude), com frase de espera e a mesma voz. Modo jogo tira o modelo da VRAM.
- Memória: **SQLite + sqlite-vec** em `data/` (histórico bruto, memória curada, conhecimento). Histórico guardado desde o primeiro dia.
- Toda ferramenta segue o padrão **MCP** (`mcp_servers/`). Orquestrador = persona; especialistas são ferramentas.
- HUD web em `hud/` (TypeScript). Componentes separados, comunicando pela rede local (modo distribuído na v0.8.0).

## Hardware alvo (seção 3)

- GPU **AMD RX 9060 XT 16 GB** (RDNA 4) no **Windows**: **evitar ferramentas só-CUDA**; usar Vulkan (ROCm no Linux). Backends sempre trocáveis (Vulkan, ROCm, CUDA, CPU).
- VRAM: LLM ~9–10 GB + Whisper ~1–2 GB + folga.

## Open source (seção 6), obrigatório

- **Nada pessoal no repositório.** Chaves só em `.env`; config pessoal só em `config/local.toml`; `data/` nunca vai para o Git.
- **Não usar** "Jarvis", Marvel ou referências visuais deles em nome, logo ou divulgação.
- Nome do assistente sempre vindo da config.
- Conferir a licença de cada modelo e voz; preferir redistribuíveis ou baixar à parte via script. Código AGPL não entra no repositório.
- Voz original: não imitar voz de ator ou personagem real.

## Fluxo de trabalho

- Versões `vMAIOR.MENOR.CORREÇÃO`: cada etapa sobe o MENOR, ajustes sobem a CORREÇÃO. Tag no Git e entrada no `CHANGELOG.md` por versão.
- Ao concluir uma etapa: atualizar o status em `docs/MAPA_MENTAL.md` **e** `docs/MAPA_MENTAL.canvas` (⬜ → 🔄 → ✅).
- Links em Markdown padrão (não `[[wikilinks]]`), para funcionar no GitHub e no Obsidian.
- Antes de commitar: `ruff format .`, `ruff check .` e `pytest`.
