# Licenças

## Resumo

- **O código da Nora** (tudo o que está neste repositório) é **[MIT](../LICENSE)**: pode usar, modificar, vender e redistribuir, mantendo o aviso de copyright.
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
| kokoro-onnx | MIT | `kokoro` | Voz local Kokoro |
| phonemizer-fork e espeakng-loader (trazem o espeak-ng) | GPL-3.0 | `kokoro`, indiretamente | Fonemas para o Kokoro |
| sqlite-vec | MIT ou Apache-2.0 (à escolha) | `memoria` | Busca vetorial da memória |
| anthropic (SDK oficial do Claude) | Apache-2.0 | `nuvem` | Cérebro na nuvem: o Claude |
| openai (SDK oficial da OpenAI) | Apache-2.0 | `nuvem` | Cérebro na nuvem: o ChatGPT, padrão para as perguntas complexas |
| pytest | MIT | `dev` | Testes |
| ruff | MIT | `dev` | Formatação e lint |

**Sobre o GPL do espeak-ng:** o Kokoro roda num processo separado (`nora servidor-kokoro`), e a Nora só fala com ele por HTTP. O código da Nora não importa nada GPL, por isso continua MIT. Quem redistribuir um pacote com o extra `kokoro` instalado precisa cumprir a GPL-3.0 dessa parte.

## HUD web (`hud/package-lock.json`)

Licenças conferidas nos metadados e arquivos de licença dos pacotes instalados, sem copiar
código de terceiros para o núcleo. O lockfile fixa as versões efetivamente utilizadas.

| Pacote | Versão instalada | Licença | Uso |
|---|---|---|---|
| [three](https://github.com/mrdoob/three.js) | 0.173.0 | MIT | Ondas e partículas WebGL; fallback Canvas próprio |
| [@types/three](https://github.com/DefinitelyTyped/DefinitelyTyped/tree/master/types/three) | 0.173.0 | MIT | Tipos de desenvolvimento |
| [vite](https://github.com/vitejs/vite) | 6.4.5 | MIT | Servidor local de desenvolvimento e build |
| [typescript](https://github.com/microsoft/TypeScript) | 5.9.3 | Apache-2.0 | Verificação de tipos |
| [vitest](https://github.com/vitest-dev/vitest) | 3.2.7 | MIT | Testes automatizados da interface |
| [eslint](https://github.com/eslint/eslint) | 9.39.5 | MIT | Análise estática |
| [typescript-eslint](https://github.com/typescript-eslint/typescript-eslint) | 8.72.1 | MIT | Análise estática TypeScript |

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
| Whisper (pesos, ex.: `ggml-small`) | MIT | Baixado pelo `scripts/instalar_voz_windows.ps1` |
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

## Ao adicionar algo novo

Toda dependência, programa, modelo ou voz nova entra nesta página, com a licença conferida na fonte, no mesmo commit que a adiciona. Um teste (`tests/test_licencas.py`) falha se um pacote do `pyproject.toml` não estiver listado aqui.
