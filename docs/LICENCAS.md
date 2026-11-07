# Licenças

## Resumo

- **O código da Nora** é de **todos os direitos reservados** ([LICENSE](../LICENSE)): público para consulta, sem permissão de uso, cópia ou redistribuição sem autorização. As versões até a `v0.3.0` saíram em MIT e continuam em MIT.
- **Os programas, modelos e vozes que a Nora usa não estão no repositório** e têm licença própria. Eles são instalados ou baixados à parte (pelo `pip`, pelos scripts de `scripts/` ou pela própria ferramenta) e a Nora conversa com eles pela rede local ou como processo separado. **Ao baixar cada um, você aceita a licença dele.**
- **O que é seu nunca entra no repositório:** memória e histórico (`data/`), chaves (`.env`), config pessoal (`config/local.toml`), fluxos do ComfyUI (`config/voz_comfyui.json`) e modelos e vozes (`models/`).

> Conferido em 31/10/2026, na página ou no arquivo de licença de cada projeto. Licenças mudam: antes de redistribuir qualquer coisa, confira a versão atual na fonte.

## Dependências Python (`pyproject.toml`)

| Pacote | Licença | Extra | Para quê |
|---|---|---|---|
| sounddevice (usa PortAudio, MIT) | MIT | `voz` | Microfone e alto-falante |
| numpy | BSD-3-Clause (e partes MIT, 0BSD, Zlib, CC0) | `voz` | Áudio (reamostragem, medidas) |
| onnxruntime | MIT | `voz` | Rodar o Silero VAD |
| soundfile (usa libsndfile, LGPL-2.1, como biblioteca dinâmica) | BSD-3-Clause | `voz` | Ler FLAC, MP3 e WAV |
| pycaw | MIT | `voz` (Windows) | Abaixar o som dos outros programas |
| websockets | BSD-3-Clause | `voz` | ElevenLabs v4 (diálogo em tempo real) |
| kokoro-onnx | MIT | `kokoro` | Voz local Kokoro |
| phonemizer-fork e espeakng-loader (trazem o espeak-ng) | GPL-3.0 | `kokoro`, indiretamente | Fonemas para o Kokoro |
| sqlite-vec | MIT ou Apache-2.0 (à escolha) | `memoria` | Busca vetorial da memória |
| anthropic (SDK oficial do Claude) | Apache-2.0 | `nuvem` | Cérebro na nuvem: o Claude |
| openai (SDK oficial da OpenAI) | Apache-2.0 | `nuvem` | Cérebro na nuvem: o ChatGPT, padrão para as perguntas complexas |
| pytest | MIT | `dev` | Testes |
| ruff | MIT | `dev` | Formatação e lint |
| pyinstaller | GPL-2.0-or-later com exceção para o bootloader (permite distribuir programas não livres gerados com ele) | `empacotar` | Gerar o `nora.exe`; só no build, não vai como biblioteca dentro do programa |

**Dentro do `nora.exe`:** o Python (PSF-2.0) e os pacotes dos extras `voz`, `memoria` e `nuvem` com as dependências deles. O build copia o aviso de licença de cada um para a pasta `licencas` do programa (`empacotamento/juntar_licencas.py`). A libsndfile (LGPL-2.1, do `soundfile`) e a PortAudio (MIT, do `sounddevice`) vão como bibliotecas separadas (DLL) na pasta do programa. O Kokoro, o Piper e o espeak-ng **não** vão no `.exe`.

**Ferramenta do instalador:** [Inno Setup](https://jrsoftware.org/isinfo.php) 6, com licença própria ([license.txt](https://github.com/jrsoftware/issrc/blob/main/license.txt)): permite o uso "for any purpose, including commercial applications", mantidos os avisos de copyright. Usado só para gerar o instalador.

**Programas que o pacote de dependências instala** (cada um com a licença dele, aceita na instalação): Ollama (MIT), whisper.cpp (MIT), modelos do Whisper (MIT), `qwen3.5:9b` e `bge-m3` (tabela abaixo) e o Visual C++ Redistributable (licença da Microsoft).

**Sobre o GPL do espeak-ng:** o Kokoro (que usa o espeak-ng, GPL-3.0) roda num processo separado (`nora servidor-kokoro`) e é instalado à parte, pelo extra `kokoro`. Distribuir a Nora junto com ele exige cumprir a GPL-3.0.

## HUD web (`hud/package-lock.json`)

Licenças conferidas nos metadados e arquivos de licença dos pacotes instalados, sem copiar
código de terceiros para o núcleo. O lockfile fixa as versões efetivamente utilizadas.

| Pacote | Versão instalada | Licença | Uso |
|---|---|---|---|
| [three](https://github.com/mrdoob/three.js) | 0.173.0 | MIT | Ondas e partículas WebGL; fallback Canvas próprio |
| [@types/three](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/three) | 0.173.0 | MIT | Tipos de desenvolvimento |
| [vite](https://github.com/vitejs/vite) | 6.4.5 | MIT | Servidor local de desenvolvimento e build |
| [typescript](https://github.com/microsoft/TypeScript) | 5.9.3 | Apache-2.0 | Verificação de tipos |
| [vitest](https://github.com/vitest-dev/vitest) | 5.1.0 | MIT | Testes automatizados da interface |
| [eslint](https://github.com/eslint/eslint) | 10.14.0 | MIT | Análise estática |
| [typescript-eslint](https://github.com/typescript-eslint/typescript-eslint) | 8.72.1 | MIT | Análise estática TypeScript |
| [@types/node](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/node) | 22.20.5 | MIT | Tipos Node para testes das ferramentas |
| [minimatch](https://github.com/isaacs/minimatch) | 11.0.4 | BlueOak-1.0.0 | Dependência transitiva de lint/parser, com override de versões vulneráveis |

O override de minimatch aplica-se somente ao intervalo vulnerável `>=7.0.0 <11.0.1`.
ESLint e typescript-eslint ainda declaravam versões nesse intervalo; a versão 11 mantém
as APIs efetivamente usadas por esses consumidores (função nomeada e `Minimatch.match`).
Testes específicos de glob/dotfiles/negação/extensões, além do lint do projeto, verificam
a compatibilidade; não se afirma equivalência de toda a API entre versões maiores.
BlueOak-1.0.0 é permissiva; a licença foi lida no pacote instalado. O arquivo de licença
acompanha a instalação da dependência fixada pelo lockfile, sem incorporar código ao núcleo Python.

O desenho procedural segue o PNG de referência fornecido pelo proprietário. Nenhum modelo,
fonte remota, imagem de terceiros ou serviço externo é necessário para renderizar a HUD.
A ponte SSE usa a biblioteca padrão do Python e não acrescenta dependência Python.

## Programas separados

| Programa | Licença | Como a Nora usa |
|---|---|---|
| [Ollama](https://github.com/ollama/ollama) | MIT | Cérebro local e embeddings, pela API local |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT | Ouvido (`whisper-server`), pela API local |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper1-gpl`) | GPL-3.0 | Voz local (servidor HTTP separado) e treino de voz (só no Google Colab) |
| [ComfyUI](https://github.com/comfyanonymous/ComfyUI) | GPL-3.0 | Opcional: criar voz, pela API local |

Nenhum deles é copiado para o repositório.

## Modelos e vozes

| Modelo ou voz | Licença | Observação |
|---|---|---|
| Silero VAD | MIT | Baixado do pacote oficial `silero-vad` |
| Whisper (pesos, ex.: `ggml-small`, `ggml-large-v3-turbo-q5_0`) | MIT | Baixado pelo `scripts/instalar_voz_windows.ps1` (o modelo escolhido em `-ModeloWhisper`) |
| Qwen 3.5 (`qwen3.5:9b`, pelo Ollama) | Licença do próprio modelo | Confira em [ollama.com/library/qwen3.5](https://ollama.com/library/qwen3.5) |
| bge-m3 (embeddings da memória) | MIT | Baixado pelo Ollama |
| Kokoro-82M (pesos) | Apache-2.0 | Baixado à parte em `models/kokoro` |
| Vozes prontas do Piper (ex.: `pt_BR-faber-medium`) e checkpoints de treino (`rhasspy/piper-checkpoints`, ex.: `cadu`) | Uma licença por voz (veja o `MODEL_CARD` de cada uma) | Muitas derivam da voz `lessac`, que é **só para uso não comercial**. Use para fins pessoais, ou escolha uma voz com licença aberta |
| Qwen3-TTS (no ComfyUI) | Apache-2.0 | Opcional, para criar voz |

## Serviços na nuvem (opcionais)

| Serviço | Termos | Observação |
|---|---|---|
| API da OpenAI (ChatGPT) | Termos de uso da OpenAI | Exige chave própria (`OPENAI_API_KEY` no `.env`) e é cobrada por uso. Padrão do roteador para as perguntas complexas; o que vai para a API é a conversa daquela pergunta, com a persona e as notas da memória |
| API da Anthropic (Claude) | Termos comerciais da Anthropic | Exige chave própria (`ANTHROPIC_API_KEY` no `.env`) e é cobrada por uso. Usada pelo roteador (v0.3.0) nas perguntas difíceis, no modo nuvem e no modo jogo; o que vai para a API é a conversa daquela pergunta, com a persona e as notas da memória |
| ElevenLabs | Termos de uso da ElevenLabs | Exige conta e chave própria (`.env`). **Não use o áudio gerado para treinar outra voz**: os termos não permitem |

## Voz treinada por você

Uma voz treinada com `nora voz gerar-dataset` e `scripts/treinar_piper_colab.ipynb` herda as condições de tudo o que entrou nela:

- **o modelo que gerou o áudio** (ex.: Qwen3-TTS, Apache-2.0; o F5-TTS pt-BR, que é CC-BY-NC-4.0, só permitiria uso não comercial);
- **a voz base do Piper** usada no ajuste fino (muitas são só para uso não comercial);
- **a pessoa da voz:** só use voz criada do zero ou de alguém que **autorizou**. Não imite atores, personagens nem pessoas reais.

Na dúvida, mantenha a voz treinada **para uso pessoal** e fora do Git (`models/`, já no `.gitignore`).

## Nome e marca

O projeto não usa nomes, logos nem referências visuais de personagens ou marcas registradas (por exemplo, "Jarvis" ou Marvel). O nome do assistente vem da config.

## Fontes

- **Marca NORA na HUD:** alfabeto geométrico próprio, desenhado em código (`hud/src/geometric-glyphs.ts`). Não é uma fonte de terceiros; nada a licenciar.
- **Nasalization (Typodermic Fonts):** a HUD usa **só se estiver instalada no computador** de quem usa (detecção pela largura medida no navegador). O arquivo da fonte **não** vai no repositório, no build da HUD nem no `nora.exe`. O arquivo da fonte (versão 5.000) traz copyright da Typodermic Fonts, "Nasalization" como marca registrada deles e permissão de embutir só para "pré-visualização e impressão" (fsType 4): **não pode ser embutida** no repositório, no build da HUD nem no `nora.exe`. Uso pessoal, instalada no próprio Windows, funciona.

## Ao adicionar algo novo

Toda dependência, programa, modelo ou voz nova entra nesta página, com a licença conferida na fonte, no mesmo commit que a adiciona. Um teste (`tests/test_licencas.py`) falha se um pacote do `pyproject.toml` não estiver listado aqui.
