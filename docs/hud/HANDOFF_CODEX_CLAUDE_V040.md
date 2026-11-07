# Handoff Codex → Claude Code — HUD v0.4.0

## Checkpoint A — base e escopo

- Branch de trabalho: `codex/hud-v040-particles-final`.
- Base remota confirmada: `integracao/v0.4.0`, SHA `1f96bcc98efb598e1bc63e4efcb6c29f050da774`.
- O pipeline ElevenLabs v4 Turbo/alinhamento já pertence à base; preservar suas interfaces,
  primeira reprodução, continuidade e privacidade. Não fazer chamadas pagas para testes.
- Último SHA remoto confirmado antes deste checkpoint: o SHA da base acima.
  Este documento será enviado como primeiro checkpoint; consultar `git ls-remote origin
  refs/heads/codex/hud-v040-particles-final` para confirmar o head atual.
- Não alterar main, Pull_code ou Second Brain, não realizar merge, release ou force push.

## Referências disponíveis

Imagem dark fornecida nesta conversa: coroa assimétrica de filamentos, poeira externa,
marca NORA e palavras materialmente feitas de partículas; painel inferior horizontal.
O vídeo citado no prompt não foi anexado/localizado nesta retomada. Não alegar comparação
quadro a quadro com vídeo externo. Não há fonte Nasalization licenciada no checkout:
usar infraestrutura de máscaras com fallback do sistema, sem baixar/redistribuir fonte.

## Plano e responsabilidade

- A: inventário e baseline (em execução).
- B: pool estável, formação/retenção/dispersão reais dos glifos; marca e cabeçalho.
- C: revisão alinhamento → posição PCM; último trecho, cancelamento e privacidade.
- D: tokens dark compartilhados e faixas reativas; preservar layout, retirar só slogans.
- E: regressões, benchmarks sintéticos comparáveis, capturas/replay, checklist e CI.

Testes de referência estão em execução; nenhum resultado novo é considerado aprovado
antes de sua conclusão. Hardware Windows/AMD e latência real ElevenLabs não estão
acessíveis no cloud. Métricas do usuário (265–985 ms de primeiro áudio, 946–1555 ms de
reprodução e 0 ms entre trechos) são históricas, não medições desta branch.

## Retomada

Ler CLAUDE.md, docs/ANDAMENTO.md e este arquivo; conferir `git status`, log e head remoto.
Manter cada fatia testável, executar verificações proporcionais, commitar e enviar.
Confirmar o SHA via `git ls-remote` após cada push; commits/ZIP locais não bastam.
Não implementar novos recursos se faltar orçamento para validar e preservar o checkpoint.
