/** Medidas do PCM real: nenhuma onda visual é usada como fonte de áudio. */
export interface Acustica {
  fonte: "microfone" | "voz";
  rms: number;
  pico: number;
  envelope: number;
  bandas: number[];
  centroide: number;
  fluxo: number;
  ativo: boolean;
  reproducao_id: number;
  posicao_ms: number;
  duracao_ms: number;
}
export interface Dinamica {
  fonte: "microfone" | "voz";
  rms: number;
  pico: number;
  envelope: number;
  bandas: number[];
  centroide: number;
  fluxo: number;
}
export const SILENCIO: Dinamica = { fonte: "microfone", rms: 0, pico: 0, envelope: 0, bandas: [0,0,0,0,0,0], centroide: 0, fluxo: 0 };
export const PRAZO_AUDIO_MS = 300;
export const aproximar = (atual: number, alvo: number, delta: number, constante: number) => atual + (alvo-atual)*(1-Math.exp(-Math.max(0,delta)/constante));
export function cadenciaVisual(fps: number, jogo: boolean, reduzido: boolean, oculta: boolean) { return oculta || reduzido ? 0 : jogo ? 8 : fps === 120 ? 120 : fps === 60 ? 60 : 30; }
/** Os dois envelopes permanecem independentes; ouvir não reutiliza a cauda do TTS. */
export class EnvelopeVisual {
  readonly voz: Dinamica = { ...SILENCIO, fonte: "voz", bandas: [0,0,0,0,0,0] };
  readonly microfone: Dinamica = { ...SILENCIO, bandas: [0,0,0,0,0,0] };
  private alvos: Record<Acustica["fonte"], Acustica | null> = {microfone:null,voz:null};
  private recebido = {microfone: -Infinity,voz: -Infinity};
  alimentar(sinal: Acustica | null, agora: number) {
    if (!sinal) { this.silenciar(); return; }
    this.alvos[sinal.fonte] = sinal;
    this.recebido[sinal.fonte] = agora;
  }
  passo(delta: number, agora: number) {
    for (const fonte of ["microfone", "voz"] as const) {
      const valor = fonte === "voz" ? this.voz : this.microfone;
      const sinal = this.alvos[fonte];
      const alvo = sinal?.ativo && Math.max(0, agora-this.recebido[fonte]) <= PRAZO_AUDIO_MS ? sinal : null;
      const mover = (a:number,b:number) => { const n=aproximar(a,b,delta,b>a?45:165); return n<0.0001?0:n; };
      valor.rms=mover(valor.rms,alvo?.rms??0);
      valor.pico=mover(valor.pico,alvo?.pico??0);
      valor.envelope=mover(valor.envelope,alvo?.envelope??0);
      valor.centroide=mover(valor.centroide,alvo?.centroide??0);
      valor.fluxo=mover(valor.fluxo,alvo?.fluxo??0);
      for(let i=0;i<6;i++) valor.bandas[i]=mover(valor.bandas[i],alvo?.bandas[i]??0);
    }
  }
  silenciar() { this.alvos.microfone=null; this.alvos.voz=null; }
}
/** Interpolação contínua elimina quinas nas fronteiras das seis bandas FFT. */
export function energiaBanda(bandas: readonly number[], posicao: number) {
  const p=Math.max(0,Math.min(1,posicao))*5, i=Math.floor(p), f=p-i;
  const suave=f*f*(3-2*f);
  return bandas[i]*(1-suave)+bandas[Math.min(5,i+1)]*suave;
}
export function faixaAcustica(x:number, faixa:number, tempo:number, sinal:Dinamica) {
  const janela=Math.max(0,1-Math.abs(x)/10)**0.6;
  const energia=energiaBanda(sinal.bandas,(x+10)/20);
  const amplitude=(sinal.rms*.27+sinal.envelope*.2+sinal.pico*.06)*(.3+energia*.7);
  // Frequência espacial contínua: energia modula amplitude, nunca salta a fase.
  const portadora=Math.sin(x*(2+sinal.centroide*.8)-tempo*4+faixa*1.4)+Math.sin(x*(4.2+sinal.centroide*3)+tempo*2.5)*sinal.fluxo*.28;
  return portadora*amplitude*janela;
}

/**
 * Onda inferior (faixa de pontos na base da tela): ondulação com o pico no centro que se apaga
 * nas bordas, sempre viva em repouso; a energia do áudio (voz ou microfone) a levanta.
 * `faixa` (0–1) separa os fios da fita, com fase e altura um pouco diferentes.
 */
export function ondaInferior(x: number, faixa: number, tempo: number, sinal: Dinamica) {
  const janela = Math.max(0, 1 - (x / 9.6) ** 2);
  const centro = Math.exp(-(x * x) / 30);
  const fase = faixa * .55;
  const forma = Math.sin(x * .92 - tempo * .8 + fase) * .62 + Math.sin(x * 1.9 + tempo * .5 + 1.3 + fase) * .24;
  const amplitude = .3 + sinal.envelope * .42 + sinal.rms * .26;
  return (faixa - .5) * .06 + forma * amplitude * (.35 + .65 * centro) * janela + faixaAcustica(x, faixa, tempo, sinal);
}
/** Brilho fixo de um ponto da onda inferior conforme a posição: mais claro no centro. */
export function brilhoInferior(x: number) {
  return .25 + .75 * Math.exp(-(x * x) / 18);
}
