# HUD da Nora · v0.4.0 em desenvolvimento

Interface local de apresentação do mesmo núcleo Python. A referência oficial é o PNG
aprovado na tarefa: preto e prata, coroa orgânica vazada de filamentos, rios diagonais de
partículas, iluminação contida, arcos de calibração e painéis laterais discretos. A cena é
procedural e animada; não há um segundo cérebro, microfone ou TTS no navegador.

## Preparar e iniciar

Requisitos: Python do projeto e Node.js LTS 22.13+ ou 24 com npm. Na raiz do repositório:

```powershell
cd hud
npm ci
npm run build
cd ..
nora ouvir --hud
```

Abra `http://127.0.0.1:8765` no navegador. O núcleo continua cuidando da escuta mãos livres,
transcrição, memória, modo jogo e fala. Fechar a página não encerra esses módulos.
`nora hud` inicia apenas o servidor da interface; nesse modo ela informa que o núcleo está
desconectado, em vez de inventar dados de áudio ou modelo. Serviços de voz e Ollama são
configurados conforme [o guia de voz](../docs/VOZ.md).

Para desenvolver a interface, mantenha o servidor local da Nora em execução e, em outro
terminal:

```powershell
cd hud
npm run dev
```

O Vite atende somente em `127.0.0.1:5173`. O proxy `/api` aponta para `127.0.0.1:8765`;
normaliza Host/Origin apenas para requisições locais de mesma origem. Produção serve o build
pelo próprio servidor Python, na mesma origem. Não publicar portas na rede.

## Estado, privacidade e supervisão

- O contrato JSON autoritativo é [`src/nora/hud_contrato.json`](../src/nora/hud_contrato.json),
  importado pelo TypeScript. SSE `/api/eventos` transporta eventos versionados; snapshots
  reinicializam a sequência após reconexão. Eventos atrasados ou malformados são ignorados.
- Estados e níveis de áudio vêm exclusivamente do pipeline Python. Na ausência de dados,
  o nível fica neutro. As ondas de repouso representam a presença visual, não um sinal medido.
- Texto e notas ficam ocultos por padrão. O botão **Privado** solicita o consentimento ao
  servidor; ocultar limpa imediatamente o conteúdo local. Sem `localStorage`, `sessionStorage`
  ou cache de conversa. O navegador não pede permissão de microfone e não faz uploads.
- Propostas usam o serviço de domínio já existente, por POST com token de sessão e confirmação.
  Aprovar apenas gera tarefa; não muda código, não publica e não faz merge.
- Notas exibem somente os resultados usados pelo núcleo na pasta explicitamente autorizada.
- Texto é inserido com `textContent`; nenhuma resposta ou nota é interpretada como HTML.

## Visual, acessibilidade e desempenho

A coroa e as partículas usam Three.js/WebGL com opção econômica e fallback Canvas. O menu
**Ajustes da interface** oferece qualidade e limite de 30/60 FPS. DPR é limitado a 1,5; modo
jogo reduz a cadência a 8 FPS. A cena respeita `prefers-reduced-motion` e evita desenhar frames
com a página oculta. A paleta emocional é majoritariamente monocromática, com acentos
prata/dourado/rosa/turquesa/terracota/azul/lavanda conforme os eventos reais.

**Palavras em partículas** são opcionais, visíveis só com consentimento e no estado falando.
Sem timestamps fonéticos do TTS, a legenda identifica explicitamente uma estimativa visual;
não há promessa de sincronismo exato. O efeito desliga com movimento reduzido ou privacidade.

Layout inclui ultrawide, 16:9 e telas móveis. Controles têm nome acessível, foco visível,
confirmadores de decisão e opção de tela cheia. Nenhuma fonte, imagem ou CDN externa é
requisitada pelo runtime. Medição com Ollama/GPU AMD e estética final no hardware real
continuam no [checklist cumulativo](../docs/HOMOLOGACAO.md).

## Verificar

```powershell
npm run lint
npm run typecheck
npm test
npm run build
```

Os testes cobrem contrato Python/TypeScript, eventos fora de ordem/reinício, amplitude real,
privacidade com SSE chegando antes da resposta HTTP e renovação de token sem repetir ações
em falhas ambíguas. Testes visuais usam dados explicitamente de teste, nunca status fictício
no runtime. CI deve passar em Windows e Ubuntu antes de o PR ser considerado pronto.

A v0.4.0 não é uma release publicada. A homologação integrada Windows/AMD depende do aceite
do proprietário; P3/P4, MCP completo e operação distribuída permanecem fora deste escopo.

No Windows, não executar o script Bash da nuvem. Para corrigir caminhos Linux no PowerShell
ou um ambiente criado com Python 3.15, usar o [procedimento Windows](../docs/HUD.md#powershell-não-executa-o-script-da-nuvem-linux).

Se abrir por link retornar `Origem local obrigatória`, atualizar a branch e reiniciar
o servidor Python: a correção distingue navegação pública inicial de acesso às APIs.
Ver [diagnóstico de navegação](../docs/HUD.md#hud-retorna-origem-local-obrigatória-ao-abrir-por-link).
