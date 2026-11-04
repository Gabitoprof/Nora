# Auto-melhoria da Nora (supervisionada)

A Nora observa como foram as conversas e, uma vez por dia, propõe melhorias com base no que se repetiu. **Ela só propõe:** nada muda no código, nada é instalado e nada é publicado sem você decidir.

## O ciclo

```text
durante o dia: conversa → observador (só tempos, falhas e categorias)
na hora marcada: agrupa → diagnostica (regras) → propostas → relatório .md → aviso
você: aprovar | recusar | adiar
aprovada: gera a tarefa para desenvolver → branch isolada + testes → publicar só com nova autorização
```

## O que ela observa

Fica em `data/auto_melhoria/auto_melhoria.db`, só no seu PC:

- cada cérebro tentado em cada resposta: quem, o resultado (resposta, escalou, `erro_provedor`, `timeout`, `resposta_vazia`, `stream_interrompido`) e o tempo até o primeiro pedaço;
- comandos (como o modo jogo), respostas sem resposta ou canceladas;
- reclamações ("tá errado", "não entendi"), ligadas à resposta anterior, e quando o local respondeu algo que você rejeitou (`rota_suspeita`);
- o tempo da transcrição e da voz, e as falhas da voz.

**Não guarda o texto do que foi dito nem áudio:** só IDs, categorias, tempos e o nome do motor. Os eventos com mais de `dias_de_eventos` (30) são apagados no fechamento do dia.

## O relatório do dia

Na hora de `hora_relatorio` (padrão 20:00), se a Nora estiver aberta e não estiver respondendo nem no modo jogo, ela fecha o dia:

- agrupa os eventos por causa provável (tipo, etapa e motor);
- só vira proposta o que aconteceu pelo menos `min_ocorrencias` vezes (3): uma vez só não basta;
- respostas lentas contam acima dos limites `latencia_*_ms`;
- salva `data/auto_melhoria/relatorios/AAAA-MM-DD.md`.

Cada proposta tem número, evidência (quantas vezes, quando, mediana e maior tempo), causa provável, solução sugerida, benefícios estimados, impacto em tempo/custo/GPU, risco, testes exigidos, arquivos prováveis, prioridade e confiança.

- **Dia sem problemas:** o relatório diz só "Sem novas melhorias relevantes".
- **PC desligado na hora:** o relatório sai na próxima vez que você abrir a Nora, cobrindo o período que faltou, sem repetir.
- **O mesmo problema em outro dia:** atualiza a mesma proposta, sem duplicar.

**Como você fica sabendo:**
- uma notificação do Windows ("Nora: melhorias do dia"), e clicar nela abre o relatório;
- na próxima conversa, a linha `[melhorias] Relatório de 03/11: 2 proposta(s) para decidir`.

## Decidir

| Pela conversa | Pelo terminal | O que acontece |
|---|---|---|
| "quais melhorias você sugeriu?" | `nora melhorias listar` | lista as que esperam decisão |
| — | `nora melhorias relatorio --abrir` | abre o relatório mais recente |
| "aprova a melhoria 3" → "sim" | `nora melhorias aprovar 3` | aprovada para **desenvolver**: gera `data/auto_melhoria/tarefas/melhoria-3.md`, a especificação para o Codex. O código não muda |
| "recusa a melhoria 3" → "sim" | `nora melhorias recusar 3` | só volta com evidência nova (o dobro de ocorrências) ou numa versão nova |
| "adia a melhoria 3" → "sim" | `nora melhorias adiar 3 --dias 7` | volta depois desses dias |
| — | `nora melhorias estado 3 preparacao` | acompanha o desenvolvimento: `preparacao` → `em_teste` → `pronta_para_revisao` → `publicada` |
| — | `nora melhorias fechar-dia` | faz o relatório de hoje agora |

Pela conversa, ela só decide com o número claro e depois do seu "sim". "Não" cancela; mudar de assunto também. **Publicar** pede uma autorização à parte: `nora melhorias estado 3 publicada --autorizo-publicar`. Cada decisão fica registrada com quem, quando e o motivo.

## Ajustes (`config/local.toml`)

```toml
[auto_melhoria]
ativa = true                  # false: não observa nem propõe nada
hora_relatorio = "20:00"
min_ocorrencias = 3
latencia_resposta_ms = 2500   # até o primeiro pedaço da resposta
latencia_ouvido_ms = 1500
latencia_voz_ms = 2000
dias_de_eventos = 30
notificar = true              # notificação do Windows
```

## O que ainda não existe (próximas etapas)

- **P3, pesquisa técnica:** o diagnóstico de hoje é por regras, sem modelo e **sem internet**. A pesquisa em documentação oficial, com fontes citadas e sem mandar nada pessoal, vai ser opcional e desligada por padrão.
- **P4, desenvolvimento supervisionado:** hoje aprovar só gera a especificação. Levar a tarefa ao Codex numa branch isolada e incorporar depois de nova autorização ainda é um passo manual.
- **Painel na HUD (v0.4.0):** "Melhorias da Nora", usando o mesmo banco e os mesmos números.
- **Agendamento com a Nora fechada:** hoje o relatório só sai com a Nora aberta (ou na próxima vez que abrir). O agendador do sistema chega com as rotinas, na v0.6.0.

## Limites

- As regras conhecem os problemas listados acima; um tipo novo de evento cai numa proposta genérica.
- A notificação usa o PowerShell do Windows. Se o seu Windows bloquear notificações, o aviso aparece na próxima conversa.
- A confiança e a prioridade são estimativas pela quantidade e pela gravidade dos eventos, não um teste do problema.
