# Cérebro da Nora: local e nuvem (v0.3.0)

A Nora tem três cérebros e um **roteador** que decide quem responde cada pergunta:

| Cérebro | Onde roda | Custo | Para quê |
|---|---|---|---|
| **Local** (Ollama, `qwen3.5:9b`) | seu PC | grátis | a conversa do dia a dia, rápida e privada |
| **ChatGPT** (API da OpenAI) | nuvem | pago por uso | o padrão para as perguntas e tarefas complexas |
| **Claude** (API da Anthropic) | nuvem | pago por uso | a reserva do ChatGPT (e o que você pedir a ele pelo nome) |

Para você, nada muda: a resposta sai com a mesma voz, a mesma personalidade, a mesma memória e a mesma emoção, venha de onde vier.

## Ligar a nuvem (uma vez)

As duas nuvens são opcionais e independentes: configure uma, as duas ou nenhuma.

1. Crie as chaves:
   - ChatGPT: [platform.openai.com](https://platform.openai.com) (**API keys**). A API é cobrada à parte da assinatura do ChatGPT.
   - Claude: [console.anthropic.com](https://console.anthropic.com) (**API Keys**).

   Defina um **limite de gasto** em cada painel, para não ter surpresa.
2. No `.env` da Nora (copie do `.env.example` se não tiver):

   ```
   OPENAI_API_KEY=sua-chave-da-openai
   ANTHROPIC_API_KEY=sua-chave-da-anthropic
   ```

3. Instale os pacotes das nuvens (dentro do `.venv`):

   ```powershell
   python -m pip install -e ".[nuvem]"
   ```

4. Confira: `nora --verificar` mostra cada chave, cada pacote e, com chave, se a conexão deu certo (`ChatGPT ok, chave aceita...`, `Claude ok, chave aceita...`).

Só com a chave do Claude, ele faz o papel do ChatGPT, sem aviso. Sem nenhuma chave, a Nora funciona só com o cérebro local.

## Como o roteador decide

Você não precisa de comando nenhum: no automático, ela decide sozinha, por três caminhos.

- **Triagem:** perguntas com cara de pesadas vão direto para a nuvem, sem depender do cérebro local se julgar capaz (modelos pequenos costumam se achar capazes demais): código, contas e fórmulas, "analisa", "compara", "explica em detalhes", planos e cronogramas, textos para escrever, resumir ou traduzir, e perguntas longas ou com texto colado.
- **O local passa adiante:** na conversa do dia a dia, o cérebro local responde. Quando ele mesmo acha a pergunta difícil demais, passa para a nuvem.
- **Segunda chance:** se o local respondeu e você reclamar ("não é isso", "tá errado", "não entendi", "explica melhor"), a pergunta vai para a nuvem.

Na nuvem, a ordem é: **ChatGPT → Claude → local**. Enquanto a nuvem pensa, a Nora diz uma frase de espera ("Deixa eu pensar com calma.").

- **ChatGPT sem resposta, Claude responde:** se o ChatGPT der erro (sem internet, chave recusada, sem créditos), recusar a pergunta ou não devolver nada, a mesma pergunta vai para o Claude, e aparece `[cérebro] ... Pedi ao Claude.`. Se os dois falharem, o local responde.
- **Caiu no meio:** se a resposta começou a sair e o cérebro caiu (nuvem ou local), a Nora não emenda outra resposta inteira de outro cérebro (você ouviria o começo duas vezes): avisa que a resposta ficou pela metade. No histórico, ela fica marcada como `"situacao": "interrompida"` e não vai para a memória.
- **Chamar pelo nome:** "pergunta pro ChatGPT ...", "usa o Claude e me diz ...", "use o Claude para explicar fotossíntese" mandam **só aquela pergunta** para quem você chamou (o outro fica de reserva); o modo da conversa não muda. Sozinho ("use o Claude"), é comando e troca o modo. "use o cérebro local para ..." responde aquela pergunta no PC. Se o chamado não estiver configurado, aparece uma vez `[cérebro] O ChatGPT não está disponível (falta ...)` e o outro responde.
- **Atalho:** "pensa com calma" ou "pergunta difícil" dentro da pergunta vão direto para a nuvem.
- **Reserva do local:** se o Ollama não responder, a nuvem responde, com aviso `[cérebro] ...`.
- **Sem nenhuma nuvem configurada:** quando uma pergunta devia subir, aparece uma vez `[cérebro] Essa pergunta era para a nuvem, mas ela não está disponível (ChatGPT: falta ...; Claude: falta ...)`, e o local responde.

Com `--medir`, cada resposta mostra quem respondeu (`[local (qwen3.5:9b): ...]`, `[ChatGPT (gpt-5.5): ...]` ou `[Claude Sonnet 5.5: ...]`), e o histórico guarda isso em cada resposta.

## Comandos de voz (ou digitados)

| Diga | O que acontece |
|---|---|
| "use o cérebro local" | só o Ollama responde (nada vai para a nuvem) |
| "use o ChatGPT" | a conversa toda vai para o ChatGPT (o modelo rápido; as difíceis usam o pesado); o Claude fica de reserva |
| "use o Claude" | a conversa toda vai para o Claude; o ChatGPT fica de reserva |
| "modo automático" | volta ao padrão (local conversa, ChatGPT nas difíceis) |
| "modo jogo" | **libera a placa de vídeo** (tira o modelo local da memória) e responde tudo pela nuvem (pela última escolhida: ChatGPT, ou o Claude depois de "use o Claude"); bom para jogar com a Nora ligada |
| "sair do modo jogo" | volta a pensar no PC |

No modo jogo, se a nuvem não responder (sem internet, sem chave, limite de uso), a Nora **não** usa o cérebro local, para não ocupar de novo a placa de vídeo: ela avisa e sugere dizer "sair do modo jogo".

Comando com pedido junto ("modo jogo, quanto falta pro meu aniversário?") faz as duas coisas: troca o modo e responde.

A troca vale até você fechar a Nora. Para mudar o padrão, use `[roteador] modo` na config.

## Ajustes (`config/local.toml`)

```toml
[modelos.openai]
rapido = "gpt-5.5"              # conversa depois de "use o ChatGPT" e no modo jogo
pesado = "gpt-5.5"              # as perguntas complexas
esforco_rapido = "low"          # none, minimal, low, medium, high, xhigh, max
esforco_pesado = "medium"

[modelos.nuvem]
rapido = "claude-haiku-5-5"     # conversa depois de "use o Claude"
pesado = "claude-sonnet-5-5"    # as complexas, quando o Claude responde
esforco_rapido = "low"          # low, medium, high, xhigh, max
esforco_pesado = "medium"

[roteador]
modo = "automatico"             # automatico, local ou nuvem
complexas = "openai"            # quem tenta primeiro: "openai" (ChatGPT) ou "anthropic" (Claude)
escalar = true                  # o local pode passar as difíceis para a nuvem
triagem = true                  # perguntas com cara de pesadas vão direto; reclamação dá segunda chance
```

Para inverter a ordem (Claude primeiro, ChatGPT de reserva), use `complexas = "anthropic"`. Os nomes dos modelos mudam com o tempo: confira os disponíveis no painel de cada empresa e troque aqui; o `--verificar` diz se o modelo pesado existe para a sua chave.

Esforço mais alto deixa as respostas melhores, mas mais lentas e mais caras. Para voz em tempo real, `low` e `medium` costumam ser o equilíbrio.

Nos modelos que aceitam (Sonnet 5.5, Opus 5.5), se o Claude recusar uma pergunta por segurança, a própria API repete o pedido num modelo indicado por ela (`fallbacks: "default"`), sem você fazer nada.

## Privacidade e custo

- O que vai para a nuvem é **só a pergunta que a nuvem responde**, com a persona, as notas da memória daquela pergunta e a conversa recente. A conversa do dia a dia fica no PC. Se o ChatGPT falhar, a mesma pergunta vai também para o Claude.
- Com "use o cérebro local", nada sai do seu computador.
- O custo depende do uso. O Haiku é bem barato; o Sonnet custa mais, por isso só entra nas perguntas difíceis. Acompanhe o gasto nos painéis da OpenAI e da Anthropic.

## Limites desta versão

- A triagem olha palavras, não o sentido: às vezes manda para a nuvem algo simples ("organiza minha semana" vai como plano) ou deixa passar algo difícil escrito de um jeito comum. A segunda chance cobre o segundo caso; se a triagem mandar coisa demais para a nuvem, desligue com `triagem = false`.
- Uma frase curta com o nome de um cérebro e só palavras de comando ("usa o Claude agora, por favor") é lida como comando. Se o pedido tiver conteúdo, ele é respondido.
