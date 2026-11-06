# Second Brain da Nora (v0.3.1)

As memórias que a Nora já consolidou viram notas no seu Obsidian, ligadas por área, por nomes que aparecem em mais de uma memória e pelos meses da agenda. Você navega pelo grafo do Obsidian ou pelo **mapa da memória**, uma página que mostra a rede como neurônios ligados.

**A fala vem primeiro.** Nada disso acontece enquanto a Nora responde ou fala: as notas são escritas depois, quando ela está livre. Veja [Tempo de resposta](#tempo-de-resposta).

## Ligar (uma vez)

O Second Brain escreve no seu vault, então vem **desligado**. No `config/local.toml`:

```toml
[notas]
pasta = "C:/Users/voce/Documents/Obsidian"   # o seu vault

[segundo_cerebro]
ativo = true
# pasta = "Nora Brain"                 # dentro do vault (padrão) ou um caminho absoluto
# areas_privadas = ["saúde", "finanças"]   # nunca viram nota (padrão)
```

Depois:

```bash
nora cerebro sincronizar
```

E, no Obsidian, abra a pasta `Nora Brain` ou o grafo (Ctrl+G).

## O que vai para o vault

```text
Nora Brain/
  Nora Brain.md          índice: áreas, meses da agenda e preferências
  Áreas/Estudos.md       uma nota por área, com as memórias dela
  Memórias/...md         uma nota por memória consolidada
  Nomes/...md            nomes (pessoas, lugares, siglas) que aparecem em 2 memórias ou mais
  Agenda/2026-11.md      memórias com data, por mês
  Preferências.md        como você pediu que ela fale
```

Exemplo (dados fictícios) de uma nota de memória:

```markdown
---
nora_id: "mem-000042"
nora_gerenciado: true
tipo: "memoria"
camada: "episodica"
area: "estudos"
emocao: "curiosa"
emocao_fonte: "tom da resposta da Nora"
data: "2026-11-21"
origem: "conversa de 2026-11-05"
criado_em: "2026-11-05T10:12:00"
atualizado_em: "2026-11-05T10:12:00"
tags:
  - "nora"
  - "nora/area/estudos"
  - "nora/tipo/memoria"
  - "nora/camada/episodica"
  - "nora/emocao/curiosa"
---

# Lia tem prova de Cálculo na Unifictícia em 21-11-2026

Lia tem prova de Cálculo na Unifictícia em 21/11/2026

## Ligações

- Área: [[Nora Brain/Áreas/Estudos|Estudos]]
- Menciona: [[Nora Brain/Nomes/Unifictícia|Unifictícia]] (nome que aparece em outras memórias)
- Agenda: [[Nora Brain/Agenda/2026-11|novembro de 2026]] (21/11/2026)
```

**O que não vai:**
- a transcrição das conversas (só as memórias que a curadoria já consolidou);
- as áreas de `areas_privadas`;
- pronúncias, respostas pela metade e os eventos da auto-melhoria;
- emoção inventada. O campo `emocao` é o **tom que a Nora usou** na conversa em que o fato surgiu (as etiquetas `{curiosa}`, `{calma}`... da resposta), não um sentimento seu. Sem etiqueta de tom, o campo não aparece. Para tirar: `emocoes = false`.

## Ligações (por que duas coisas se conectam)

| Ligação | De → para | Base |
|---|---|---|
| `pertence_a` | memória → área | a área que a curadoria anotou |
| `menciona` | memória → nome | o nome aparece no texto da memória e em pelo menos mais uma |
| `aconteceu_em` | memória → mês | a data que está na agenda |

Nenhuma ligação é inventada para o desenho ficar mais cheio: um nome que só aparece numa memória não vira nó, e o seu nome e o da Nora (da config) não contam, porque estão em quase tudo.

## Sincronização

- **Incremental:** compara a memória com o que já foi exportado e escreve só o que mudou. Repetir não duplica nada.
- **Correção:** o fato com texto novo troca a nota (o título acompanha) e a antiga sai.
- **Esquecer e apagar de vez:** a memória sai do vault e do mapa na próxima rodada, sem voltar por reimportação. Backups fora da Nora (Obsidian Sync, a lixeira do sistema, o plugin de recuperação de arquivos, OneDrive...) ela não controla: apague por lá também, se precisar.
- **Suas notas são intocáveis:** a Nora só mexe nos arquivos que ela mesma criou na pasta dela. Se já existe uma nota sua com o mesmo nome, ou se você editou uma nota dela, ela não sobrescreve nem apaga: vira conflito em `nora cerebro status`. Para devolver a nota a ela, apague a sua versão.
- **Sem ciclo:** o leitor de notas (`[notas]`) ignora a pasta do Second Brain, então as memórias não voltam como se fossem notas suas.
- **Queda de energia:** cada nota é escrita num arquivo temporário e trocada de uma vez; uma queda no meio deixa a versão anterior inteira. A rodada seguinte retoma do ponto em que parou, sem duplicar.
- **Vault fora do ar** (disco desconectado, pasta sem permissão): a Nora continua conversando; o erro fica em `nora cerebro status` (só o tipo do erro, sem conteúdo) e a próxima rodada tenta de novo.

## Mapa da memória

Peça falando ("Nora, mostre seu segundo cérebro", "abra o mapa da memória", "visualize suas conexões") ou pelo terminal (`nora cerebro mapa --abrir`). O mapa é uma página só, sem internet e sem bibliotecas de fora, em `data/segundo_cerebro/mapa.html`, montada na sincronização. Abrir não recalcula nada.

| No mapa | Significa |
|---|---|
| Cor do nó | área da memória |
| Halo colorido | tom da conversa (as mesmas cores da HUD) |
| Tamanho | número de ligações (com limite) |
| Pulso branco | memória atualizada nos últimos 7 dias |
| Ligações surgindo ao abrir | animação das ligações reais; nenhuma memória é criada |

Clique num nó para ver a ficha: área, camada, origem, data e **por que se liga** a cada vizinho, com o link para abrir a nota no Obsidian. O link usa o caminho completo do arquivo (`obsidian://open?path=...`), então funciona com qualquer nome de vault; só precisa que a pasta do vault já tenha sido aberta no Obsidian alguma vez (Abrir pasta como vault). Não precisa de plugin. Busca, filtros por área, tipo e tom, zoom e arrasto. Com mais de 900 nós, o mapa abre só com áreas, nomes e meses, e as memórias aparecem ao clicar ou em "Ver tudo".

**Privacidade:** o texto das memórias abre escondido (borrado), e aparece no botão "Mostrar textos". Para abrir já visível: `mostrar_texto_no_mapa = true`.

### Cores

Áreas (cor do nó):

| Área | Cor |
|---|---|
| Trabalho | `#2F6BFF` azul |
| Pessoal | `#F09BD8` rosa/lilás |
| Saúde | `#4ADE80` verde |
| Família | `#FBBF24` amarelo quente |
| Estudos | `#22D3EE` ciano |
| Projetos | `#FF8A3D` laranja |
| Rotina | `#CBD5E1` prata |
| Finanças | `#059669` verde-esmeralda |
| Espiritualidade | `#A855F7` violeta |
| Tecnologia | `#7C8CFF` azul elétrico |
| Outras áreas | uma cor fixa da reserva, sempre a mesma para a mesma área |

Tons (halo): **as mesmas cores da HUD**, lidas do mesmo arquivo, `src/nora/paleta.json` (em Python, `nora.paleta`), com os mesmos nomes das etiquetas de `emocao.py`. Não há um segundo sistema de cores; para mudar uma cor, mude só esse arquivo:

| Tom | Cor |
|---|---|
| alegre, empolgada | `#F0C66A` |
| carinhosa | `#E3A4BD` |
| calma | `#66D4CB` turquesa |
| séria | `#80A8F6` |
| triste | `#AA9ACF` lavanda |
| curiosa | `#DF876A` terracota |
| neutra | `#C9C9C9` |

## Contrato para a HUD de memória

O Second Brain não depende da HUD principal (v0.4.0) e não mexe nela. O que ele produz segue um contrato versionado, para uma HUD de memória se ligar depois: [`src/nora/segundo_cerebro_contrato.json`](../src/nora/segundo_cerebro_contrato.json) (versão 1). Ele define:
- o arquivo `data/segundo_cerebro/grafo.json`, com `versao`, `nos`, `ligacoes` e `legenda`;
- os tipos de nó e de ligação;
- o campo `texto`, marcado como privado;
- as emoções, com os mesmos nomes do evento `emocao` da HUD;
- o evento `segundo_cerebro_atualizado`, reservado para quando a HUD de memória existir (na v0.3.1 só o arquivo é gravado).

## Tempo de resposta

O caminho crítico é este:

```text
Fala → VAD/STT → busca na memória (a mesma de antes) → LLM → TTS → reprodução
                                                              │
               curadoria (já era em segundo plano) ◄──────────┘ (depois da resposta)
                        │
                        └─► avisar(): só levanta um sinal (Event.set), nunca espera
                                  │
                 linha "nora-segundo-cerebro" (outra thread)
                   espera conversa.ocupada e conversa.falando ficarem desligados
                   lê a memória numa conexão só de leitura
                   escreve as notas que mudaram (para no meio se a Nora voltar a falar)
                   grava grafo.json e mapa.html
                                  │
                   mapa no navegador (outro processo, sob pedido)
```

Garantias, com testes automatizados em `tests/test_segundo_cerebro.py`:
- **Sem escrita no caminho da fala:** a conversa só chama `avisar()`. O teste coloca uma sincronização de 3 s e confere que a resposta sai em menos de 1 s, e que a sincronização roda só na linha `nora-segundo-cerebro`.
- **Espera a voz:** `conversa.falando` fica ligado do começo da resposta até o último áudio tocar. A linha não começa enquanto isso, e para entre um arquivo e outro se a Nora voltar a falar.
- **Sem modelo:** nenhuma chamada a modelo, embeddings ou nuvem. Ela usa o que a curadoria já produziu, então não acorda o cérebro local no modo jogo.
- **Falha isolada:** um erro no vault ou na linha não chega à conversa.
- **Mapa separado:** o mapa roda no navegador, em outro processo. Abrir, fechar ou travar o mapa não toca no áudio.
- **Escuta contínua:** a linha não lê o teclado nem o microfone.

### Medição

`python scripts/medir_segundo_cerebro.py` roda o caminho da voz de verdade (`responder_falando`, `Locutor`, tocar), com um cérebro e uma voz falsos de tempo fixo, em três cenários: desligado, ligado com memória grande (uso real) e estresse (a sincronização reescrevendo tudo sem parar, ignorando se a Nora fala, que é um pior caso artificial). Orçamento definido antes de medir: **p95 do início do áudio até 5% acima do cenário desligado**, sem aumento relevante das pausas entre trechos.

Resultado em 05/11/2026 (Linux x86_64 na nuvem, Python 3.13, 60 respostas por cenário, memória com 2000 fatos; cérebro falso com primeiro pedaço em 150 ms e voz falsa de 120 ms + 2 ms por caractere):

| Cenário | Início do áudio p50 | p95 | p99 | Desvio | Δ p95 | Maior pausa entre trechos (p95) | Sincronizações |
|---|---|---|---|---|---|---|---|
| Desligado | 494,2 ms | 495,0 ms | 496,5 ms | 0,5 ms | referência | 0,1 ms | 0 |
| Ligado (uso real) | 493,9 ms | 494,7 ms | 497,8 ms | 0,6 ms | −0,1% | 0,1 ms | 61 |
| Estresse (pior caso artificial) | 493,7 ms | 494,6 ms | 514,7 ms | 3,1 ms | −0,1% | 0,1 ms | 220 |

**Leitura:**
- **Ligado:** dentro do orçamento. O Second Brain rodou 61 vezes, uma por resposta e sempre depois dela, sem mudar o começo da fala nem as pausas.
- **Estresse:** a sincronização reescreveu 2000 notas sem parar, inclusive enquanto a Nora falava. Ainda assim o p95 ficou igual; só o p99 subiu cerca de 18 ms, a disputa de CPU nos piores momentos. No uso real isso não acontece, porque a linha espera a voz.
- **Limite da medição:** o cérebro e a voz falsos só esperam; não usam CPU. O Ollama, o Kokoro e o Piper rodam em processos separados e o ElevenLabs na nuvem, então a disputa que importa é dentro do processo da Nora, que é a que esta medição cobre.

**Isso não é a homologação.** Falta medir no Windows com o modelo e a voz de verdade (checklist abaixo).

## Checklist de homologação (Windows + Obsidian)

1. `git switch feat/v0.3.1-second-brain` e `git pull`.
2. Sem o Second Brain (`ativo = false`): 10 perguntas parecidas em `nora falar --medir`; anote "começou a falar em".
3. Com `ativo = true`: as mesmas 10 perguntas. O p95 de "começou a falar em" não pode passar de 5% acima do passo 2 (as variações da nuvem entram na conta: repita se a rede oscilar).
4. Diga algo novo ("eu estudo com a Ana às quartas"), espere a resposta terminar e veja a nota aparecer em `Nora Brain/Memórias` em até ~1 minuto, sem pausa na fala.
5. Corrija ("não é às quartas, é às sextas"): a nota troca, a antiga some.
6. "Esquece que eu estudo com a Ana": a nota some do vault e do mapa.
7. Edite uma nota da Nora no Obsidian e mude o fato pela conversa: a sua edição fica, e `nora cerebro status` mostra o conflito.
8. Feche o Obsidian (ou renomeie o vault) e converse: a Nora responde normalmente; `nora cerebro status` mostra o erro; volte o vault e a rodada seguinte completa.
9. "Nora, mostre seu segundo cérebro": o mapa abre no navegador; continue conversando com ele aberto e animando, e compare "começou a falar em".
10. `nora ouvir` com várias falas seguidas: nenhuma fala perdida.
11. Modo jogo: o Ollama não carrega o modelo por causa do Second Brain (veja o uso de VRAM).

## As dez melhorias (A–J): estado e decisão

| ID | Melhoria | Antes | Nesta versão | Próximo passo |
|---|---|---|---|---|
| A | Memória em camadas | Parcial: fatos, histórico (episódios), agenda, preferências e contexto da sessão já eram separados, sem rótulo de camada | `camada` nas notas: `semantica` (fato), `episodica` (fato com data), `procedural` (preferências). Nenhuma tabela nova | v0.4.x: camada guardada no banco, curadoria classificando; "afetiva" separada da preferência |
| B | Grafo explícito | Ausente | Nós (memória, área, nome, mês, preferências) e ligações com tipo e base; nomes deduplicados sem acento e sem maiúscula; nome único não vira nó | v0.4.x: resolução de homônimos (duas "Ana"), relações declaradas pela curadoria (`participa_de`, `depende_de`) |
| C | Força e relevância | Parcial: data de atualização e similaridade na busca | Tamanho do nó = número de ligações; pulso = atualizado em 7 dias. Sem pontuação inventada | v0.5.x: "isso é importante" pela conversa, frequência de uso na resposta (o histórico já guarda quais fatos foram usados) |
| D | Esquecimento e retenção | Existia: esquecer, apagar de vez, bloqueio de reimportação | O vault e o mapa seguem a memória: o que sai dela sai das notas. Nada é esquecido por idade | v0.5.x: arquivar (fora do foco, consultável) e validade de fatos com data passada |
| E | Consolidação em lote | Parcial: curadoria em segundo plano por resposta | Sincronização em lote, incremental, idempotente e retomável, numa linha própria, sem nenhuma chamada nova a modelo | v0.4.x: agrupar várias menções do mesmo assunto numa nota de tema (sem LLM pago) |
| F | Memória explicável | Parcial: origem do fato e IDs das lembranças usadas no histórico | Cada ligação tem a base ("área anotada pela curadoria", 'o texto cita "X"', "data na agenda"); a ficha do mapa mostra origem, datas e o porquê de cada ligação | v0.4.x: "de onde veio isso?" respondido pela própria Nora |
| G | Contexto ativo | Parcial: a conversa da sessão já é o contexto curto, e a sessão não vira memória sozinha | Nada novo no caminho da fala (decisão do documento 2) | v0.4.x: nós usados na resposta destacados no mapa, por evento leve |
| H | Recuperação híbrida | Parcial: vetorial + agenda por data + contas de data (v0.3.1) | Não trocado (o documento pede medir antes) | v0.5.x: FTS5 para nomes próprios, com benchmark de precisão e latência contra a busca atual |
| I | Memória afetiva | Parcial: etiquetas de emoção na voz e preferências de tom | Tom da conversa guardado no fato (`fatos.emocao`, tirado das etiquetas da resposta, em segundo plano), opcional, com fonte e cores da HUD | v0.4.x: corrigir ou tirar o tom pela conversa |
| J | Visualização cognitiva | Ausente | Mapa (MVP funcional): cores por área, halo por tom, tamanho por ligações, pulso, revelação animada, busca, filtros, foco, ficha com o porquê, link para o Obsidian e modo de grafo grande | v0.4.x: integrar na HUD pelo contrato; 3D e agrupamento de aglomerados |

## Riscos e limites

- **Nomes próprios por regra:** uma palavra com maiúscula no meio da frase vira nome. Homônimos ("Ana" do trabalho e "Ana" da família) viram o mesmo nó, e um nome que começa a frase só conta se for sigla.
- **Títulos mudam com o texto:** um link escrito à mão para uma nota da Nora quebra se ela corrigir o fato. Use os links das notas de área, que ela atualiza.
- **Concorrência do Python:** a linha roda no mesmo processo da conversa. Ela espera a voz e para no meio se a Nora voltar a falar, mas uma rodada já em andamento ainda disputa a CPU por alguns milissegundos. O cenário de estresse da medição mostra o pior caso.
- **Plugins de grafo** que mostram tags como nós (`#nora` está em todas as notas) ou criam ligações adivinhadas ("inferred links") embolam o desenho: desligue essas opções para ver só as ligações da Nora.
- **O grafo nativo do Obsidian** colore por grupos de busca (tag, pasta), não por halo nem tamanho por relevância. Para ver as cores das áreas lá: Grafo → Grupos → `tag:#nora/area/estudos` com a cor da tabela. O mapa da Nora mostra o resto.
