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
3.11–3.13, Node.js LTS 22.13+ ou 24, conforme `hud/package.json`, e os serviços de voz já configurados.
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
& 'B:\Nora-venv313\Scripts\python.exe' -m nora --verificar
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
fala devem acompanhar o início/fim de reprodução, não apenas a síntese. Os dados acústicos vêm do
mesmo PCM captado/reproduzido pela Nora. Emoções vêm das etiquetas já usadas pelo motor de voz.

Texto progressivo, notas e palavras em partículas exigem consentimento. O efeito de palavras
é desativável. A sequência usa o relógio da reprodução e os intervalos da frase; mudanças
de estado não avançam palavras. Sem alinhamento temporal fornecido pelo TTS, os intervalos
são uma **estimativa fundamentada na duração do áudio**, identificada internamente como
`estimada`; não é sincronismo fonético. O frontend não revela pensamento privado, perguntas
pessoais ou chaves.

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

## Executável de entrada bloqueado pelo Windows

Se a instalação concluir e `pip check` disser `No broken requirements found`, mas o
Controle de Aplicativos bloquear `nora.exe`, isso não indica falha nas dependências.
A entrada oficial `python -m nora` usa o mesmo `nora.cli.main` do launcher instalado.
O diagnóstico da aplicação continua sendo `--verificar`. Não desativar políticas de
segurança; se a política também impedir a execução pelo Python, solicitar a análise e
liberação da aplicação ao responsável pela política do computador.

## HUD retorna `Origem local obrigatória` ao abrir por link

A abertura inicial pelo navegador envia `Sec-Fetch-Site: cross-site` ou `same-site` quando
vem de um link de outra página. Uma versão anterior da ponte rejeitava também essa navegação
legítima, embora o build estivesse correto. A correção autoriza somente `GET /` e
`GET /index.html` com modo `navigate` e destino `document`, mantendo Host/Origin validados.
APIs, requisições externas de dados, iframe e mutações continuam protegidos; não remover
as verificações de origem ou token para abrir a interface.

Parar o servidor antigo com Ctrl+C, atualizar a branch `feat/v0.4.0-hud`, reinstalar o
lockfile com `npm.cmd ci`, compilar e reiniciar o Python. O processo antigo mantém em memória
as regras anteriores até ser reiniciado. O build exibido como concluído no terminal já é
uma evidência de compilação aprovada; o erro HTTP de origem é registrado separadamente.

Os alertas de auditoria das ferramentas de desenvolvimento também foram corrigidos por
atualizações explícitas e testadas. Não é necessário executar `npm audit fix --force`.
O aviso local de scripts de instalação requer análise somente se uma instalação ou build
falhar; a captura fornecida confirma build concluído, sem necessidade de liberar scripts
adicionais para corrigir o HTTP 403.


## Retomada acústica e emocional — 06/11/2026

A coroa central preserva o centro aberto e os contornos orgânicos da referência. RMS,
picos, envelope, distribuição espectral em seis bandas, centroide e fluxo derivados do
PCM controlam a dinâmica; a geometria continua sendo interpretação artística, não um
osciloscópio. Escuta e reprodução usam comportamentos distintos. A faixa inferior é
complementar e reage somente à voz da Nora. Em repouso permanece a respiração discreta.

A análise reutiliza o pipeline único de áudio. O navegador recebe somente medidas e
metadados temporais, nunca áudio bruto, credenciais ou uma nova captura. Filas limitadas,
descarte de dados atrasados e frequência de atualização limitada protegem o pipeline de
voz; desconectar a HUD não deve interrompê-lo. Movimento reduzido, página oculta, modo
jogo e qualidade Canvas continuam disponíveis.

O painel lateral "Sinal de áudio" mostra o mesmo sinal que move a onda central (a medida da fonte em uso: microfone enquanto escuta, voz enquanto fala), em escala de decibéis (−60 dBFS = 0%, 0 dBFS = 100%). Com sinal, nunca mostra "0%"; pensando ou em repouso, mostra "Em silêncio".

A paleta fica num arquivo só, `hud/paleta.json`, lido pela HUD (`state.ts`) e pelo Python (`nora.paleta.cor("curiosa")`), para o Second Brain usar as mesmas cores sem copiá-las. A paleta canônica mantém prata neutra, dourado para alegria/entusiasmo, rosa para carinho,
turquesa para calma, azul para seriedade, lavanda para tristeza e terracota para curiosidade.
Os nomes de emoção são os do núcleo existente; não há outro classificador. As marcações
amarela, roxa e rosa da referência não fazem parte da interface.

As evidências atuais, seus tipos de simulação e limitações estão em
[QA acústica](evidencias/hud-acustica/README.md). Resultados históricos acima continuam
restritos aos commits indicados. O checklist cumulativo preserva a instalação, o
`pip check`, o diagnóstico e a abertura/conexão no Windows informados pelo proprietário.
Essas evidências não homologam a nova reatividade acústica, a voz física ou o consumo na
GPU AMD; esses cenários permanecem na homologação integrada.
