# Treinar uma voz própria (ComfyUI → Piper)

A ideia: usar o **ComfyUI para criar** a voz (pesado, lento, mas com a qualidade que você escolheu) e o **Piper para falar** no dia a dia (leve, roda no processador, responde em menos de meio segundo e não disputa a GPU com o cérebro).

```
ComfyUI (sua voz)  ──►  500 a 1.000 frases faladas  ──►  treino do Piper (Colab, grátis)  ──►  voz leve na Nora
   nora voz gerar-dataset                                    arquivo .onnx              motor = "piper"
```

## 0. Antes de começar: licença e direitos

- **Confira a licença do modelo de voz usado no ComfyUI** (na página do modelo): ela precisa permitir usar o áudio gerado para treinar outro modelo. Modelos só para uso não comercial limitam o uso da voz final do mesmo jeito.
- A voz tem que ser **criada** (design de voz) ou de alguém que **autorizou**. Não use áudio do ElevenLabs para treinar: os termos deles não permitem.

## 1. Deixar a voz pronta no ComfyUI

Siga [VOZ.md](VOZ.md#usar-uma-voz-feita-no-comfyui): fluxo exportado em formato API como `config/voz_comfyui.json`, com `{{texto}}` (ou `[voz.comfyui] campo`), e `[voz] motor = "comfyui"` no `config/local.toml`. Teste com `nora voz salvar "teste" --ouvir`.

**Dica:** fixe a semente (`seed`) no nó de voz. Com semente fixa, todas as frases saem com a mesma voz; com semente aleatória, a voz pode variar de uma frase para outra, e o treino aprende uma voz "média".

## 2. Gerar o conjunto de treino

```powershell
nora voz gerar-dataset --nome minha_voz
```

- Usa a lista de frases do projeto (`recursos/frases_pt.txt`, ~120 frases variadas).
- Para chegar a **500 a 1.000 frases**, use também um texto de **domínio público** (ex.: um livro de Machado de Assis do portal Domínio Público), que a Nora corta em frases sozinha:

  ```powershell
  nora voz gerar-dataset --nome minha_voz --texto "C:\Users\Gabriel Moura\Downloads\livro.txt" --limite 800
  ```

- Usa **só a voz principal** (nunca a reserva), para não misturar vozes no conjunto.
- **Pode interromper** (Ctrl+C, ou o ComfyUI fechou): rodando de novo, ela continua de onde parou.
- Resultado em `data\dataset_voz\minha_voz\`: a pasta `wavs\` (0001.wav, 0002.wav... mono, 16 bits, 22.050 Hz) e o `metadata.csv` (`0001|texto da frase`), o formato que o treino do Piper usa.

Quanto tempo leva: o ComfyUI gasta alguns segundos por frase; 800 frases podem levar algumas horas. Deixe rodando e feche outros programas pesados (a GPU fica toda para o ComfyUI; o Ollama nem precisa estar aberto nesta etapa).

## 3. Conferir o conjunto (10 minutos que valem a pena)

Ouça umas 20 frases salteadas. Apague o **wav e a linha correspondente do `metadata.csv`** das que saíram com erro (palavra trocada, ruído, voz diferente, corte no fim). Áudio ruim no treino vira voz ruim depois.

## 4. Treinar no Google Colab (grátis)

O treino precisa de GPU NVIDIA; o Colab empresta uma de graça por algumas horas por dia.

1. Compacte a pasta `data\dataset_voz\minha_voz` em `.zip` e envie para o seu Google Drive.
2. Abra um notebook de treino do Piper no Colab, com a GPU ligada (Ambiente de execução → Alterar tipo → GPU).
3. Em vez de treinar do zero, faça o **ajuste fino** a partir de uma voz pronta do Piper (muito mais rápido, e funciona bem com algumas centenas de frases). Escolha uma voz base com **licença aberta**; bases derivadas da `lessac` herdam uso só não comercial.
4. Treine até a voz soar natural (algumas horas; o Colab grátis pode desconectar, então salve os checkpoints no Drive).
5. Exporte para `.onnx` e baixe os dois arquivos: `minha_voz.onnx` e `minha_voz.onnx.json`.

> Os comandos exatos do treino mudam entre versões do Piper. Quando você chegar nesta etapa, peça ao Claude para montar o notebook conferido com a versão atual.

## 5. Usar na Nora

1. Copie `minha_voz.onnx` e `minha_voz.onnx.json` para `B:\Nora\models\piper\`.
2. No `config\local.toml`:

   ```toml
   [voz]
   motor = "piper"
   reserva = "kokoro"

   [voz.piper]
   voz = "minha_voz"
   ```

3. Inicie com `scripts\iniciar_voz_windows.ps1 -Voz piper -VozPiper minha_voz` e teste: `nora voz salvar "Oi, Gabriel! Esta é a minha voz." --ouvir`.

Pronto: a mesma voz que você criou no ComfyUI, agora rápida, local e sem custo.
