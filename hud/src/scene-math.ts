import type { Estado } from "./state";
import type { Dinamica } from "./scene-audio";
export function onda(
  t: number,
  faixa: number,
  tempo: number,
  estado: Estado,
  nivel: number,
  acustica?: Dinamica,
  saida: [number, number, number] = [0,0,0],
  expressao = 1,
): [number, number, number] {
  const atividade = acustica ? 0 :
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
  let deformacao=0;
  if(acustica && ["ouvindo","fala_detectada","falando"].includes(estado)) {
    const impulso=(acustica.envelope*.48+acustica.rms*.32+acustica.pico*.2)*expressao;
    const grave=(acustica.bandas[0]+acustica.bandas[1])/2, agudo=(acustica.bandas[4]+acustica.bandas[5])/2;
    deformacao=impulso*(acustica.fonte === "voz" ? Math.sin(t*6-tempo*3.8+largura)*.29+Math.cos(t*3)*grave*.18+Math.sin(t*13+tempo*2)*agudo*.08 : Math.sin(t*3+tempo*2.5)*.17+Math.cos(t-.7)*.14+Math.sin(t*10)*agudo*.045);
    deformacao+=largura*impulso*(acustica.fonte === "voz"?.2:.08);
  }
  const r = (3.14 + harmonico + largura * 0.88 + respiracao + deformacao) * contracao;
  saida[0]=r*Math.cos(t);
  saida[1]=r*Math.sin(t)*.97+Math.sin(t*3+largura)*largura*.32;
  saida[2]=Math.sin(t*2+largura*2)*.25;
  return saida;
}
/** Gerador determinístico visual, nunca usado como nível de áudio. */
export function aleatorio(indice: number): number {
  const x = Math.sin(indice * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}
