# Nora's brain: local and cloud (v0.3.0)

Nora has three brains and a **router** that decides who answers each question:

| Brain | Where it runs | Cost | What for |
|---|---|---|---|
| **Local** (Ollama, `qwen3.5:9b`) | your PC | free | everyday conversation, fast and private |
| **ChatGPT** (OpenAI API) | cloud | pay per use | the default for complex questions and tasks |
| **Claude** (Anthropic API) | cloud | pay per use | ChatGPT's fallback (and whatever you ask it for by name) |

For you, nothing changes: the answer comes out with the same voice, personality, memory and emotion, wherever it comes from.

## Turning the cloud on (once)

Both clouds are optional and independent: configure one, both or neither.

1. Create the keys:
   - ChatGPT: [platform.openai.com](https://platform.openai.com) (**API keys**). The API is billed separately from the ChatGPT subscription.
   - Claude: [console.anthropic.com](https://console.anthropic.com) (**API Keys**).

   Set a **spending limit** in each dashboard, so there are no surprises.
2. In Nora's `.env` (copy it from `.env.example` if you do not have one):

   ```
   OPENAI_API_KEY=sua-chave-da-openai
   ANTHROPIC_API_KEY=sua-chave-da-anthropic
   ```

3. Install the cloud packages (inside the `.venv`):

   ```powershell
   python -m pip install -e ".[nuvem]"
   ```

4. Check: `nora --verificar` shows each key, each package and, with a key, whether the connection worked (`ChatGPT ok, chave aceita...`, `Claude ok, chave aceita...`).

With only the Claude key, it plays ChatGPT's role, without warning. With no key at all, Nora works with the local brain only.

## How the router decides

You do not need any command: in automatic mode she decides on her own, through three paths.

- **Triage:** questions that look heavy go straight to the cloud, without depending on the local brain judging itself capable (small models tend to think themselves too capable): code, math and formulas, "analisa", "compara", "explica em detalhes", plans and schedules, texts to write, summarize or translate, and long questions or questions with pasted text.
- **The local model passes it on:** in everyday conversation, the local brain answers. When it finds the question too hard itself, it passes it to the cloud.
- **Second chance:** if the local model answered and you complain ("não é isso", "tá errado", "não entendi", "explica melhor"), the question goes to the cloud.

In the cloud, the order is: **ChatGPT → Claude → local**. While the cloud thinks, Nora says a holding phrase ("Deixa eu pensar com calma.").

- **ChatGPT with no answer, Claude answers:** if ChatGPT errors (no internet, key rejected, no credits), refuses the question or returns nothing, the same question goes to Claude, and `[cérebro] ... Pedi ao Claude.` shows. If both fail, the local model answers.
- **Dropped midway:** if the answer started coming out and the brain dropped (cloud or local), Nora does not stitch a whole other answer from another brain (you would hear the beginning twice): she says the answer was left halfway. In the history it is marked `"situacao": "interrompida"` and does not go to memory. The question is kept as a **pending item**: say "termina a resposta que ficou pela metade" for her to answer again, in full (see [MEMORIA.md](MEMORIA.md#half-finished-answers)).
- **Each attempt is recorded** (which brain, whether it answered or the kind of failure, and the time until it started), so [self-improvement](AUTO_MELHORIA.md) can find what repeats. Switching to the fallback only happens before the answer starts; the holding phrase does not count as a start.
- **Calling by name:** "pergunta pro ChatGPT ...", "usa o Claude e me diz ...", "use o Claude para explicar fotossíntese" send **only that question** to whoever you called (the other one stays as fallback); the conversation mode does not change. On its own ("use o Claude"), it is a command and switches the mode. "use o cérebro local para ..." answers that question on the PC. If the one called is not configured, `[cérebro] O ChatGPT não está disponível (falta ...)` shows once and the other one answers.
- **Shortcut:** "pensa com calma" or "pergunta difícil" inside the question go straight to the cloud.
- **Local fallback:** if Ollama does not answer, the cloud answers, with a `[cérebro] ...` warning.
- **No cloud configured:** when a question should go up, `[cérebro] Essa pergunta era para a nuvem, mas ela não está disponível (ChatGPT: falta ...; Claude: falta ...)` shows once, and the local model answers.

With `--medir`, each answer shows who answered (`[local (qwen3.5:9b): ...]`, `[ChatGPT (gpt-5.5): ...]` or `[Claude Sonnet 5.5: ...]`), and the history stores it in each answer.

## Voice (or typed) commands

| Say | What happens |
|---|---|
| "use o cérebro local" | only Ollama answers (nothing goes to the cloud) |
| "use o ChatGPT" | the whole conversation goes to ChatGPT (the fast model; the hard ones use the heavy one); Claude stays as fallback |
| "use o Claude" | the whole conversation goes to Claude; ChatGPT stays as fallback |
| "modo automático" | back to the default (local talks, ChatGPT on the hard ones) |
| "modo jogo" | **frees the graphics card** (unloads the local model from memory) and answers everything through the cloud (the last one chosen: ChatGPT, or Claude after "use o Claude"); good for gaming with Nora on |
| "sair do modo jogo" | asks first ("Quer sair do modo jogo? ... Confirma?"); with "sim", goes back to thinking on the PC. "Não" cancels, and so does changing the subject |

Asking **about** a command does not run it: "como sair do modo jogo?" is answered, and the mode stays. The confirmation is rule-based, without calling any brain (the graphics card stays free). Mode switches are kept in the history as `"situacao": "comando"` and do not become a fact in memory.

In game mode, if the cloud does not answer (no internet, no key, usage limit), Nora does **not** use the local brain, so as not to occupy the graphics card again: she warns and suggests saying "sair do modo jogo".

A command with a request attached ("modo jogo, quanto falta pro meu aniversário?") does both: switches the mode and answers.

The switch lasts until you close Nora. To change the default, use `[roteador] modo` in the config.

## Settings (`config/local.toml`)

```toml
[modelos.openai]
rapido = "gpt-5.5"              # conversation after "use o ChatGPT" and in game mode
pesado = "gpt-5.5"              # the complex questions
esforco_rapido = "low"          # none, minimal, low, medium, high, xhigh, max
esforco_pesado = "medium"

[modelos.nuvem]
rapido = "claude-haiku-5-5"     # conversation after "use o Claude"
pesado = "claude-sonnet-5-5"    # the complex ones, when Claude answers
esforco_rapido = "low"          # low, medium, high, xhigh, max
esforco_pesado = "medium"

[roteador]
modo = "automatico"             # automatico, local or nuvem
complexas = "openai"            # who tries first: "openai" (ChatGPT) or "anthropic" (Claude)
escalar = true                  # the local model may pass the hard ones to the cloud
triagem = true                  # heavy-looking questions go straight up; a complaint gives a second chance
```

To invert the order (Claude first, ChatGPT as fallback), use `complexas = "anthropic"`. Model names change over time: check the available ones in each company's dashboard and change them here; `--verificar` says whether the heavy model exists for your key.

Higher effort makes answers better, but slower and more expensive. For real-time voice, `low` and `medium` are usually the balance.

On models that accept it (Sonnet 5.5, Opus 5.5), if Claude refuses a question for safety reasons, the API itself retries the request on a model it indicates (`fallbacks: "default"`), without you doing anything.

## Privacy and cost

- What goes to the cloud is **only the question the cloud answers**, with the persona, that question's memory notes and the recent conversation. Everyday conversation stays on the PC. If ChatGPT fails, the same question also goes to Claude.
- With "use o cérebro local", nothing leaves your computer.
- The cost depends on use. Haiku is quite cheap; Sonnet costs more, so it only comes in on hard questions. Track spending in the OpenAI and Anthropic dashboards.

## Limits of this version

- Triage looks at words, not meaning: sometimes it sends something simple to the cloud ("organiza minha semana" goes as a plan) or lets something hard written in an ordinary way through. The second chance covers the second case; if triage sends too much to the cloud, turn it off with `triagem = false`.
- A short sentence with a brain's name and only command words ("usa o Claude agora, por favor") is read as a command. If the request has content, it is answered.
