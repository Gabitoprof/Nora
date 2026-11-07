import { describe, expect, it } from "vitest";
import paleta from "../../src/nora/paleta.json";
import { cadenciaVisual, faixaAcustica, SILENCIO } from "../src/scene-audio";

describe("identidade dark compartilhada e cadência", () => {
  it("mantém aliases e dinâmica centralizados, com cores frias contidas", () => {
    for (const grupo of Object.values(paleta.aliases)) expect(grupo in paleta.cores).toBe(true);
    for (const hex of Object.values(paleta.cores)) {
      expect(hex).toMatch(/^#[A-Fa-f0-9]{6}$/);
      const [r,g,b] = hex.slice(1).match(/../g)!.map(x => parseInt(x,16));
      expect(Math.max(r,g,b)-Math.min(r,g,b)).toBeLessThanOrEqual(45);
      expect(b).toBeGreaterThanOrEqual(r);
    }
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
