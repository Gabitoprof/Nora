# Project base goal

> Name: **Nora**, for the project and for the assistant (the assistant's name is configurable).
> Technical details: [`PROJETO_ASSISTENTE_IA.md`](../PROJETO_ASSISTENTE_IA.md) · Map view: [`MAPA_MENTAL.md`](MAPA_MENTAL.md)

## In one sentence

Build a **personal AI assistant that talks by voice in real time**, with its own name, voice and personality, that runs mainly on my computer, remembers what we talked about and evolves with use.

## What it needs to be

1. **A natural conversation, not a voice command.** I say its name, ask a question and hear the answer in under 2 seconds (the final target is under 1 s). I can interrupt it while it speaks.
2. **Local first.** Everyday conversation runs on my PC, without depending on the internet or paying per use. Only heavy tasks go to external models (like ChatGPT and Claude), and the answer comes back in the same voice and personality.
3. **With a memory that evolves.** Everything we talk about is kept in a local database. It learns my facts and preferences, forgets what I ask it to and reuses good answers. Over time it depends less on the cloud, and it proposes improvements to itself, which only go in with my approval.
4. **With initiative.** It does not only answer: it speaks first when it makes sense, as in a morning briefing, a reminder or when it notices I arrived.
5. **Able to act.** Through tools on the MCP standard, it controls the PC, checks the agenda and the weather and, in the future, the house. Each new skill comes in as a plugin, without rebuilding the core.
6. **With visual presence.** A full-screen interface, with an orb that reacts to the voice and cards with the conversation content.
7. **Private.** My data, memories and images stay on my computer. Nothing personal goes to the repository.

## How we will get there

- **In stages**, each delivering a version that really works (v0.0.0 → v1.0.0).
- **Documented in the repository** and tracked in the mind map, which is updated at every stage.
- **Designed for my hardware** (AMD RX 9060 XT GPU), but with swappable parts (Vulkan, ROCm, CUDA and CPU) to run on other machines.
- **Open source:** in the end, anyone can install it and create their own assistant, with whatever name and voice they want.

## What is NOT the goal (for now)

- Copying existing characters or brands: the assistant has its own identity.
- Training a model from scratch: we use ready-made models, and the evolution comes from memory and, later, fine-tuning (LoRA).

## How to know it worked (v1.0.0)

- I talk to it by voice every day, fluidly, as with a person.
- It remembers me from one session to the next and takes initiative at the right moments.
- It performs real tasks by voice.
- Someone else can install it from GitHub and use it with their own assistant.
