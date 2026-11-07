/**
 * Alfabeto geométrico próprio da Nora (maiúsculas, algarismos e pontuação): letras largas, de
 * traço único com cantos arredondados e "A" sem travessão, no espírito das fontes de ficção
 * científica. É desenho original em código, sem arquivo de fonte (nada a licenciar ou baixar).
 *
 * Serve de máscara: as partículas pousam sobre os traços. Coordenadas em unidades da altura
 * da letra (0 = topo, 1 = base); cada glifo tem largura própria.
 */

type Ponto = readonly [number, number];
/** Um traço: pontos ligados em linha, com cantos arredondados; `fechado` liga o último ao primeiro. */
interface Traco { pontos: Ponto[]; fechado?: boolean; raio?: number | number[] }
interface Glifo { largura: number; tracos: Traco[] }

const t = (pontos: Ponto[], raio?: number | number[], fechado = false): Traco => ({ pontos, raio, fechado });
const ponto = (x: number, y: number): Traco => ({ pontos: [[x, y], [x + 0.001, y]] });

const L = 1.06; // largura padrão: letras largas

export const GLIFOS: Record<string, Glifo> = {
  A: { largura: 1.12, tracos: [t([[0, 1], [0.56, 0], [1.12, 1]], 0.12)] },
  B: { largura: L, tracos: [t([[0, 1], [0, 0], [L * 0.86, 0], [L * 0.86, 0.47], [0, 0.47]]), t([[0, 0.47], [L, 0.47], [L, 1], [0, 1]])] },
  C: { largura: L, tracos: [t([[L, 0], [0, 0], [0, 1], [L, 1]], 0.3)] },
  D: { largura: L, tracos: [t([[0, 0], [L, 0], [L, 1], [0, 1]], [0.04, 0.4, 0.4, 0.04], true)] },
  E: { largura: L * 0.92, tracos: [t([[L * 0.92, 0], [0, 0], [0, 1], [L * 0.92, 1]], 0.2), t([[0, 0.5], [L * 0.78, 0.5]])] },
  F: { largura: L * 0.9, tracos: [t([[L * 0.9, 0], [0, 0], [0, 1]], 0.2), t([[0, 0.5], [L * 0.76, 0.5]])] },
  G: { largura: L, tracos: [t([[L, 0], [0, 0], [0, 1], [L, 1], [L, 0.52], [L * 0.52, 0.52]], 0.3)] },
  H: { largura: L, tracos: [t([[0, 0], [0, 1]]), t([[L, 0], [L, 1]]), t([[0, 0.5], [L, 0.5]])] },
  I: { largura: 0.001, tracos: [t([[0, 0], [0, 1]])] },
  J: { largura: L * 0.86, tracos: [t([[L * 0.86, 0], [L * 0.86, 1], [0, 1], [0, 0.66]], 0.26)] },
  K: { largura: L * 0.96, tracos: [t([[0, 0], [0, 1]]), t([[L * 0.96, 0], [0.08, 0.5], [L * 0.96, 1]], 0.08)] },
  L: { largura: L * 0.88, tracos: [t([[0, 0], [0, 1], [L * 0.88, 1]], 0.2)] },
  M: { largura: 1.3, tracos: [t([[0, 1], [0, 0], [0.65, 0.6], [1.3, 0], [1.3, 1]], 0.14)] },
  N: { largura: 1.12, tracos: [t([[0, 1], [0, 0], [1.12, 1], [1.12, 0]], 0.14)] },
  O: { largura: 1.16, tracos: [t([[0, 0], [1.16, 0], [1.16, 1], [0, 1]], 0.36, true)] },
  P: { largura: L, tracos: [t([[0, 1], [0, 0], [L, 0], [L, 0.54], [0, 0.54]], 0.26)] },
  Q: { largura: 1.16, tracos: [t([[0, 0], [1.16, 0], [1.16, 1], [0, 1]], 0.36, true), t([[0.74, 0.72], [1.2, 1.06]])] },
  R: { largura: L, tracos: [t([[0, 1], [0, 0], [L, 0], [L, 0.5], [0, 0.5]], 0.26), t([[L * 0.42, 0.5], [L, 1]])] },
  S: { largura: L, tracos: [t([[L, 0], [0, 0], [0, 0.5], [L, 0.5], [L, 1], [0, 1]], 0.26)] },
  T: { largura: L, tracos: [t([[0, 0], [L, 0]]), t([[L / 2, 0], [L / 2, 1]])] },
  U: { largura: L, tracos: [t([[0, 0], [0, 1], [L, 1], [L, 0]], 0.34)] },
  V: { largura: 1.12, tracos: [t([[0, 0], [0.56, 1], [1.12, 0]], 0.12)] },
  W: { largura: 1.5, tracos: [t([[0, 0], [0.37, 1], [0.75, 0.42], [1.13, 1], [1.5, 0]], 0.1)] },
  X: { largura: L, tracos: [t([[0, 0], [L, 1]]), t([[L, 0], [0, 1]])] },
  Y: { largura: L, tracos: [t([[0, 0], [L / 2, 0.52], [L, 0]], 0.1), t([[L / 2, 0.52], [L / 2, 1]])] },
  Z: { largura: L, tracos: [t([[0, 0], [L, 0], [0, 1], [L, 1]], 0.1)] },
  "0": { largura: 0.96, tracos: [t([[0, 0], [0.96, 0], [0.96, 1], [0, 1]], 0.3, true)] },
  "1": { largura: 0.46, tracos: [t([[0, 0.18], [0.46, 0], [0.46, 1]], 0.08)] },
  "2": { largura: 0.96, tracos: [t([[0, 0], [0.96, 0], [0.96, 0.5], [0, 0.5], [0, 1], [0.96, 1]], 0.22)] },
  "3": { largura: 0.96, tracos: [t([[0, 0], [0.96, 0], [0.96, 1], [0, 1]], 0.26), t([[0.3, 0.5], [0.96, 0.5]])] },
  "4": { largura: 0.96, tracos: [t([[0, 0], [0, 0.62], [0.96, 0.62]], 0.12), t([[0.74, 0.26], [0.74, 1]])] },
  "5": { largura: 0.96, tracos: [t([[0.96, 0], [0, 0], [0, 0.48], [0.96, 0.48], [0.96, 1], [0, 1]], 0.22)] },
  "6": { largura: 0.96, tracos: [t([[0.96, 0], [0, 0], [0, 1], [0.96, 1], [0.96, 0.5], [0, 0.5]], 0.24)] },
  "7": { largura: 0.96, tracos: [t([[0, 0], [0.96, 0], [0.3, 1]], 0.1)] },
  "8": { largura: 0.96, tracos: [t([[0, 0], [0.96, 0], [0.96, 1], [0, 1]], 0.26, true), t([[0, 0.5], [0.96, 0.5]])] },
  "9": { largura: 0.96, tracos: [t([[0.96, 0.5], [0, 0.5], [0, 0], [0.96, 0], [0.96, 1], [0, 1]], 0.24)] },
  ".": { largura: 0.001, tracos: [ponto(0, 1)] },
  ",": { largura: 0.08, tracos: [t([[0.08, 0.92], [0, 1.12]])] },
  ":": { largura: 0.001, tracos: [ponto(0, 0.38), ponto(0, 1)] },
  ";": { largura: 0.08, tracos: [ponto(0.08, 0.38), t([[0.08, 0.92], [0, 1.12]])] },
  "!": { largura: 0.001, tracos: [t([[0, 0], [0, 0.68]]), ponto(0, 1)] },
  "?": { largura: 0.86, tracos: [t([[0, 0], [0.86, 0], [0.86, 0.42], [0.43, 0.42], [0.43, 0.68]], 0.2), ponto(0.43, 1)] },
  "-": { largura: 0.56, tracos: [t([[0, 0.55], [0.56, 0.55]])] },
  "'": { largura: 0.001, tracos: [t([[0, 0], [0, 0.26]])] },
  '"': { largura: 0.22, tracos: [t([[0, 0], [0, 0.26]]), t([[0.22, 0], [0.22, 0.26]])] },
  "/": { largura: 0.66, tracos: [t([[0, 1], [0.66, 0]])] },
};

/** Acentos sobre a letra base (em unidades da altura, acima do topo). */
const ACENTOS: Record<string, (centro: number) => Traco[]> = {
  "́": c => [t([[c - 0.1, -0.16], [c + 0.14, -0.32]])], // agudo
  "̀": c => [t([[c + 0.1, -0.16], [c - 0.14, -0.32]])], // grave
  "̂": c => [t([[c - 0.22, -0.14], [c, -0.32], [c + 0.22, -0.14]], 0.04)], // circunflexo
  "̃": c => [t([[c - 0.26, -0.16], [c - 0.1, -0.3], [c + 0.1, -0.18], [c + 0.26, -0.32]], 0.06)], // til
  "̈": c => [ponto(c - 0.16, -0.22), ponto(c + 0.16, -0.22)], // trema
  "̧": c => [t([[c, 1], [c, 1.12], [c + 0.14, 1.2]], 0.05)], // cedilha
};

export const ESPACO = 0.5;
export const ENTRE_LETRAS = 0.3;

/** Letras que o alfabeto sabe desenhar (depois de tirar os acentos e pôr em maiúsculas). */
export function temGlifos(texto: string): boolean {
  return [...texto.normalize("NFD").toLocaleUpperCase("pt-BR")]
    .every(c => c === " " || c in GLIFOS || c in ACENTOS);
}

interface Peca { glifo: Glifo; acentos: string[] }
function pecas(texto: string): (Peca | null)[] {
  const saida: (Peca | null)[] = [];
  for (const c of texto.normalize("NFD").toLocaleUpperCase("pt-BR")) {
    if (c === " ") saida.push(null);
    else if (c in ACENTOS) { const ultima = saida[saida.length - 1]; if (ultima) ultima.acentos.push(c); }
    else if (c in GLIFOS) saida.push({ glifo: GLIFOS[c], acentos: [] });
  }
  return saida;
}

/** Largura do texto em unidades da altura da letra. */
export function larguraTexto(texto: string): number {
  let x = 0, primeira = true;
  for (const p of pecas(texto)) {
    if (!primeira) x += ENTRE_LETRAS;
    x += p ? p.glifo.largura : ESPACO;
    primeira = false;
  }
  return x;
}

function tracar(ctx: CanvasRenderingContext2D, traco: Traco, ox: number, oy: number, h: number) {
  const pts = traco.pontos.map(([x, y]) => [ox + x * h, oy + y * h] as const);
  // Raio por canto (lista, na ordem dos pontos) ou um só para todos.
  const raioDe = (i: number) => (Array.isArray(traco.raio) ? traco.raio[i % traco.raio.length] : traco.raio ?? 0) * h;
  ctx.beginPath();
  if (traco.fechado) {
    // Começa no meio do primeiro lado para arredondar todos os cantos.
    const [a, b] = [pts[0], pts[1]];
    ctx.moveTo((a[0] + b[0]) / 2, (a[1] + b[1]) / 2);
    for (let i = 1; i <= pts.length; i++) {
      const p = pts[i % pts.length], q = pts[(i + 1) % pts.length];
      ctx.arcTo(p[0], p[1], q[0], q[1], raioDe(i % pts.length));
    }
    ctx.closePath();
  } else {
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length - 1; i++) ctx.arcTo(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], raioDe(i));
    ctx.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1]);
  }
  ctx.stroke();
}

/**
 * Desenha o texto centralizado no retângulo (largura × altura), cabendo nos dois sentidos.
 * `espessura` é a grossura do traço em frações da altura da letra.
 */
export function desenharGeometrico(
  ctx: CanvasRenderingContext2D, texto: string, largura: number, altura: number,
  opcoes: { ocupacao?: number; espessura?: number } = {},
) {
  const espessura = opcoes.espessura ?? 0.13;
  const total = larguraTexto(texto);
  if (total <= 0) return;
  // Altura da letra: cabe em ~62% da altura (espaço para acentos) e na largura disponível.
  const h = Math.min(altura * 0.58, (largura * (opcoes.ocupacao ?? 0.9)) / (total + espessura));
  let x = (largura - total * h) / 2;
  const y = (altura - h) / 2 + h * 0.06;
  ctx.lineWidth = Math.max(1, espessura * h);
  ctx.lineCap = "round"; ctx.lineJoin = "round";
  let primeira = true;
  for (const p of pecas(texto)) {
    if (!primeira) x += ENTRE_LETRAS * h;
    primeira = false;
    if (!p) { x += ESPACO * h; continue; }
    for (const traco of p.glifo.tracos) tracar(ctx, traco, x, y, h);
    for (const acento of p.acentos) for (const traco of ACENTOS[acento](p.glifo.largura / 2)) tracar(ctx, traco, x, y, h);
    x += p.glifo.largura * h;
  }
}
