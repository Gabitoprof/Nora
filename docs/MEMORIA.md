# Memória (v0.2.0)

A Nora lembra de você entre uma conversa e outra. Tudo fica num arquivo **só na sua máquina**: `data/memoria.db` (a pasta `data` nunca vai para o GitHub). Para mudar o lugar, use `[caminhos] dados` no `config/local.toml`.

## Como funciona

1. **Ela anota.** Depois de cada resposta, em segundo plano, o modelo local relê a troca e anota o que vale lembrar sobre você: **fatos duradouros** (preferências, rotina, pessoas próximas, animais), **datas e planos** e **acontecimentos marcantes**, com a data ("Ana faz aniversário em 12 de março", "Em 05/03/2026 o gato da Ana fugiu e foi encontrado perto de casa"). Na resposta seguinte aparece `[memória] anotei: ...`. Fatos quase iguais são juntados: o mais novo substitui o antigo.
   Cada fato vai para uma **área** (saúde, trabalho, estudos, família, pets...). Ela reaproveita as áreas que já existem e **cria uma nova** quando aparece um assunto novo.
2. **Ela guarda tudo.** Cada pergunta e resposta também fica guardada **inteira**, mesmo quando não vira fato. Assim ela lembra de qualquer coisa que você disse.
3. **Ela lembra.** Antes de responder, busca os fatos e os **trechos de conversas antigas** mais parecidos com a pergunta (por significado, não por palavra exata) e lê junto. Se você perguntar "onde eu achei meu cachorro?", ela acha o trecho em que você contou isso.
4. **Você manda.** Dá para ver, acrescentar e apagar o que ela sabe (abaixo).

O modelo em si não muda: ele fica mais esperto sobre você porque recebe a memória certa a cada pergunta. O histórico completo continua em `data/historico/`, palavra por palavra.

## Instalar (uma vez)

```powershell
ollama pull bge-m3
```

```powershell
pip install -e ".[dev,voz,kokoro,memoria]"
```

- **`bge-m3`** transforma textos em vetores de significado (multilíngue, licença MIT, ~1,2 GB, roda na GPU junto com o Qwen).
- **`memoria`** instala o `sqlite-vec` (MIT/Apache) para a busca ficar rápida. Sem ele, a busca funciona do mesmo jeito, só mais devagar quando houver muitos milhares de fatos.

Confira com `nora --verificar`: a linha **Memória** deve dizer `ok`.

## Agenda: lembrar pelo dia

A busca por significado acha "quando é minha prova?", mas não acha "o que tenho amanhã?": a pergunta não tem nenhuma palavra em comum com "prova em 21/11". Por isso, todo fato com data também vai para uma **agenda**:

- **Ao anotar:** a curadoria transforma "amanhã", "sexta", "dia 21" e "21/11" em datas de verdade e guarda o fato na agenda (aniversários e datas comemorativas ficam marcados como **todo ano**). Na conversa aparece `[memória] anotei: ... (agenda: 21/11/2026)`.
- **Ao responder:** ela sempre lê o que está marcado para os **próximos 7 dias** (`agenda_dias`) e, se a pergunta falar de um período, o que está marcado nele. Pergunte do jeito natural: "o que tenho amanhã?", "tenho algo essa semana?", "e na sexta?", "e no dia 21?", "o que tem em dezembro?", "quando é meu aniversário?".
- **Fatos antigos:** os que já tinham data escrita no texto entram na agenda sozinhos, na primeira vez que a memória é aberta.

## Aprender pela conversa: pronúncia e jeito de falar

Você ensina conversando, e ela guarda:

- **Pronúncia:** "Nora, você fala 'houje', o certo é 'ôje'." A curadoria anota a palavra e como falar, e na conversa aparece `[memória] aprendi a pronúncia: hoje → ôje`. Vale na hora, para qualquer voz (ElevenLabs, Piper, Kokoro, ComfyUI) e também para o `gerar-dataset`, então a próxima voz treinada já nasce com a pronúncia certa. Dica: para ensinar pronúncia, **digite** a correção; falando, o Whisper escreve "hoje" das duas vezes.
- **Jeito de falar:** "Não precisa repetir minha pergunta", "Seja mais direta", "Me chama pelo nome." Ela guarda como preferência (`[memória] vou lembrar de: ...`) e segue em todas as conversas: as preferências vão junto em toda resposta, não só quando o assunto é parecido.

Pedidos só para aquela resposta ("resume isso") não viram preferência.

## Ver e editar

| Comando | O que faz |
|---|---|
| `nora memoria listar` | Os 20 fatos mais recentes, com o número de cada um e o total. `--pagina 2` para os anteriores, `--contendo cachorro` para filtrar, `--todos` para ver tudo |
| `nora memoria areas` | As áreas da memória (saúde, trabalho, estudos...) e quantos fatos cada uma tem |
| `nora memoria listar --area saúde` | Só os fatos de uma área |
| `nora memoria buscar prova de cálculo` | Os fatos mais parecidos com o texto, com a nota de parecença (0 a 1) |
| `nora memoria lembrar Ana prefere chá` | Guarda um fato à mão |
| `nora memoria esquecer 12` | Apaga o fato nº 12 |
| `nora memoria agenda` | Os compromissos e datas dos próximos 30 dias (`--dias 90` para mais, `--passados 7` para ver também a semana que passou) |
| `nora memoria marcar 21/11/2026 prova de cálculo` | Põe um compromisso na agenda à mão (e guarda como fato). `--anual` para o que repete todo ano |
| `nora memoria pronuncias` | As pronúncias que ela aprendeu. `nora memoria pronuncias hoje ôje` ensina uma à mão; `--esquecer hoje` apaga |
| `nora memoria preferencias` | O que você pediu sobre o jeito de ela falar. `nora memoria preferencias "Seja mais direta."` guarda à mão; `--esquecer 2` apaga |
| `nora memoria desmarcar 3` | Tira o evento nº 3 da agenda (o fato continua na memória) |
| `nora memoria importar` | Lê as conversas antigas de `data/historico/` e tira fatos delas (pode demorar; dá para rodar de novo, ele continua de onde parou) |

Com `--medir`, cada resposta mostra quantos fatos ela usou (`lembrou N fatos`).

## Ajustes (`config/local.toml`)

```toml
[memoria]
ativa = true                 # false desliga tudo
curadoria = true             # false: ela lembra, mas não anota fatos novos sozinha
fatos_por_pergunta = 5       # quantos fatos ela lê antes de responder
similaridade_minima = 0.45   # suba se ela trouxer fatos sem relação; desça se esquecer coisas
modelo_embeddings = "bge-m3"
agenda_dias = 7              # quantos dias à frente da agenda ela lê antes de responder (0 = não)
```

## Limites desta versão

- A curadoria usa o mesmo modelo da conversa (Qwen 9B): às vezes anota algo inútil ou deixa passar um fato. Use `listar` e `esquecer` para limpar.
- Ainda não dá para pedir por voz "esquece isso" ou "o que você sabe sobre mim?": use os comandos acima.
- A memória guarda fatos, não ainda a camada de **conhecimento** (boas respostas da API reaproveitadas), que depende do roteador da v0.3.0.
