# HUD da Nora v0.4.0 — em desenvolvimento

A HUD representa a mesma Nora que conversa pelo terminal: nenhum segundo microfone,
modelo, histórico ou sintetizador de voz. O núcleo Python é a fonte dos estados e níveis.
O navegador só apresenta os dados recebidos e encaminha decisões supervisionadas.

## Referência visual oficial

A referência é o PNG fornecido pelo proprietário nesta tarefa: fundo preto, coroa central
orgânica de ondas prateadas com centro aberto, contornos fluidos sobrepostos, rios diagonais
de partículas, iluminação pontual contida, arcos de calibração e molduras finas. O desenho
é procedural e animável; não usa um orbe genérico ou outra identidade visual.

O PNG está disponível na conversa, sem arquivo local de referência persistido no checkout.
A comparação visual é qualitativa; não há alegação de igualdade pixel a pixel. Capturas de
QA usam dados sintéticos somente no harness de teste, nunca como estado real da aplicação.

A base é monocromática. Emoções alteram suavemente movimento e acentos: prata neutra
`#C9C9C9`, ouro `#F0C66A`, rosa `#E3A4BD`, turquesa `#66D4CB`, terracota `#DF876A`, azul
`#80A8F6` e lavanda `#AA9ACF`. Movimento reduzido, densidade e taxa de quadros limitam custo.
A medição com Ollama/STT/TTS e GPU AMD reais pertence à homologação integrada.

## Preparar no Windows

Usar o checkout existente; não é preciso worktree ou outro clone. Requisitos: Python
3.11–3.13, Node.js 22 ou superior compatível com Vite, e os serviços de voz já configurados.
Na raiz do repositório, em PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,voz,memoria]"
cd hud
npm ci
npm run lint
npm run typecheck
npm test
npm run build
cd ..
nora --verificar
```

O extra `nuvem` continua opcional para ChatGPT/Claude, assim como suas credenciais. Não
colocar segredos no frontend, no Git ou no comando. Instalação de Ollama, Whisper e TTS
continua descrita em [VOZ](VOZ.md), sem reconfigurar o PC automaticamente.

## PowerShell não executa o script da nuvem Linux

`/workspace/Nora`, `.venv/bin/python`, `#!/usr/bin/env bash` e `set -euo pipefail`
pertencem ao ambiente Linux do Codex. Não copiar o `install_script` da nuvem para o
PowerShell. No Windows usar o caminho real do checkout e `Scripts\python.exe`.

Se `python3` estiver apontando para Python 3.15, não reutilizar esse ambiente para voz.
Listar versões com `py -0p`; usar Python 3.13 (ou 3.11/3.12 suportado) explicitamente.
O exemplo abaixo é para o checkout `B:\Nora`, com um novo ambiente fora dele, preservando
qualquer `.venv` anterior e todos os dados/configurações:

```powershell
Set-Location 'B:\Nora' -ErrorAction Stop
py -0p
# Executar as linhas seguintes quando Python 3.13 estiver listado:
py -3.13 -m venv 'B:\Nora-venv313'
& 'B:\Nora-venv313\Scripts\python.exe' -m pip install -e ".[dev,voz,memoria]"
& 'B:\Nora-venv313\Scripts\python.exe' -m pip check
& 'B:\Nora-venv313\Scripts\nora.exe' --verificar
```

Não é preciso ativar o ambiente ou alterar a política de execução do PowerShell. Se 3.13
não estiver instalado, instalar essa versão primeiro, por exemplo com
`winget install --exact --id Python.Python.3.13`, e confirmar com `py -0p` em novo terminal.
Avisos de um `.pth` antigo para `B:\ELLA\src` indicam uma instalação editável anterior;
o ambiente separado não herda os pacotes da instalação global por padrão.

## Executar

Com os serviços existentes de voz e modelo disponíveis:

```powershell
nora ouvir --hud --hud-porta 8765
```

Abrir no navegador local `http://127.0.0.1:8765` e usar tela cheia. O microfone continua
sendo o de `nora ouvir`; a HUD não solicita permissão de microfone ao navegador. Os comandos
falados de modelo/voz/modo jogo continuam sendo interpretados e confirmados pelo núcleo.

Para inspecionar só o visual/servidor, sem iniciar escuta:

```powershell
nora hud --porta 8765
```

Esse modo deve permanecer identificado como desconectado da conversa, sem inventar
modelo ativo, amplitude de voz ou transcrição. Para desenvolver o frontend:

```powershell
cd hud
npm run dev
```

Vite encaminha `/api` ao servidor Python local na porta 8765. Para o uso integrado,
preferir a build servida pelo próprio Python, que mantém interface e API na mesma origem.

## Contrato e privacidade

- Contrato autoritativo: `src/nora/hud_contrato.json`; frontend TypeScript consome o mesmo
  contrato. Versão, sequência e payload são validados; mensagens inválidas não comandam a Nora.
  Envelope limitado a 64 KiB UTF-8, texto a 6000 caracteres, até 8 assinantes SSE.
- SSE `GET /api/eventos`: eventos `{versao, sequencia, tipo, dados, instante}`. Conexão/
  reconexão começa com snapshot autoritativo; não depende de replay de mensagens pessoais.
- `GET /api/estado`: snapshot do estado atual. `nivel_audio` é medida do pipeline, não
  gravação; não transmite WAV ou PCM. Quando não há dados, o nível é neutro.
- `GET /api/sessao`: token local de sessão para requisições de mudança. Não é credencial
  de provedor; não vai para URL, storage persistente ou logs.
- `POST /api/privacidade` com `{visivel: true|false}`: opt-in explícito para conteúdo pessoal.
  O padrão é oculto; desligar limpa o conteúdo exibido. Não guardar conversas no navegador.
- `GET /api/propostas` e `POST /api/decisao` com `{id, acao, confirmar:true}`: usa
  `Melhorias.decidir`, com confirmação na interface e validação no servidor. Aprovar gera
  tarefa; não modifica código, não publica e não implementa P3/P4.
- `GET /api/notas`: somente notas realmente utilizadas pelo núcleo, de pasta autorizada.
  Não varre o disco, não abre caminhos arbitrários e não expõe conteúdo sem consentimento.
- `GET /api/relatorio`: disponibilidade/metadados do relatório, sem perguntas pessoais.
- Mutações exigem `X-Nora-Token`; Host/Origin e destino são locais. Sem CORS público,
  sem bind em `0.0.0.0`, sem acesso remoto implícito. Não publicar a porta na rede.

A ponte é opcional, com filas e tamanhos limitados, amostragem de níveis e descarte para
clientes lentos. Um cliente que desconecta não deve interromper a conversa. O snapshot
permite recuperar o estado após perda de eventos. Falhas da HUD não devem parar a voz.

## Fala, emoção e conteúdo

Estados diferenciam repouso, escuta, transcrição, pensamento, fala, jogo e erro. Eventos de
fala devem acompanhar o início/fim de reprodução, não apenas a síntese. A amplitude vem do
mesmo áudio usado pela Nora. Emoções vêm das etiquetas já usadas pelo motor de voz.

Texto progressivo e notas exigem consentimento. Palavras em partículas são desativáveis.
Sem alinhamento temporal do TTS, o efeito é uma **estimativa visual**, não sincronismo
fonético. O frontend não revela pensamento privado, perguntas pessoais ou chaves.

## Qualidade e homologação

```powershell
ruff format --check .
ruff check .
pytest
nora --verificar
cd hud
npm run lint
npm run typecheck
npm test
npm run build
```

A CI inclui o núcleo em Windows/Ubuntu com Python 3.11/3.13 e o frontend em Windows/Ubuntu
com Node 22. Localmente passaram 295 testes Python (1 ignorado por falta de Kokoro real),
15 testes TypeScript, Ruff, lint, typecheck e build. Os resultados desta entrega são registrados no [checklist cumulativo](HOMOLOGACAO.md).
Não chamar a v0.4.0 de lançada ou homologada apenas porque a CI passou.

Pendente no computador real: silêncio prolongado e digitação durante escuta, alertas e
relatórios com auto-melhoria ativa, transições em modo jogo sem reativar Ollama, saída de
voz real e reserva, latência, fullscreen/ultrawide, uso de CPU/GPU com os modelos carregados.
A versão permanece em desenvolvimento, sem merge automático, tags ou release.
