import type { Estado } from "./state";
export function onda(
  t: number,
  faixa: number,
  tempo: number,
  estado: Estado,
  nivel: number,
): [number, number, number] {
  const atividade =
    estado === "falando"
      ? nivel * 0.36
      : estado === "ouvindo"
        ? nivel * 0.18
        : 0;
  const contracao =
    estado === "pensando" || estado === "transcrevendo"
      ? 0.9
      : estado === "modo_jogo"
        ? 0.95
        : 1;
  const largura = faixa - 0.5;
  const respiracao = estado === "modo_jogo" ? 0 : Math.sin(tempo * 0.5) * 0.035;
  const fase = tempo * 0.12;
  const harmonico =
    Math.cos(t * 4 + fase + largura * 1.5) * (0.31 + atividade) +
    Math.sin(t * 3 - fase * 0.6 + 0.8) * 0.17 +
    Math.cos(t * 5 + largura * 0.7 + 1.5) * 0.09;
  const r = (3.14 + harmonico + largura * 0.88 + respiracao) * contracao;
  return [
    r * Math.cos(t),
    r * Math.sin(t) * 0.97 + Math.sin(t * 3 + largura) * largura * 0.32,
    Math.sin(t * 2 + largura * 2) * 0.25,
  ];
}
/** Gerador determinístico visual, nunca usado como nível de áudio. */
export function aleatorio(indice: number): number {
  const x = Math.sin(indice * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}
