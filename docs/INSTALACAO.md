# Instalar a Nora no Windows

Este guia é para quem vai **usar** a Nora. Para desenvolver, use o repositório (veja o README).

São duas partes:
1. o **instalador da Nora** (`Nora-<versão>-instalador.exe`), com o programa e a HUD;
2. o **pacote de dependências da Nora**: os programas que ela usa e que não vêm dentro dela, porque são grandes, têm licença própria e se atualizam sozinhos. O instalador oferece instalar esse pacote no fim.

## Antes de começar

- Windows 10 ou 11, 64 bits.
- Internet, para o pacote de dependências: uns **8 GB** de download (o modelo de conversa é a maior parte).
- Para a voz da Nora: uma conta no [ElevenLabs](https://elevenlabs.io) com uma chave de API. As vozes locais (Kokoro e Piper) usam programas GPL e **não** vêm no instalador.
- Placa de vídeo: a Nora foi feita para a AMD RX 9060 XT 16 GB, mas o Ollama usa a placa que tiver, ou o processador, mais devagar.

## 1. Instalar a Nora

1. Rode `Nora-<versão>-instalador.exe`. Não precisa de administrador: ela vai para a sua pasta de usuário.
2. **O Windows vai avisar** "O Windows protegeu o computador", porque o instalador ainda não tem assinatura digital. Clique em **Mais informações** e depois em **Executar assim mesmo**. Se o antivírus perguntar, permita: programas novos sem assinatura costumam ser examinados na primeira vez.
3. Deixe marcada a opção **"Instalar agora o pacote de dependências"** e clique em Instalar.

## 2. O pacote de dependências (automático)

Ele abre uma janela do PowerShell e instala, em ordem:

| Etapa | O que instala | Tamanho |
|---|---|---|
| 1 | Visual C++ Redistributable (x64), se faltar | ~25 MB |
| 2 | **Ollama** (cérebro local), pelo `winget` | ~1 GB |
| 3 | Modelos do Ollama: `qwen3.5:9b` (conversa) e `bge-m3` (memória) | ~7 GB |
| 4 | **whisper.cpp** (ouvido), do site oficial | ~10 MB |
| 5 | Modelo do Whisper (`small`) | ~470 MB |

No fim aparece um **resumo**, com `ok` ou `FALHOU` em cada etapa. O registro completo fica em `%APPDATA%\Nora\instalacao\`.

- **Pode rodar de novo** quantas vezes precisar (menu Iniciar > Nora > **Instalar dependências da Nora**): o que já estiver pronto é pulado.
- **"O winget não está neste Windows":** instale o **Instalador de Aplicativo** (App Installer) pela Microsoft Store e rode de novo.
- **Ouvido mais preciso** (fala rápida ou pouco clara): rode o pacote com outro modelo, num PowerShell aberto na pasta da Nora (`%LOCALAPPDATA%\Programs\Nora`):

  ```powershell
  powershell -ExecutionPolicy Bypass -File instalar_dependencias.ps1 -ModeloWhisper large-v3-turbo-q5_0
  ```

## 3. Configurar (uma vez)

Abra **menu Iniciar > Nora > Pasta da Nora (config e memória)**. É a pasta `%APPDATA%\Nora`, onde fica tudo o que é seu:

| Arquivo ou pasta | O que é |
|---|---|
| `.env` | Suas chaves. Ponha `ELEVENLABS_API_KEY=` e, se quiser a nuvem para as perguntas difíceis, `OPENAI_API_KEY=` e/ou `ANTHROPIC_API_KEY=` |
| `config\local.toml` | Sua config: seu nome e o `voz_id` da voz do ElevenLabs (Voices > ... > Copy voice ID) |
| `data\` | Memória, histórico e relatórios. Nunca sai do seu PC |
| `models\`, `ferramentas\` | Modelos e programas baixados pelo pacote de dependências |

Abra os dois arquivos no Bloco de Notas: eles já vêm com comentários explicando cada linha.

## 4. Usar

- **Menu Iniciar > Nora:** liga o Ollama e o ouvido se ainda não estiverem rodando, abre a HUD no navegador e começa a escuta contínua. Diga "Nora, ..." e fale.
- **Menu Iniciar > Nora > Nora - verificar instalação:** mostra a versão, o commit e se cada parte (Ollama, ouvido, voz, chaves) está ok. Use isso primeiro se algo não funcionar.

## Desinstalar

Configurações > Aplicativos > **Nora** > Desinstalar. A pasta `%APPDATA%\Nora` (config, chaves e memória) **fica**, para você não perder nada. Para apagar tudo, apague essa pasta também. O Ollama e os modelos dele se desinstalam pelo próprio Ollama.

## Gerar o instalador (para quem desenvolve)

A cada push na `main`, na `integracao/...` ou numa tag `v*`, o GitHub gera o instalador e o `.zip`: **Actions > Empacotar > a execução > Artifacts > nora-windows** (ficam 14 dias). Para gerar no seu PC: `scripts\empacotar_windows.ps1`, com as instruções no começo do arquivo.
