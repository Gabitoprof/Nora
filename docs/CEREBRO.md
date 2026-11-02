# Cérebro da Nora: local e nuvem (v0.3.0)

A Nora tem dois cérebros e um **roteador** que decide quem responde cada pergunta:

| Cérebro | Onde roda | Custo | Para quê |
|---|---|---|---|
| **Local** (Ollama, `qwen3.5:9b`) | seu PC | grátis | a conversa do dia a dia, rápida e privada |
| **Claude** (API da Anthropic) | nuvem | pago por uso | as perguntas difíceis, o modo nuvem e o modo jogo |

Para você, nada muda: a resposta sai com a mesma voz, a mesma personalidade, a mesma memória e a mesma emoção, venha de onde vier.

## Instalar o Claude (uma vez)

1. Crie uma chave em [console.anthropic.com](https://console.anthropic.com) (**API Keys**). Defina um **limite de gasto** no Console, para não ter surpresa.
2. No `.env` da Nora (copie do `.env.example` se não tiver):

   ```
   ANTHROPIC_API_KEY=sua-chave
   ```

3. Instale o pacote do Claude:

   ```powershell
   pip install -e ".[nuvem]"
   ```

4. Confira: `nora --verificar` deve mostrar a chave **definida** e o pacote do Claude **instalado**.

Sem a chave, a Nora funciona igual a antes, só com o cérebro local.

## Como o roteador decide

- **Automático (padrão):** o cérebro local conversa. Quando acha a pergunta difícil demais para ele (contas complexas, código, uma análise detalhada, um plano com muitas etapas), passa adiante, e a pergunta sobe para o Claude. Enquanto o Claude pensa, a Nora diz uma frase de espera ("Deixa eu pensar com calma.").
- **Pedido direto:** "pensa com calma", "pergunta difícil", "pergunta pro Claude" ou "usa o Claude" dentro da pergunta vão direto para o Claude.
- **Reserva:** se o Ollama não responder, o Claude responde. Se o Claude falhar (sem internet, chave errada, limite de uso), o local responde. Nos dois casos aparece um aviso `[cérebro] ...`.

Com `--medir`, cada resposta mostra quem respondeu (`[local (qwen3.5:9b): ...]` ou `[Claude Sonnet 5.5: ...]`), e o histórico guarda isso em cada resposta.

## Comandos de voz (ou digitados)

| Diga | O que acontece |
|---|---|
| "use o cérebro local" | só o Ollama responde (nada vai para a nuvem) |
| "use o Claude" | tudo vai para o Claude (o modelo rápido; "pensa com calma" usa o pesado) |
| "modo automático" | volta ao padrão |
| "modo jogo" | **libera a placa de vídeo** (tira o modelo local da memória) e responde tudo pela nuvem; bom para jogar com a Nora ligada |
| "sair do modo jogo" | volta a pensar no PC |

A troca vale até você fechar a Nora. Para mudar o padrão, use `[roteador] modo` na config.

## Ajustes (`config/local.toml`)

```toml
[modelos.nuvem]
rapido = "claude-haiku-5-5"     # conversa no modo nuvem e no modo jogo
pesado = "claude-sonnet-5-5"    # as perguntas difíceis
esforco_rapido = "low"          # quanto pensa antes de responder: low, medium, high, xhigh, max
esforco_pesado = "medium"

[roteador]
modo = "automatico"             # automatico, local ou nuvem
escalar = true                  # o local pode passar as difíceis para o Claude
```

Esforço mais alto deixa as respostas melhores, mas mais lentas e mais caras. Para voz em tempo real, `low` e `medium` costumam ser o equilíbrio.

Nos modelos que aceitam (Sonnet 5.5, Opus 5.5), se o Claude recusar uma pergunta por segurança, a própria API repete o pedido num modelo indicado por ela (`fallbacks: "default"`), sem você fazer nada.

## Privacidade e custo

- O que vai para a nuvem é **só a pergunta que o Claude responde**, com a persona e as notas da memória daquela pergunta. A conversa do dia a dia fica no PC.
- Com "use o cérebro local", nada sai do seu computador.
- O custo depende do uso. O Haiku é bem barato; o Sonnet custa mais, por isso só entra nas perguntas difíceis. Acompanhe o gasto no Console da Anthropic.

## Limites desta versão

- O cérebro local às vezes passa adiante perguntas que conseguiria responder, ou responde sozinho algumas que deveriam subir. Se acontecer muito, desligue com `escalar = false` e use os pedidos diretos ("pensa com calma").
- Trocar a **voz** por comando e o índice das notas do Obsidian ainda vêm nesta etapa.
