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

- Usa a lista de frases do projeto (`recursos/frases_pt.txt`, 154 frases variadas).
- Para chegar a **500 a 1.000 frases**, use também um texto de **domínio público** (ex.: um livro de Machado de Assis do portal Domínio Público), que a Nora corta em frases sozinha:

  ```powershell
  nora voz gerar-dataset --nome minha_voz --texto "C:\caminho\para\livro.txt" --limite 800
  ```

- Usa **só a voz principal** (nunca a reserva), para não misturar vozes no conjunto.
- **Pode interromper** (Ctrl+C, ou o ComfyUI fechou): rodando de novo, ela continua de onde parou.
- Resultado em `data\dataset_voz\minha_voz\`: a pasta `wavs\` (0001.wav, 0002.wav... mono, 16 bits, 22.050 Hz) e o `metadata.csv` (`0001|texto da frase`), o formato que o treino do Piper usa.

Quanto tempo leva: o ComfyUI gasta alguns segundos por frase; 800 frases podem levar algumas horas. Deixe rodando e feche outros programas pesados (a GPU fica toda para o ComfyUI; o Ollama nem precisa estar aberto nesta etapa).

## 3. Conferir o conjunto (10 minutos que valem a pena)

Ouça umas 20 frases salteadas. Apague o **wav e a linha correspondente do `metadata.csv`** das que saíram com erro (palavra trocada, ruído, voz diferente, corte no fim). Áudio ruim no treino vira voz ruim depois.

## 4. Treinar no Google Colab (grátis)

O treino precisa de GPU NVIDIA; o Colab empresta uma de graça por algumas horas por dia. O notebook pronto está em [`scripts/treinar_piper_colab.ipynb`](../scripts/treinar_piper_colab.ipynb) e usa o Piper atual ([piper1-gpl](https://github.com/OHF-Voice/piper1-gpl), GPL-3.0, baixado dentro do Colab, nunca no repositório).

1. Compacte a pasta `data\dataset_voz\minha_voz` (com `wavs\` e `metadata.csv`) em `minha_voz.zip` e envie para o Google Drive, numa pasta `Nora` (`Meu Drive/Nora/minha_voz.zip`).
2. Abra o [Google Colab](https://colab.research.google.com), vá em **Arquivo → Fazer upload de notebook** e escolha `scripts\treinar_piper_colab.ipynb`.
3. **Ambiente de execução → Alterar o tipo de ambiente de execução → GPU (T4)**.
4. Na célula 1, ponha em `NOME_VOZ` o nome do conjunto (`minha_voz`). Rode as células em ordem.

O que o notebook faz:

- Confere o conjunto (áudios em 22.050 Hz, frases sem áudio) e estima o tempo de treino.
- Parte de uma voz pt-BR "medium" pronta do Piper (`rhasspy/piper-checkpoints`) e faz o **ajuste fino** com as suas frases, por 2.000 épocas (a receita do Piper para menos de 5 h de fala).
- A cada 15 minutos copia o último ponto do treino para `Meu Drive/Nora/treino_minha_voz/`. **Se o Colab desconectar**, abra de novo e rode as células outra vez: ele continua de onde parou.
- Na célula 7 exporta para `.onnx` e toca uma frase de teste. Dá para ouvir no meio do treino: pare a célula 6, rode a 7 e depois a 6 de novo.
- Na célula 8 salva no Drive os dois arquivos da voz: `pt_BR-minhavoz-medium.onnx` e `pt_BR-minhavoz-medium.onnx.json` (o nome perde o "_", porque o Piper usa "_" e "-" para separar idioma, nome e qualidade).

Quanto tempo: com ~10 minutos de fala (as 154 frases da lista), umas 6 a 8 horas na T4, normalmente em duas ou três sessões do Colab grátis. Mais frases deixam a voz melhor, mas cada época fica mais lenta.

**Licença:** as vozes base do Piper costumam derivar de dados só para uso não comercial; a voz treinada é para uso pessoal e fica fora do Git (`models/`).

## 5. Usar na Nora

1. Copie `pt_BR-minhavoz-medium.onnx` e `pt_BR-minhavoz-medium.onnx.json` para `B:\Nora\models\piper\`.
2. No `config\local.toml`:

   ```toml
   [voz]
   motor = "piper"
   reserva = "kokoro"

   [voz.piper]
   voz = "pt_BR-minhavoz-medium"
   ```

3. Inicie com `scripts\iniciar_voz_windows.ps1 -Voz piper -VozPiper pt_BR-minhavoz-medium` e teste: `nora voz salvar "Oi! Esta é a minha voz." --ouvir`.

Pronto: a mesma voz que você criou no ComfyUI, agora rápida, local e sem custo.
