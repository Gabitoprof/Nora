# CLAUDE.md

Regras do projeto Nora para o Claude Code. Detalhes em `PROJETO_ASSISTENTE_IA.md`.

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
- **`.env.example` acompanha o `.env`:** toda variável nova (chave, endereço, opção) entra no `.env.example` no mesmo commit, com um comentário do que é e onde conseguir, mas **sem valor pessoal** (chaves sempre vazias). O `tests/test_env_exemplo.py` confere que toda variável lida pelo código está lá e que nenhuma chave foi preenchida.
- Toda dependência, programa, modelo ou voz nova entra em `docs/LICENCAS.md` no mesmo commit, com a licença conferida na fonte (o `tests/test_licencas.py` confere as dependências do `pyproject.toml`).
- Voz original: não imitar voz de ator ou personagem real.

## Fluxo de trabalho

- Versões `vMAIOR.MENOR.CORREÇÃO`: cada etapa sobe o MENOR, ajustes sobem a CORREÇÃO. Tag no Git e entrada no `CHANGELOG.md` por versão.
- Ao concluir uma etapa: atualizar o status em `docs/MAPA_MENTAL.md` **e** `docs/MAPA_MENTAL.canvas` (⬜ → 🔄 → ✅).
- Ao concluir uma etapa, **revisar e reescrever toda a documentação** para o estado novo, não só o CHANGELOG: `README.md` (status, o que ela faz, começando, comandos), roadmap da seção 5 do `PROJETO_ASSISTENTE_IA.md` (status e entregas reais), `docs/OBJETIVO.md`, o mapa mental (nós novos e status), os guias em `docs/` e o banco de ideias (o que virou realidade). Nada de texto que descreva uma versão antiga como atual.
- Links em Markdown padrão (não `[[wikilinks]]`), para funcionar no GitHub e no Obsidian.
- Antes de commitar: `ruff format .`, `ruff check .` e `pytest`.

## Homologação integrada

Seguir a estratégia e manter o [checklist cumulativo por módulo](docs/HOMOLOGACAO.md).
Criar e executar testes de unidade, integração e regressão para as alterações, preservando
os existentes. PR pronto exige CI verde em Windows e Linux no commit avaliado; isso não
significa homologação funcional completa. A homologação final integrada será no Windows
com GPU AMD ao fim da implementação planejada. Durante o desenvolvimento, testes manuais
pontuais só quando indispensáveis para hardware ou integração externa. Não pedir repetição
de testes manuais aprovados salvo impacto direto no componente; preservar suas evidências.
Integração à `main`, merge, tags e publicação continuam sujeitos à autorização explícita.
