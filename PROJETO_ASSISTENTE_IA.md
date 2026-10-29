# Assistente de IA Pessoal por Voz: Documento do Projeto

> Documento de partida para desenvolver o projeto no Claude Code.
> Origem: conversa de planejamento em 29/10/2026.
> Autor: Gabriel (Carlos Gabriel Moura Santiago)

---

## 1. Visão

Criar uma **IA de conversação por voz em tempo real**, no estilo do "Jarvis" dos filmes do Homem de Ferro, mas com **nome, voz e identidade próprios e exclusivos**.

- **Foco:** a IA conversando em tempo real. A mesa touch com projetor vista no vídeo de referência **não é prioridade**.
- **Desenvolvimento:** por etapas, cada uma gerando uma versão funcional.
- **Objetivo futuro:** publicar como **open source no GitHub**.

### Referência analisada (vídeo "Bom dia J.A.R.V.I.S")
- **Cenário:** rotina matinal às 06:30. A pessoa senta na mesa e a IA fala primeiro, em português, com data, recado motivacional e plano do dia.
- **Monitor ultrawide:** HUD com um orbe central animado ("MACHINE"), relógio e feed de câmera.
- **Mesa:** projeção touch com cartões exibindo o conteúdo falado.
- **O que gera a imersão:** voz natural, resposta rápida, interface reagindo à fala e **iniciativa própria** (a IA fala sem ser chamada).

---

## 2. Arquitetura definida

### 2.1 Pipeline de voz em tempo real
1. **Wake word** com o nome personalizado: openWakeWord (grátis, treinável) ou Porcupine. Roda localmente, na CPU.
2. **VAD** (detecção de fala): Silero VAD.
3. **STT** (transcrição em streaming): **whisper.cpp com Vulkan**. O faster-whisper exige CUDA/NVIDIA e não serve para a GPU AMD.
4. **Cérebro (LLM)**: ver 2.2.
5. **TTS** (voz em streaming, frase por frase): Piper (local, CPU). Opções na nuvem: ElevenLabs ou Cartesia.
6. **Barge-in**: interromper a IA falando por cima. Exige **cancelamento de eco** e um bom microfone.
7. **Meta de latência:** < 1 s entre parar de falar e ouvir a resposta (MVP: < 2 s). Só se alcança com tudo em streaming.

### 2.2 Cérebro híbrido (decisão do Gabriel)
- **Conversa do dia a dia → modelo LOCAL** via Ollama ou LM Studio (backend ROCm ou Vulkan). Sugestão: modelo de 12–14B quantizado (Qwen ou Gemma), usando cerca de 9–10 GB de VRAM.
- **Raciocínio pesado → modelos externos via API** (Claude e outros). O modelo local decide quando escalar a tarefa.
  - Enquanto espera, a IA local fala algo como "deixa eu analisar isso", para não ficar em silêncio.
  - A resposta volta e é dita com a mesma voz e persona.
- **Modo jogo:** quando um jogo pesado abre, o modelo local sai da VRAM e a conversa vai para a API.
- **Descarregamento automático:** usar `keep_alive` do Ollama para liberar a VRAM depois de um tempo sem uso.

### 2.3 Base de dados local que evolui (decisão do Gabriel)
Alimentada pelas perguntas e respostas e desenvolvida com o tempo. Usa **SQLite + sqlite-vec** (busca vetorial), num arquivo local, no NVMe.

**Camadas:**
| Camada | Conteúdo | Uso |
|---|---|---|
| **Histórico bruto** | Todas as perguntas e respostas | Consulta e dataset futuro |
| **Memória curada** | Fatos e preferências extraídos e resumidos automaticamente ("acorda 06:30", "prefere respostas curtas") | Injetada no contexto (RAG) |
| **Conhecimento** | Boas respostas vindas dos modelos grandes | Modelo local responde sozinho na próxima vez, sem gastar API |

> **Importante:** o modelo local não "aprende" sozinho só por ter um banco ao lado. A evolução vem da recuperação de memória (RAG). **Futuro (fase 4 ou 5):** fine-tuning LoRA do modelo local com o histórico acumulado. Por isso o histórico bruto é guardado desde o primeiro dia.

### 2.4 Extensibilidade
- **Conectores, skills, agentes, subagentes e automações** entram conforme a ideia se desenvolve.
- **Decisão de base, já agora:** toda ferramenta segue o **padrão MCP** (Model Context Protocol). Cada conector novo vira um plugin, sem refazer o núcleo.

### 2.5 Agentes dentro da IA (runtime)
- **Orquestrador (a persona):** conversa com o usuário e delega aos especialistas, chamados como ferramentas.
- **Especialistas:** agenda e rotina, pesquisa, controle do PC e da casa, memória (resume e guarda o que importa).

### 2.6 HUD (interface visual)
- Página web em tela cheia (Electron ou Tauri) no monitor ultrawide.
- **Orbe** em Three.js/WebGL pulsando conforme o volume da voz (Web Audio API).
- **Cartões** surgindo com o conteúdo das respostas, relógio e status.

### 2.7 Modo distribuído (futuro)
- **Máquina pequena sempre ligada** (mini PC, notebook velho ou Raspberry Pi 5), o "corpo": wake word, agendador, banco de memória, automações. Consumo de cerca de 10–15 W.
- **PC principal**, o "cérebro" local: quando ligado, recebe a conversa.
- **API como reserva:** quando o PC está desligado ou ocupado.
- **Regra:** a arquitetura já nasce preparada para isso, com componentes separados que se comunicam pela rede local.

---

## 3. Hardware do PC principal

| Componente | Modelo |
|---|---|
| GPU | Gigabyte **RX 9060 XT 16 GB** (AMD, RDNA 4) |
| CPU | Ryzen 7 **9800X3D** |
| RAM | 32 GB DDR5 6000 MHz CL36 Corsair (2 pentes) |
| Fonte | MSI 750 W Gold Plus |
| Placa-mãe | B850 Gaming X WiFi6E |
| Armazenamento | SSD NVMe 1 TB + SSD SATA 240 GB |

**Implicações:**
- **GPU AMD:** evitar ferramentas só-CUDA. Usar **Vulkan e ROCm**. O suporte à RDNA 4 depende da versão do driver e do programa, então **testar primeiro** (Etapa 1).
- **Divisão da VRAM (16 GB):** LLM 12–14B (~9–10 GB) + Whisper (~1–2 GB) + folga para o sistema e o HUD. Modelos de 20B ou mais cabem, mas ficam apertados e lentos.
- **Armazenamento:** modelos e banco no **NVMe**. O SATA fica para **backup do banco**.

**Upgrades futuros (só se sentir falta depois de usar):**
1. **RAM:** **trocar** por 2×32 GB (64 GB) ou 2×48 GB (96 GB) DDR5 6000. **Não usar 4 pentes:** no AM5 isso costuma derrubar a velocidade (para 5200–5600) e causar instabilidade.
2. **Segunda GPU só para IA:** ex.: RTX 3060 12 GB usada. Libera a RX 9060 XT para jogos e resolve a compatibilidade CUDA. Antes de comprar, conferir:
   - consumo da placa (a fonte de 750 W deve aguentar);
   - o segundo slot PCIe (geralmente x4, o que não importa para IA);
   - espaço e ventilação no gabinete.
3. **NVMe extra** para os modelos (organização e espaço).

---

## 4. Custos e API

- **Claude Pro não inclui API.** São produtos separados. O Pro serve para **desenvolver** o projeto no Claude Code. A API (Console, paga por uso) é para a IA **rodando**. Max e Team trazem créditos mensais de API, o Pro não.
- **Custo estimado da API:** baixo para uso pessoal. Haiku na conversa e Sonnet/Opus só no pesado devem dar poucos dólares por mês. Definir um **limite de gasto** no Console.
- **Não usar** `claude -p` com o login do Pro como "cérebro": é lento (vários segundos) e o plano não foi feito para isso.
- **Energia:** PC gamer ligado 24h fica em algo como R$ 50–80/mês, contra R$ 7–10/mês de um mini PC (estimativa).

---

## 5. Roadmap por etapas (cada etapa = uma versão)

| Versão | Etapa | Entregas | Critério de pronto |
|---|---|---|---|
| **v0.0.0** | Fundação | Repositório, licença, README, estrutura, `.gitignore`, `.env.example`, config de **nome, persona, voz e modelos** | Projeto roda o "hello world" e a config carrega |
| **v0.1.0** | Conversa por voz | Wake word, VAD, whisper.cpp (Vulkan), Ollama, Piper | Falar o nome, perguntar e ouvir a resposta em < 2 s |
| **v0.2.0** | Memória | SQLite + sqlite-vec: histórico, memória curada, conhecimento | Lembra de fatos entre sessões |
| **v0.3.0** | Roteador de modelos | Escalonamento para Claude e outros, frase de espera, modo jogo, fallback | Pergunta difícil vai para a API e volta com a mesma voz |
| **v0.4.0** | HUD | Orbe reativo, cartões, relógio, tela cheia | Interface reage à voz em tempo real |
| **v0.5.0** | Ferramentas MCP | Agenda, clima, controle do PC, arquivos | Executa ações por voz |
| **v0.6.0** | Rotinas e iniciativa | Briefing das 06:30, lembretes, automações, **câmera** (ver Banco de ideias) | IA fala primeiro no horário e por presença |
| **v0.7.0** | Agentes e subagentes | Especialistas chamados pelo orquestrador | Tarefas complexas delegadas |
| **v0.8.0** | Modo distribuído | Separação "corpo 24h" × "cérebro" | Funciona com o PC desligado (via API) |
| **v1.0.0** | Lançamento | Instalador, docs completas, backends AMD/NVIDIA/CPU | Terceiros instalam e usam |

### Versionamento semântico (`vMAIOR.MENOR.CORREÇÃO`)

| Parte | Quando muda | Exemplo |
|---|---|---|
| **MAIOR** | Lançamento estável ou mudança que quebra a compatibilidade | `v0.8.0` → `v1.0.0` |
| **MENOR** | Cada nova etapa do roadmap | `v0.1.0` → `v0.2.0` |
| **CORREÇÃO** | Ajustes, correções e melhorias pequenas dentro de uma etapa | `v0.1.0` → `v0.1.1` → `v0.1.2` |

- Cada versão publicada ganha uma **tag no Git** com o mesmo nome (ex.: `v0.1.0`) e uma entrada no `CHANGELOG.md`.
- Antes da `v1.0.0`, o projeto ainda está em desenvolvimento e qualquer parte pode mudar.

**Etapas futuras:** fine-tuning LoRA, casa inteligente (Home Assistant), mesa com projetor e touch.

---

## 6. Diretrizes de open source

- **Nada pessoal no repositório:**
  - chaves de API só em `.env` (ignorado pelo Git), com um `.env.example` de modelo;
  - **o banco de memória, o histórico e os dados de rosto nunca vão para o GitHub**;
  - pasta `data/` no `.gitignore` desde a v0.0.
- **Nome e marca:** não usar "Jarvis", nem logos ou referências visuais da Marvel, no nome, no logo ou na divulgação. É marca registrada. "Inspirado em assistentes da ficção" pode.
- **Nome personalizável:** o nome do assistente vem do config. Cada usuário dá o seu, e o do Gabriel continua exclusivo.
- **Licença do código:** MIT ou Apache-2.0.
- **Licenças de modelos e vozes:** verificar uma a uma. Algumas proíbem uso comercial ou redistribuição (ex.: **XTTS é não comercial**; algumas vozes do Piper têm restrições). Preferir componentes redistribuíveis, ou baixar os modelos à parte via script.
- **Backends trocáveis:** Vulkan, ROCm, CUDA e CPU, para rodar em outras máquinas.
- **Qualidade do repositório:** commits organizados (Conventional Commits), uma tag por etapa, `CHANGELOG.md`, CI básico. Serve também como portfólio.
- **Voz original:** criar com voice design ou escolher uma pronta. **Não imitar a voz de ator real.**

---

## 7. Sugestões de nome (com sigla)

- **K.A.I.R.O.S.:** *kairós* = "o momento certo" (grego). Combina com briefing e rotina.
- **Ó.R.I.O.N.:** Operador de Rotina, Inteligência e Organização Neural.
- **V.E.G.A.:** Vigilância, Execução e Gestão Autônoma.
- **A.U.R.A.:** Assistente Universal de Rotina e Automação.

> Ainda a decidir: o **nome do projeto open source** e o **nome do assistente pessoal** do Gabriel podem ser diferentes.

---

## 8. Banco de ideias

### 8.1 Identificação por câmera
Ao chegar no quarto, a IA identifica a pessoa e interage. Encaixe: **Etapa 6**.

- **Camada 1, presença:** detectar que alguém entrou, sem identificar quem. Leve: webcam + MediaPipe (CPU) ou um **sensor mmWave** (barato, sem câmera, detecta até alguém parado).
- **Camada 2, reconhecimento:** só quando há presença, comparar o rosto com o cadastro (ex.: InsightFace) e cumprimentar com contexto ("Boa noite, Gabriel. Você tem prova amanhã, quer revisar?").
- **Privacidade:**
  - dados de rosto **só locais**;
  - pessoa desconhecida → nada pessoal é dito;
  - comando de voz ou botão para desligar a câmera;
  - cadastro de visitas só com consentimento.

*(Adicionar novas ideias aqui.)*

---

## 9. Desenvolvimento com Claude Code: papéis sugeridos

| Papel | Responsabilidade |
|---|---|
| **Plan** | Arquitetura, contratos entre módulos, plano de cada etapa |
| **Subagente de voz** | Wake word, VAD, STT, TTS, barge-in, eco |
| **Subagente de cérebro** | Orquestração LLM, roteador, persona |
| **Subagente de memória** | Esquema do banco, RAG, curadoria automática |
| **Subagente de HUD** | Orbe, cartões, animações, Electron/Tauri |
| **Subagente de integrações** | Servidores MCP (agenda, clima, PC, casa) |
| **Revisor** | Mede a latência por etapa, testes, comparação com a referência |

---

## 10. Decisões pendentes (responder antes da v0.0.0)

1. **Sistema operacional:** Windows ou Linux? No Linux o ROCm costuma ser mais maduro.
2. **Nome:** o nome do projeto e o do assistente são o mesmo ou diferentes?
3. **Linguagem:** sugestão de **núcleo em Python + HUD em web (TypeScript)**.
4. **Uso 24h:** precisa funcionar com o PC desligado? Isso define quando entra a Etapa 8.
5. **Licença:** MIT ou Apache-2.0.

---

## 11. Primeiro prompt sugerido para o Claude Code

```
Leia PROJETO_ASSISTENTE_IA.md por completo. Vamos iniciar a Etapa 0 (v0.0.0).
Antes de escrever código, use o modo de planejamento para:
1. Confirmar comigo as decisões pendentes da seção 10.
2. Propor a estrutura de pastas (núcleo Python modular, HUD web separado,
   servidores MCP como plugins, pasta data/ fora do Git).
3. Criar um CLAUDE.md resumindo as regras do projeto (seções 2, 3 e 6).
Depois, implemente a v0.0.0 e, em seguida, um teste rápido de compatibilidade
da GPU AMD (Ollama com ROCm/Vulkan e whisper.cpp com Vulkan) para validar a Etapa 1.
```
