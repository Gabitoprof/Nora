import { describe, expect, it } from "vitest";
import { desenharGeometrico, GLIFOS, larguraTexto, temGlifos } from "../src/geometric-glyphs";
import { amostrarMascara } from "../src/text-particle-field";

/** Contexto 2D falso que guarda os pontos de cada traço desenhado. */
function contextoFalso() {
  const tracos: number[][][] = [];
  let atual: number[][] = [];
  const ctx = {
    lineWidth: 0, lineCap: "", lineJoin: "",
    beginPath() { atual = []; },
    moveTo(x: number, y: number) { atual.push([x, y]); },
    lineTo(x: number, y: number) { atual.push([x, y]); },
    arcTo(x1: number, y1: number, x2: number, y2: number) { atual.push([x1, y1], [x2, y2]); },
    closePath() {},
    stroke() { tracos.push(atual); },
  };
  return { ctx: ctx as unknown as CanvasRenderingContext2D, tracos, estado: ctx };
}

describe("alfabeto geométrico próprio (marca)", () => {
  it("cobre maiúsculas, algarismos, pontuação comum e acentos do português", () => {
    for (const c of "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?!:-") expect(c in GLIFOS).toBe(true);
    expect(temGlifos("Nora")).toBe(true);
    expect(temGlifos("ÍRIS, OLÁ! AÇÃO")).toBe(true);
    expect(temGlifos("NORA ✦")).toBe(false); // símbolo desconhecido: cai na fonte do sistema
  });
  it("A da marca não tem travessão: um único traço em V invertido", () => {
    expect(GLIFOS.A.tracos).toHaveLength(1);
    const [esq, topo, dir] = GLIFOS.A.tracos[0].pontos;
    expect(topo[1]).toBe(0); expect(esq[1]).toBe(1); expect(dir[1]).toBe(1);
  });
  it("desenha cada letra dentro do retângulo, centralizada e sem passar das bordas", () => {
    const { ctx, tracos, estado } = contextoFalso();
    desenharGeometrico(ctx, "NORA", 960, 180, { espessura: 0.12 });
    // N (1 traço), O (1), R (2), A (1)
    expect(tracos).toHaveLength(5);
    const pontos = tracos.flat();
    const xs = pontos.map(p => p[0]), ys = pontos.map(p => p[1]);
    expect(Math.min(...xs)).toBeGreaterThan(0); expect(Math.max(...xs)).toBeLessThan(960);
    expect(Math.min(...ys)).toBeGreaterThan(0); expect(Math.max(...ys)).toBeLessThan(180);
    // centralizado na horizontal (tolerância de meio traço)
    expect(Math.abs((Math.min(...xs) + Math.max(...xs)) / 2 - 480)).toBeLessThan(estado.lineWidth);
    expect(estado.lineCap).toBe("round");
  });
  it("acentos e cedilha viram traços extras da mesma letra; espaço só avança", () => {
    const comAcento = contextoFalso(), sem = contextoFalso();
    desenharGeometrico(comAcento.ctx, "AÇÃO", 960, 180);
    desenharGeometrico(sem.ctx, "ACAO", 960, 180);
    expect(comAcento.tracos.length).toBe(sem.tracos.length + 2);
    expect(larguraTexto("NO RA")).toBeGreaterThan(larguraTexto("NORA"));
    expect(larguraTexto("nora")).toBe(larguraTexto("NORA"));
  });
  it("texto longo encolhe para caber; nunca desenha fora", () => {
    const { ctx, tracos } = contextoFalso();
    desenharGeometrico(ctx, "ASSISTENTE PESSOAL DA CASA", 960, 180);
    const xs = tracos.flat().map(p => p[0]);
    expect(Math.min(...xs)).toBeGreaterThan(0); expect(Math.max(...xs)).toBeLessThan(960);
  });
});

describe("amostragem da máscara: as partículas pousam sobre a letra", () => {
  const w = 200, h = 60;
  const mascara = () => {
    const px = new Uint8ClampedArray(w * h * 4);
    // duas barras: x 20–40 e x 120–180, y 10–50
    for (let y = 10; y < 50; y++) for (let x = 0; x < w; x++)
      if ((x >= 20 && x < 40) || (x >= 120 && x < 180)) px[(y * w + x) * 4 + 3] = 255;
    return px;
  };
  it("todo destino fica dentro da forma (com o pequeno deslocamento) e respeita o limite", () => {
    const alvos = amostrarMascara(mascara(), w, h, 300);
    expect(alvos.length).toBe(600);
    for (let i = 0; i < alvos.length; i += 2) {
      const [x, y] = [alvos[i], alvos[i + 1]];
      expect(y).toBeGreaterThanOrEqual(9); expect(y).toBeLessThanOrEqual(51);
      expect((x >= 19 && x <= 41) || (x >= 119 && x <= 181)).toBe(true);
    }
  });
  it("espalha por toda a forma (as duas barras e várias linhas), sem listras", () => {
    const alvos = amostrarMascara(mascara(), w, h, 300);
    let esquerda = 0; const linhas = new Set<number>();
    for (let i = 0; i < alvos.length; i += 2) { if (alvos[i] < 60) esquerda++; linhas.add(Math.round(alvos[i + 1] / 4)); }
    // a barra da esquerda tem 1/4 da área: recebe por volta de 1/4 dos pontos
    expect(esquerda / 300).toBeGreaterThan(0.18); expect(esquerda / 300).toBeLessThan(0.32);
    expect(linhas.size).toBeGreaterThanOrEqual(10);
  });
  it("é determinística e não inventa pontos sem máscara", () => {
    expect(amostrarMascara(mascara(), w, h, 120)).toEqual(amostrarMascara(mascara(), w, h, 120));
    expect(amostrarMascara(new Uint8ClampedArray(w * h * 4), w, h, 100)).toHaveLength(0);
  });
});

import { escolherFonteInstalada, fonteInstalada } from "../src/text-particle-field";
describe("Nasalization só quando instalada no computador",()=>{
  // Contexto falso: a "fonte instalada" muda a largura medida; as outras caem na genérica.
  const contexto=(instaladas:string[])=>{
    const ctx={font:"",measureText(t:string){const instalada=instaladas.some(n=>this.font.includes(`"${n}"`));return {width:t.length*(instalada?71:60)};}};
    return ctx as unknown as CanvasRenderingContext2D;
  };
  it("detecta pela largura medida, sem baixar fonte",()=>{
    expect(fonteInstalada(contexto(["Nasalization"]),"Nasalization")).toBe(true);
    expect(fonteInstalada(contexto([]),"Nasalization")).toBe(false);
  });
  it("escolhe a primeira instalada; sem nenhuma, volta ao alfabeto próprio",()=>{
    expect(escolherFonteInstalada(contexto(["Nasalization Rg"]),["Nasalization","Nasalization Rg"])).toBe("Nasalization Rg");
    expect(escolherFonteInstalada(contexto([]),["Nasalization","Nasalization Rg"])).toBe("");
  });
});
