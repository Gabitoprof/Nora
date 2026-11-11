import { describe, expect, it } from "vitest";
import paleta from "../../src/nora/paleta.json";
import { cadenciaVisual, faixaAcustica, SILENCIO } from "../src/scene-audio";
import { cores, coresDaEmocao, misturar, PRATA } from "../src/state";

describe("identidade dark compartilhada e cadência", () => {
  it("a HUD mostra as emoções contidas no prata, sem trocar a paleta aprovada", () => {
    for (const grupo of Object.values(paleta.aliases)) expect(grupo in paleta.cores).toBe(true);
    // The single source keeps the approved colors (Second Brain and emotions).
    expect(coresDaEmocao.calma).toBe("#66D4CB"); expect(coresDaEmocao.curiosa).toBe("#DF876A");
    for (const [nome, hex] of Object.entries(cores)) {
      expect(hex).toMatch(/^#[A-F0-9]{6}$/);
      const [r,g,b] = hex.slice(1).match(/../g)!.map(x => parseInt(x,16));
      expect(Math.max(r,g,b)-Math.min(r,g,b)).toBeLessThanOrEqual(45);
      expect(Math.min(r,g,b)).toBeGreaterThanOrEqual(150); // light: silvery glow on the dark background
      expect(hex).toBe(misturar(PRATA, coresDaEmocao[nome], .2));
    }
    // Different emotions stay slightly distinguishable.
    expect(cores.calma).not.toBe(cores.curiosa);
  });
  it("suporta limite120 sem elevar o orçamento de jogo, aba oculta ou movimento reduzido", () => {
    expect(cadenciaVisual(120,false,false,false)).toBe(120);
    expect(cadenciaVisual(120,true,false,false)).toBe(8);
    expect(cadenciaVisual(120,false,true,false)).toBe(0);
    expect(cadenciaVisual(120,false,false,true)).toBe(0);
  });
  it("faixa inferior responde também ao microfone, sem inventar energia no silêncio", () => {
    const mic = {...SILENCIO, rms:.4,pico:.7,envelope:.5,bandas:[.1,.1,.3,.3,.1,.1]};
    expect(faixaAcustica(2,.5,1,mic)).not.toBe(0);
    expect(faixaAcustica(2,.5,1,SILENCIO)).toBe(0);
  });
});

import { brilhoInferior, ondaInferior } from "../src/scene-audio";
describe("onda inferior viva e reativa", () => {
  const amplitude = (sinal: typeof SILENCIO) => { let m = 0; for (let x = -6; x <= 6; x += .1) m = Math.max(m, Math.abs(ondaInferior(x, .5, 2, sinal))); return m; };
  it("em repouso ondula (não é uma linha reta) e some nas bordas", () => {
    expect(amplitude(SILENCIO)).toBeGreaterThan(.1);
    expect(Math.abs(ondaInferior(9.6, .5, 2, SILENCIO))).toBeLessThan(.001);
  });
  it("a voz levanta a onda", () => {
    const voz = { ...SILENCIO, fonte: "voz" as const, rms: .4, envelope: .6, pico: .7, bandas: [.2, .3, .4, .3, .2, .1] };
    expect(amplitude(voz)).toBeGreaterThan(amplitude(SILENCIO) * 1.8);
  });
  it("os pontos do centro são mais claros que os das bordas", () => {
    expect(brilhoInferior(0)).toBeGreaterThan(brilhoInferior(8) * 3);
  });
});

import { Telemetria } from "../src/telemetria";
describe("telemetria da HUD (homologação)", () => {
  it("calcula p50/p95/pior do quadro e o atraso das palavras, só com números", () => {
    const t = new Telemetria();
    for (let i = 0; i < 95; i++) t.quadro(33.3, 4);
    for (let i = 0; i < 5; i++) t.quadro(60, 9);
    t.palavra(20); t.palavra(40); t.palavra(-5);
    const r = t.resumo();
    expect(r.quadros).toBe(100); expect(r.intervalo_p50).toBe(33.3); expect(r.intervalo_pior).toBe(60);
    expect(r.intervalo_p95).toBe(33.3); expect(r.palavras).toBe(3); expect(r.atraso_palavra_p95).toBe(40);
    for (const v of Object.values(r)) expect(typeof v).toBe("number");
    expect(t.linha()).toContain("p95 33.3");
  });
  it("ignora valores absurdos (aba em segundo plano, relógio maluco)", () => {
    const t = new Telemetria(); t.quadro(9000, -1); t.palavra(NaN);
    expect(t.resumo().quadros).toBe(0); expect(t.resumo().palavras).toBe(0);
  });
});
