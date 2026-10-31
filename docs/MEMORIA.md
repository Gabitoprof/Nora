# Memória (v0.2.0)

A Nora lembra de você entre uma conversa e outra. Tudo fica num arquivo **só na sua máquina**: `data/memoria.db` (a pasta `data` nunca vai para o GitHub). Para mudar o lugar, use `[caminhos] dados` no `config/local.toml`.

## Como funciona

1. **Ela anota.** Depois de cada resposta, em segundo plano, o modelo local relê a troca e anota o que vale lembrar sobre você: **fatos duradouros** (preferências, rotina, pessoas próximas, animais), **datas e planos** e **acontecimentos marcantes**, com a data ("Gabriel faz aniversário em 31 de outubro", "Em 30/10/2026 o cachorro do Gabriel fugiu e foi encontrado perto de casa"). Na resposta seguinte aparece `[memória] anotei: ...`. Fatos quase iguais são juntados: o mais novo substitui o antigo.
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

## Ver e editar

| Comando | O que faz |
|---|---|
| `nora memoria listar` | Os 20 fatos mais recentes, com o número de cada um e o total. `--pagina 2` para os anteriores, `--contendo cachorro` para filtrar, `--todos` para ver tudo |
| `nora memoria buscar prova de cálculo` | Os fatos mais parecidos com o texto, com a nota de parecença (0 a 1) |
| `nora memoria lembrar Gabriel prefere chá` | Guarda um fato à mão |
| `nora memoria esquecer 12` | Apaga o fato nº 12 |
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
```

## Limites desta versão

- A curadoria usa o mesmo modelo da conversa (Qwen 9B): às vezes anota algo inútil ou deixa passar um fato. Use `listar` e `esquecer` para limpar.
- Ainda não dá para pedir por voz "esquece isso" ou "o que você sabe sobre mim?": use os comandos acima.
- A memória guarda fatos, não ainda a camada de **conhecimento** (boas respostas da API reaproveitadas), que depende do roteador da v0.3.0.
