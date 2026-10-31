# Mapa mental do projeto

> Visão geral do projeto em diagramas. O GitHub desenha os blocos `mermaid` automaticamente.
> **Regra:** toda etapa concluída atualiza este arquivo, mudando o status no roadmap e incluindo nós novos no mapa.
> Versão visual editável no Obsidian: [`MAPA_MENTAL.canvas`](MAPA_MENTAL.canvas) (veja [`OBSIDIAN.md`](OBSIDIAN.md)).
> Fonte detalhada: [`PROJETO_ASSISTENTE_IA.md`](../PROJETO_ASSISTENTE_IA.md).
> Referências estudadas: [`referencias/`](referencias/video-01-assistente-local.md).

**Legenda do roadmap:** ✅ concluída · 🔄 em andamento · ⬜ pendente

**Versões:** `vMAIOR.MENOR.CORREÇÃO`. Cada etapa sobe o número do meio (`v0.1.0` → `v0.2.0`), e ajustes dentro de uma etapa sobem o último (`v0.1.0` → `v0.1.1`). Detalhes na seção 5 de [`PROJETO_ASSISTENTE_IA.md`](../PROJETO_ASSISTENTE_IA.md).

---

## 1. Visão geral

```mermaid
mindmap
  root((Nora))
    Voz em tempo real
      Wake word
        openWakeWord ou Porcupine
      VAD
        Silero VAD
      STT
        whisper.cpp com Vulkan
      TTS
        Piper local
        ElevenLabs ou Cartesia
      Barge-in
        Cancelamento de eco
      Latência
        Meta menos de 1 s
        MVP menos de 2 s
    Cérebro híbrido
      Local
        Ollama ou LM Studio
        Modelo 12 a 14B quantizado
        keep_alive libera VRAM
      API
        Claude e outros
        Frase de espera
      Modo jogo
        Conversa vai para a API
    Memória
      SQLite e sqlite-vec
      Histórico bruto
      Memória curada
      Conhecimento
      Futuro LoRA
    Extensões
      Padrão MCP
      Orquestrador persona
      Especialistas
        Agenda e rotina
        Pesquisa
        Controle do PC e casa
        Memória
    HUD
      Electron ou Tauri
      Orbe Three.js
      Cartões e relógio
    Modo distribuído
      Corpo 24h mini PC
      Cérebro PC principal
      API como reserva
    Hardware
      RX 9060 XT 16 GB
        Vulkan e ROCm
        Evitar só CUDA
      Ryzen 7 9800X3D
      32 GB DDR5
      NVMe para modelos e banco
    Open source
      Dados fora do Git
      env.example
      Sem marca Marvel
      Nome configurável
      MIT ou Apache-2.0
      Conferir licenças de modelos e vozes
    Banco de ideias
      Câmera
        Presença
        Reconhecimento facial local
        Privacidade
      Obsidian como segundo cérebro
        Índice das notas
        Grafo no HUD
      Trocar cérebro e voz por comando
      Palavras de partículas no HUD
      Criação de voz pelo ComfyUI
```

---

## 2. Roadmap por etapas

```mermaid
flowchart LR
  v00["v0.0.0 Fundação"]:::done --> v01["v0.1.0 Conversa por voz"]:::done
  v01 --> v02["v0.2.0 Memória"]:::doing
  v02 --> v03["v0.3.0 Roteador de modelos"]:::pend
  v03 --> v04["v0.4.0 HUD"]:::pend
  v04 --> v05["v0.5.0 Ferramentas MCP"]:::pend
  v05 --> v06["v0.6.0 Rotinas e iniciativa"]:::pend
  v06 --> v07["v0.7.0 Agentes"]:::pend
  v07 --> v08["v0.8.0 Modo distribuído"]:::pend
  v08 --> v10["v1.0.0 Lançamento"]:::pend

  classDef done fill:#2e7d32,stroke:#1b5e20,color:#fff
  classDef doing fill:#f9a825,stroke:#f57f17,color:#000
  classDef pend fill:#eceff1,stroke:#90a4ae,color:#37474f
```

| Versão | Etapa | Status | Critério de pronto |
|---|---|---|---|
| v0.0.0 | Fundação | ✅ | Projeto roda o "hello world" e a config carrega |
| v0.1.0 | Conversa por voz | ✅ | Falar o nome, perguntar e ouvir a resposta em menos de 2 s |
| v0.2.0 | Memória | 🔄 | Lembra de fatos entre sessões |
| v0.3.0 | Roteador de modelos | ⬜ | Pergunta difícil vai para a API e volta com a mesma voz |
| v0.4.0 | HUD | ⬜ | Interface reage à voz em tempo real |
| v0.5.0 | Ferramentas MCP | ⬜ | Executa ações por voz |
| v0.6.0 | Rotinas e iniciativa | ⬜ | IA fala primeiro no horário e por presença |
| v0.7.0 | Agentes e subagentes | ⬜ | Tarefas complexas delegadas |
| v0.8.0 | Modo distribuído | ⬜ | Funciona com o PC desligado, via API |
| v1.0.0 | Lançamento | ⬜ | Terceiros instalam e usam |

---

## 3. Fluxo de uma conversa

```mermaid
flowchart LR
  mic(["Microfone"]) --> ww["Wake word"] --> vad["VAD"] --> stt["STT whisper.cpp"]
  stt --> orq{"Orquestrador"}
  orq -->|conversa| local["LLM local Ollama"]
  orq -->|pesado| api["API Claude"]
  orq -->|ação| mcp["Ferramentas MCP"]
  mem[("Memória SQLite")] <--> orq
  local --> tts["TTS Piper"]
  api --> tts
  mcp --> orq
  tts --> spk(["Alto-falante"])
  tts --> hud["HUD orbe e cartões"]
```

---

## 4. Decisões tomadas (30/10/2026)

```mermaid
mindmap
  root((Decisões da v0.0.0))
    Sistema operacional
      Windows com Vulkan
      Linux como plano B
    Nome
      Nora para projeto e assistente
    Linguagem
      Núcleo Python
      HUD TypeScript
    Uso 24h
      Só na v0.8.0
    Licença
      MIT
```
