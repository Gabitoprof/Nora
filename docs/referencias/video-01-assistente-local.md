# Referência 01: assistente 100% local (vídeo de demonstração)

> Vídeo de ~25 min (em inglês) mostrando um assistente de voz inspirado em ficção rodando totalmente local: cérebro via Ollama e voz clonada localmente.
> Estudado em 30/10/2026 a partir do vídeo e da transcrição. Aqui ficam só as **ideias**; nome, marca e voz do vídeo não são usados no projeto (ver seção 6 do [`PROJETO_ASSISTENTE_IA.md`](../../PROJETO_ASSISTENTE_IA.md)).

---

## 1. O que o vídeo mostra

| Momento | O que acontece |
|---|---|
| 0:00 | Comando de voz "troque para o cérebro local" → o assistente confirma qual modelo assumiu, com humor. |
| 1:52 | **Interface:** página web em `localhost`, com um **grafo 3D de todos os arquivos e pastas** que o assistente pode acessar (o "segundo cérebro"), orbe com status e ferramentas conectadas. |
| 2:44 | **Troca de cérebro por voz:** Qwen 3.5 9B ↔ Gemma 4 12B ↔ modelo na nuvem. O modelo ativo aparece na tela. |
| 4:35 | **Troca de voz por voz:** voz na nuvem (ElevenLabs) ↔ voz local clonada (VoiceStudio) ↔ outras vozes clonadas. |
| 9:42 | **Teste 1, segundo cérebro:** "puxe minha voz de marca" → abre as notas ligadas a esse tema e destaca os nós no grafo. |
| 10:47 | **Teste 2, ferramentas:** "o que tenho amanhã na agenda?" → frase de espera ("deixa eu ver se tenho as ferramentas para isso"), consulta o Google Agenda e responde com comentário bem-humorado. A tela mostra **qual ferramenta foi usada**. |
| 13:19 | **Teste 3, tarefa longa:** analisa um site abrindo um navegador limpo, rolando a página e montando um relatório técnico. Avisa quanto tempo vai levar e narra o progresso. |
| 16:50 | Outras funções citadas: ligações, agendamentos, faturas. Acesso **controlado por permissão** ("se você não der acesso, ele não tem"). |
| 17:43 | Comparação **nuvem × local** e instalação (Ollama + VoiceStudio). |

---

## 2. Detalhes da interface (prints do vídeo)

- **Fundo:** grafo de nós coloridos por categoria (rotas, wiki, conceitos, skills, ferramentas, notas, arquivos), com controles de física (repulsão, peso das ligações).
- **Barra lateral esquerda:** categorias do segundo cérebro com contagem de itens; ao pedir um tema, mostra a lista de notas relacionadas.
- **Orbe** no canto: anel animado com status (`SPEAKING`), **selo do modelo ativo** (`QWEN3.5:9B`, `GEMMA4:12B`) e modos de visual (anel, núcleo, rosto).
- **Painel de modos** ligáveis: visão (câmera), segurar, foco, reflexo.
- **Rodapé:** texto da resposta com a **origem** ("via google calendar · gcal_events"), campo de texto e ícones das ferramentas.
- **Indicadores de atividade:** "buscando ferramentas", "ferramenta executada via …", e um checklist de etapas durante tarefas longas.

---

## 3. Comparação nuvem × local (do material do vídeo)

| Aspecto | Nuvem | Local |
|---|---|---|
| Ouvir | Reconhecimento de fala do navegador (áudio vai para o Google) | Whisper na máquina, rápido o suficiente |
| Pensar | Modelo grande da API, rápido e muito capaz | Modelo do Ollama; mais lento em notebook, rápido em máquina forte |
| Falar | ElevenLabs, pago por mês | Voz clonada local; um pouco mais lenta |
| Privacidade | Áudio e texto passam por terceiros | Nada sai da máquina |
| Qualidade | Melhor raciocínio e uso de ferramentas | Bom, não genial; depende do tamanho do modelo |
| Custo | Assinaturas e uso de API | Só energia |

---

## 4. O que aprendemos (e como entra no projeto)

| # | Ideia do vídeo | Como aplicar no nosso projeto | Etapa |
|---|---|---|---|
| 1 | **Trocar de cérebro por voz** ("use o cérebro local", "troque para o Gemma") | Comando de voz que força o roteador para um modelo específico; lista de modelos instalados no config. O roteador automático continua existindo. | v0.3.0 |
| 2 | **Trocar de voz por voz** | Várias vozes no config (local e nuvem), com troca por comando. | v0.3.0 |
| 3 | **Selo do modelo e da voz ativos** | O HUD mostra sempre qual cérebro e qual voz estão em uso. | v0.4.0 |
| 4 | **Grafo do segundo cérebro** | Usar o **vault do Obsidian** como segundo cérebro: o assistente indexa as notas `.md` (busca vetorial) e o HUD desenha o grafo, destacando as notas usadas na resposta. | v0.2.0 (índice) e v0.4.0 (grafo) |
| 5 | **Frase de espera** enquanto usa ferramentas | Já previsto para a API; estender para **qualquer** ferramenta lenta. | v0.3.0 e v0.5.0 |
| 6 | **Mostrar a origem** da resposta ("via Google Agenda") | Toda resposta que usou ferramenta ou nota traz a fonte no cartão do HUD. | v0.4.0 e v0.5.0 |
| 7 | **Narrar tarefas longas** (estimativa de tempo e checklist de etapas) | Tarefas de agentes publicam progresso no HUD e a voz dá atualizações curtas. | v0.7.0 |
| 8 | **Acesso por permissão** | Cada ferramenta MCP declara o que pode acessar; o usuário libera uma a uma. | v0.5.0 |
| 9 | **Personalidade com humor, ajustável** | Nível de humor e formalidade como parâmetros da persona no config. | v0.0.0 (config) |
| 10 | **Escolher o modelo pelo hardware** | Na nossa GPU de 16 GB, **Qwen 3.5 9B (~7,6 GB)** é um bom candidato padrão, com sobra para o Whisper; testar também modelos de 12–14B. | v0.1.0 |
| 11 | **Testar uso de ferramentas no modelo local** | Modelos pequenos erram mais ao chamar ferramentas. O teste de compatibilidade da v0.1.0 deve medir também a **qualidade das chamadas de ferramenta**, não só a velocidade. | v0.1.0 |
| 12 | **Agente que usa navegador** | Especialista que abre um navegador isolado para pesquisar ou analisar sites. | v0.7.0 |

---

## 5. Cuidados

- **Voz:** o vídeo clona a voz de um personagem de filme. **Não faremos isso:** a voz do assistente será original (voice design) ou uma voz pronta com licença livre.
- **Licença do VoiceStudio:** o print do repositório mostra **AGPL-3.0**. Se usarmos, deve rodar como **programa separado** (instalado à parte, chamado pela rede local), sem copiar o código para o nosso repositório. Verificar antes de adotar.
- **Desempenho:** o vídeo roda numa máquina Apple bem forte. Na nossa (AMD RX 9060 XT), a latência real só sai do teste da v0.1.0.
- **Nome e visual:** grafo e orbe são ideias genéricas; não copiar o logo, as cores exatas nem o nome do personagem.
