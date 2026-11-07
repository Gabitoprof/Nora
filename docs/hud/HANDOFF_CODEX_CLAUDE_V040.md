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
Vídeo posteriormente anexado e visto: 30,785 s, 576×288, 30 FPS. Referência de movimento
(poeira → formação de glifos → retenção → dispersão); não copiar cores ou conteúdo do vídeo. Não há fonte Nasalization licenciada no checkout:
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

## Checkpoint B — partículas e UI

- Primeiro checkpoint remoto confirmado: `e2d7395233306912978f525f55cdca5ee8dbd937`.
- Motor reutilizável de partículas com IDs/pool estáveis, posição/velocidade e mola amortecida.
  A máscara fornece destinos; o canvas desenha corpos móveis, não uma imagem estática.
- Marca central usa o motor com fallback Arial do sistema (Nasalization ausente).
  Somente heading acessível permanece em HTML. Slogans/ornamentos retirados; funções preservadas.
- Cabeçalho usa relógio de mídia, modo reduzido mostra alternativa estática autorizada.
- Paleta compartilhada `src/nora/paleta.json`: aliases preservados, tons dark frios contidos.
  Faixa inferior responde mic/voz; limite 120 FPS adicionado sem elevar jogo (8 FPS).
- Frontend: lint/typecheck/47 testes/build aprovados. Biblioteca Three separada em chunk
  estável, sem aumentar limite de avisos. Baseline Python:465 aprovados/2 ignorados;
  um dos ignorados era o módulo v4 por websockets ausente. Dependência já declarada
  está sendo instalada para validação final; CI passa a instalá-la explicitamente.
- Próximo checkpoint C: regressões reproduzidas de alinhamento/padding, fragmentos,
  metadados finais e fim natural vs cancelamento; benchmark achou overhead na base
  ainda em correção. Não declarar meta p95≤5% até medir o resultado.

## Retomada Claude Code — 07/11/2026

### Auditoria (antes de editar)

- `integracao/v0.4.0`: local e remoto em `1f96bcc` (sem commits do Codex nela).
- Trabalho do Codex: branch `codex/hud-v040-particles-final`, `b5cbe44` (2 commits sobre `1f96bcc`:
  `e2d7395` handoff, `b5cbe44` partículas). O autor Git registrado é outra identidade; a autoria
  do Codex vem deste documento, não do Git.
- CI de `b5cbe44`: vermelho nos 7 jobs. Causas reproduzidas: a paleta das emoções
  (`src/nora/paleta.json`) foi trocada por tons quase brancos (quebra `test_paleta`,
  `test_segundo_cerebro` e a instalação limpa) e um teste da HUD comparava `undefined`.
- Checkpoint C do Codex (alinhamento/último fragmento) não foi feito; o front consumia
  `reproducao_encerrada`, mas o backend nunca enviava e o contrato não listava.
- Referências: imagem dark aprovada (anexada na conversa) e vídeo de 30,8 s (576×288) vistos.
  Não estão no repositório. Nenhuma fonte Nasalization licenciada disponível.

### Branch e commits da retomada

Branch `refino/hud-v040`, criada a partir de `codex/hud-v040-particles-final`. Sem merge em
`integracao/v0.4.0`, `main`, `Pull_code` ou Second Brain.

| Commit | Lote | O que mudou |
|---|---|---|
| `4588d1c` | 1 | Paleta aprovada restaurada; a HUD mistura cada emoção em 20% num prata-ciano (`state.ts`: `PRATA`, `misturar`, `cores`). CI verde nos 7 jobs. |
| `53c29dd` | 2 | Marca NORA no alfabeto geométrico próprio (`geometric-glyphs.ts`): desenho original em código, sem arquivo de fonte; amostragem da máscara sem listras; partículas maiores com halo. |
| `a9ac07b` | 3 | Faixa da fala: palavra atual grande; até 3 já ditas menores e apagadas à esquerda, na mesma nuvem (nunca as próximas); segura 320 ms entre palavras para não piscar. |
| `c39dc44` | 4 | Evento `reproducao_encerrada` no contrato e no backend (id, posição, duração, interrompida; sem texto): fim natural mantém a última palavra, barge-in apaga. |
| (este) | 5 | Handoff, evidências, `scripts/hud_cenario.py`. |

### Estado por requisito

| Requisito | Estado | Onde |
|---|---|---|
| Visual dark, prata com ciano contido | Feito | `state.ts` (`cores`), paleta aprovada preservada |
| NORA feita de partículas reais, estilo geométrico tipo Nasalization | Feito (desenho próprio, não é a Nasalization) | `geometric-glyphs.ts`, `text-particle-field.ts`, `main.ts` |
| Palavras da fala formam, seguram e dispersam pelo tempo do áudio | Feito | `word-particles.ts` (relógio do PCM), `text-particle-field.ts` |
| Linha da fala com contexto, sem adiantar palavras | Feito | `word-particles.ts` (`ANTERIORES`, `SEGURAR_MS`) |
| Fim natural vs barge-in | Feito | `hud.py` (`reproducao`, `_encerrada_valida`), `audio.py` |
| Privacidade (sem texto sem permissão; revogar apaga) | Mantido do Codex, testado | `word-particles.ts`, `hud.py` |
| Movimento reduzido | Mantido do Codex, testado | `word-particles.ts`, `scene-audio.ts` |
| Onda inferior e anel reagindo ao áudio real | Base existente; não alterado nesta retomada | `scene-audio.ts`, `scene.ts` |
| Comparação visual com a GPU real (Windows, RX 9060 XT) | Pendente (manual) | — |

### QA e métricas

- `ruff format --check`, `ruff check`, `pytest`: 486 aprovados, 2 ignorados.
- HUD: `npm run lint`, `typecheck`, `test` (65), `build`: aprovados.
- Instalação limpa (`scripts/testar_instalacao_limpa.py`): aprovada.
- Início da reprodução com a ponte da HUD ligada (método: `_tocar_partes` com saída falsa a 8×
  tempo real, PCM chegando em pedaços de 200 ms, 60 amostras por série, Linux da nuvem):
  base `1f96bcc` p50 11,2 ms / p95 21,1 ms; `c39dc44` p50 11,1 ms / p95 21,3 ms (+0,9%, dentro do
  ruído; meta ≤ 5%). Não substitui a medida com o ElevenLabs real no Windows.
- Atraso áudio→visual e correlação envelope→onda: **não medidos** (o Chromium sem GPU da nuvem
  leva 2 a 12 s por captura durante a fala; não dá para medir quadro a quadro aqui).

### Evidências

- `docs/hud/evidencias/hud-repouso-marca-particulas.jpg`: HUD real (servidor + build) em repouso.
- `docs/hud/evidencias/alfabeto-geometrico.jpg`: alfabeto geométrico formado por partículas.
- `docs/hud/evidencias/faixa-da-fala.jpg`: linha da fala (palavra atual + anteriores).
- Capturas da HUD inteira durante a fala: pendentes (limitação do navegador sem GPU acima).

### Como retomar

1. `git fetch origin refino/hud-v040 && git switch refino/hud-v040`.
2. `cd hud && npm ci && npm run build`, depois `python scripts/hud_cenario.py` e abrir o endereço;
   digitar `falar` para ver a marca, a linha da fala e a onda com uma fala sintética alinhada.
3. Validação: `ruff format --check . && ruff check . && pytest`; em `hud/`:
   `npm run lint && npm run typecheck && npm test && npm run build`.

### Pendências (ordem sugerida)

- [ ] Homologação visual no Windows com a RX 9060 XT: marca, linha da fala com o ElevenLabs v4
      real, onda inferior, FPS; comparar com a imagem aprovada.
- [ ] Medir no Windows o início da reprodução com e sem a HUD (p50/p95) e o atraso áudio→palavra.
- [x] Nasalization: a marca usa a fonte **se estiver instalada no Windows** (`fontesInstaladas` em
      `main.ts`); sem ela, o alfabeto próprio. O arquivo (Typodermic, fsType 4 "pré-visualização e
      impressão") não pode ser embutido. Testado na nuvem com a fonte instalada fora do repositório:
      `docs/hud/evidencias/hud-repouso-nasalization-instalada.jpg`.
- [x] Linha da fala: decisão do Gabriel (07/11) — só as palavras já ditas, nunca as próximas.
- [x] Merge autorizado pelo Gabriel (07/11): `refino/hud-v040` avançou `integracao/v0.4.0` até
      `f89d89d` (fast-forward, sem commit de merge).

### Homologação do Gabriel (06/11, noite) e ajustes

- Primeira abertura no Windows mostrou a HUD antiga (build `3eeba77`): uma Nora antiga ocupava
  a porta. Depois de encerrar os processos e refazer o build, carregou `93f870f`.
- Achados no Windows: a marca formada ficava **parada** e não interagia com a poeira; a opção
  "Palavras em partículas" apareceu desmarcada (estado de formulário restaurado pelo navegador).
- Correção: `Vida` em `text-particle-field.ts` (tremor, fluxo para a poeira e volta, poeira livre
  em volta) e energia do áudio (`QuadroVisual.energia`, o mesmo sinal do anel) aumentando
  movimento e brilho; palavras com tremor leve; `autocomplete="off"` na opção das palavras.
  Movimento reduzido continua parado. Vídeo: `docs/hud/evidencias/marca-viva.mp4`
  (0–4 s repouso, 4–8 s com voz simulada).
