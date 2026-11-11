/**
 * Speech clock measurement (roadmap item 5): deterministic simulation, no browser.
 *
 * Real playback: position P(t) = t. The backend publishes an acoustic sample every 50 ms with the
 * position played at that instant; it reaches the HUD with a network/processing delay of 5 to 45
 * ms and, now and then, there is a "stall" (busy CPU, garbage collection) where no sample arrives
 * for 150 to 450 ms. The HUD draws at 60 FPS. Measured:
 * - sound → word delay: when the word appears on screen minus when it starts in the sound (p50/p95);
 * - dropout: fraction of frames, during speech, with no word at all (the clock said "no sample");
 * - jump: largest jump of the estimated position between consecutive frames (ms) and setbacks.
 */
import { describe, expect, it } from "vitest";
import { RelogioFala } from "../src/word-particles";
import type { Acustica } from "../src/scene-audio";
import type { FalaTemporizada } from "../src/state";
import { aleatorio } from "../src/scene-math";

const DURACAO = 60_000;
const palavras = Array.from({ length: 200 }, (_, i) => ({ texto: `p${i}`, inicio_ms: i * 300, fim_ms: i * 300 + 260, destaque: false }));
const fala: FalaTemporizada = { id: 1, duracao_ms: DURACAO, precisao: "alinhada", palavras };
const amostra = (posicao: number): Acustica => ({ fonte: "voz", rms: .2, pico: .3, envelope: .2, bandas: [0, 0, 0, 0, 0, 0], centroide: 0, fluxo: 0, ativo: true, reproducao_id: 1, posicao_ms: posicao, duracao_ms: DURACAO });

export function medir(idade: number, extrapolacao: number, engasgos = 0.01) {
  const relogio = new RelogioFala(idade, extrapolacao);
  // chegadas: [instante de chegada, posição]
  const chegadas: [number, number][] = [];
  let pausaAte = -1;
  for (let t = 0, k = 0; t < DURACAO; t += 50, k++) {
    if (t > pausaAte && aleatorio(k + 77) < engasgos) pausaAte = t + 150 + aleatorio(k + 91) * 300;
    if (t <= pausaAte) continue;
    chegadas.push([t + 5 + aleatorio(k + 13) * 40, t]);
  }
  chegadas.sort((a, b) => a[0] - b[0]);
  const atrasos: number[] = []; let vazios = 0, quadros = 0, salto = 0, recuos = 0;
  let j = 0, anterior: number | null = null; const vista = new Set<number>();
  for (let t = 0; t < DURACAO; t += 1000 / 60) {
    while (j < chegadas.length && chegadas[j][0] <= t) { relogio.atualizar(amostra(chegadas[j][1]), chegadas[j][0]); j++; }
    const r = relogio.palavra(fala, t);
    quadros++;
    if (!r) { vazios++; anterior = null; continue; }
    if (anterior !== null) { salto = Math.max(salto, r.posicao - anterior); if (r.posicao < anterior - .5) recuos++; }
    anterior = r.posicao;
    const i = palavras.indexOf(r.palavra);
    if (!vista.has(i)) { vista.add(i); atrasos.push(t - r.palavra.inicio_ms); }
  }
  atrasos.sort((a, b) => a - b);
  const q = (p: number) => atrasos[Math.min(atrasos.length - 1, Math.ceil(p * atrasos.length) - 1)];
  // quadros "sem palavra" esperados: os 40 ms entre palavras (260–300) = 13,3% dos quadros
  return { p50: q(.5), p95: q(.95), pior: atrasos[atrasos.length - 1], sumico: vazios / quadros - 40 / 300, salto, recuos, perdidas: palavras.length - vista.size };
}

describe("relógio da fala: medição", () => {
  it("compara a configuração atual (300/250) com as alternativas", () => {
    const linhas: string[] = [];
    for (const [idade, extra] of [[300, 250], [300, 300], [450, 400], [600, 500]] as const) {
      for (const eng of [0, .01, .03]) {
        const m = medir(idade, extra, eng);
        linhas.push(`idade ${idade} / extrapola ${extra} · engasgos ${(eng * 100).toFixed(0)}%: atraso p50 ${m.p50.toFixed(0)} ms, p95 ${m.p95.toFixed(0)} ms, pior ${m.pior.toFixed(0)} ms · sumiço ${(m.sumico * 100).toFixed(2)}% · salto ${m.salto.toFixed(0)} ms · recuos ${m.recuos} · palavras perdidas ${m.perdidas}`);
      }
    }
    console.log(linhas.join("\n"));
    expect(linhas.length).toBe(12);
  });
  it("a configuração escolhida (padrão) cumpre as metas: atraso p95 ≤ 100 ms, sem perder palavras nem recuar", () => {
    const relogio = new RelogioFala();
    for (const eng of [0, .01, .03]) {
      const m = medir(relogio.idadeMaxima, relogio.extrapolacaoMaxima, eng);
      expect(m.p95).toBeLessThanOrEqual(100);
      expect(m.perdidas).toBe(0);
      expect(m.recuos).toBe(0);
      expect(m.sumico).toBeLessThan(.005);
    }
  });
});
