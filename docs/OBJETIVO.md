# Objetivo base do projeto

> Nome provisório: **Ella**. O nome final do projeto e do assistente ainda está em aberto.
> Detalhes técnicos: [`PROJETO_ASSISTENTE_IA.md`](../PROJETO_ASSISTENTE_IA.md) · Visão em mapa: [`MAPA_MENTAL.md`](MAPA_MENTAL.md)

## Em uma frase

Construir um **assistente de IA pessoal que conversa por voz em tempo real**, com nome, voz e personalidade próprios, que roda principalmente no meu computador, lembra do que conversamos e evolui com o uso.

## O que ele precisa ser

1. **Uma conversa natural, não um comando de voz.** Eu falo o nome dele, faço uma pergunta e ouço a resposta em menos de 2 segundos (a meta final é menos de 1 s). Posso interromper enquanto ele fala.
2. **Local primeiro.** A conversa do dia a dia roda no meu PC, sem depender de internet nem pagar por uso. Só as tarefas pesadas vão para modelos externos (como o Claude), e a resposta volta com a mesma voz e personalidade.
3. **Com memória que evolui.** Tudo o que conversamos fica guardado num banco local. Ele aprende meus fatos e preferências e reaproveita boas respostas. Com o tempo, depende menos da nuvem.
4. **Com iniciativa.** Ele não só responde: fala primeiro quando faz sentido, como num briefing da manhã, num lembrete ou quando percebe que cheguei.
5. **Capaz de agir.** Por ferramentas no padrão MCP, ele controla o PC, consulta agenda e clima e, no futuro, a casa. Cada nova habilidade entra como um plugin, sem refazer o núcleo.
6. **Com presença visual.** Uma interface em tela cheia, com um orbe que reage à voz e cartões com o conteúdo da conversa.
7. **Privado.** Meus dados, memórias e imagens ficam no meu computador. Nada pessoal vai para o repositório.

## Como vamos chegar lá

- **Por etapas**, cada uma entregando uma versão que funciona de verdade (v0.0.0 → v1.0.0).
- **Documentado no repositório** e acompanhado no mapa mental, que é atualizado a cada etapa.
- **Pensado para o meu hardware** (GPU AMD RX 9060 XT), mas com peças trocáveis (Vulkan, ROCm, CUDA e CPU) para rodar em outras máquinas.
- **Open source:** no fim, qualquer pessoa pode instalar e criar o seu próprio assistente, com o nome e a voz que quiser.

## O que NÃO é o objetivo (por enquanto)

- A mesa com projetor e touch do vídeo de referência: fica para o futuro.
- Copiar personagens ou marcas existentes: o assistente tem identidade própria.
- Treinar um modelo do zero: usamos modelos prontos, e a evolução vem da memória e, mais tarde, de ajuste fino (LoRA).

## Como saber que deu certo (v1.0.0)

- Converso por voz com ele todos os dias, de forma fluida, como com uma pessoa.
- Ele lembra de mim entre uma sessão e outra e toma iniciativa nos momentos certos.
- Executa tarefas reais por voz.
- Outra pessoa consegue instalar a partir do GitHub e usar com o seu próprio assistente.
