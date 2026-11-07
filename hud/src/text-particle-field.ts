import { aleatorio } from "./scene-math";
import { desenharGeometrico, temGlifos } from "./geometric-glyphs";

export type FaseParticulas = "poeira" | "formando" | "retendo" | "dispersando";
/** Pool fixo: identidade, posição e velocidade sobrevivem às trocas de palavra. */
export class NuvemLetras {
  readonly ids: Uint16Array;
  readonly x: Float32Array;
  readonly y: Float32Array;
  readonly vx: Float32Array;
  readonly vy: Float32Array;
  readonly alpha: Float32Array;
  readonly tamanho: Float32Array;
  readonly alvoX: Float32Array;
  readonly alvoY: Float32Array;
  private readonly livreX: Float32Array;
  private readonly livreY: Float32Array;
  private readonly brilho: Float32Array;
  quantidade = 0;
  alvos = 0;
  fase: FaseParticulas = "poeira";
  private inicio = 0;
  constructor(readonly maximo = 1800, readonly largura = 1200, readonly altura = 140) {
    this.ids = new Uint16Array(maximo);
    this.x = new Float32Array(maximo); this.y = new Float32Array(maximo);
    this.vx = new Float32Array(maximo); this.vy = new Float32Array(maximo);
    this.alpha = new Float32Array(maximo); this.tamanho = new Float32Array(maximo);
    this.alvoX = new Float32Array(maximo); this.alvoY = new Float32Array(maximo);
    this.livreX = new Float32Array(maximo); this.livreY = new Float32Array(maximo);
    this.brilho = new Float32Array(maximo);
    for (let i = 0; i < maximo; i++) {
      this.ids[i] = i;
      this.x[i] = this.livreX[i] = largura * (.04 + aleatorio(i + 8101) * .92);
      this.y[i] = this.livreY[i] = altura * (.09 + aleatorio(i + 1244) * .82);
      this.brilho[i] = .58 + aleatorio(i + 3341) * .37;
      this.tamanho[i] = .68 + aleatorio(i + 9981) * .52;
    }
  }
  definirAlvos(coordenadas: ArrayLike<number>, agora: number, imediato = false) {
    this.alvos = Math.min(this.maximo, Math.floor(coordenadas.length / 2));
    this.quantidade = Math.min(this.maximo, Math.max(this.quantidade, this.alvos + 36));
    this.inicio = agora;
    this.fase = imediato ? "retendo" : "formando";
    for (let i = 0; i < this.quantidade; i++) {
      if (i < this.alvos) {
        this.alvoX[i] = coordenadas[i * 2]; this.alvoY[i] = coordenadas[i * 2 + 1];
        // Partículas apagadas voltam como poeira, jamais nascem já sobre o glifo.
        if (this.alpha[i] < .01) { this.x[i] = this.livreX[i]; this.y[i] = this.livreY[i]; this.alpha[i] = .1; }
        if (imediato) { this.x[i] = this.alvoX[i]; this.y[i] = this.alvoY[i]; this.vx[i] = this.vy[i] = 0; this.alpha[i] = this.brilho[i]; }
      }
    }
  }
  dispersar(agora: number) {
    if (this.fase === "poeira" || this.fase === "dispersando") return;
    this.fase = "dispersando"; this.inicio = agora;
  }
  limpar() {
    this.fase = "poeira"; this.quantidade = this.alvos = 0;
    this.alpha.fill(0); this.vx.fill(0); this.vy.fill(0);
    this.x.set(this.livreX); this.y.set(this.livreY);
    // Apagar também a máscara geométrica evita reter texto privado no pool.
    this.alvoX.fill(0); this.alvoY.fill(0);
  }
  passo(agora: number, delta: number, reduzido = false) {
    if (this.fase === "poeira") return;
    if (this.fase === "formando" && agora - this.inicio >= 130) this.fase = "retendo";
    const retendo = this.fase === "retendo" || this.fase === "formando";
    const dt = Math.max(0, Math.min(100, delta)) / 1000;
    const omega = retendo ? 48 : 4.2;
    const amortecimento = Math.exp(-omega * dt);
    const fade = Math.exp(-dt / (retendo ? .075 : .135));
    for (let i = 0; i < this.quantidade; i++) {
      const glifo = retendo && i < this.alvos;
      const tx = glifo ? this.alvoX[i] : this.livreX[i];
      const ty = glifo ? this.alvoY[i] : this.livreY[i];
      if (reduzido) {
        this.x[i] = tx; this.y[i] = ty; this.vx[i] = this.vy[i] = 0;
        this.alpha[i] = glifo ? this.brilho[i] : 0; continue;
      }
      // Solução analítica da mola criticamente amortecida, estável em 30/60/120 FPS.
      const dx = this.x[i] - tx, dy = this.y[i] - ty;
      const bx = this.vx[i] + omega * dx, by = this.vy[i] + omega * dy;
      this.x[i] = tx + (dx + bx * dt) * amortecimento;
      this.y[i] = ty + (dy + by * dt) * amortecimento;
      this.vx[i] = (this.vx[i] - omega * bx * dt) * amortecimento;
      this.vy[i] = (this.vy[i] - omega * by * dt) * amortecimento;
      const alvoAlpha = glifo ? this.brilho[i] : retendo ? .025 : 0;
      this.alpha[i] = alvoAlpha + (this.alpha[i] - alvoAlpha) * fade;
    }
    if (!retendo && agora - this.inicio > 700) this.limpar();
  }
}

export interface OpcoesCampoTexto {
  largura?: number;
  altura?: number;
  maximo?: number;
  fonte?: string;
  tamanhoFonte?: number;
  /** "geometrico": alfabeto próprio da Nora (marca); "fonte": a fonte do sistema. */
  estilo?: "geometrico" | "fonte";
  /** Grossura do traço do alfabeto geométrico, em frações da altura da letra. */
  espessura?: number;
  /** Halo suave em volta de cada partícula (brilho da poeira). */
  brilho?: number;
  /** Multiplica o tamanho das partículas (canvas que a tela reduz precisa de pontos maiores). */
  escalaParticula?: number;
}
/** Canvas desenha os corpos da simulação; a máscara só define seus destinos. Sem RAF próprio. */
export class CampoParticulasTexto {
  readonly nuvem: NuvemLetras;
  private contexto: CanvasRenderingContext2D | null;
  private mascara: HTMLCanvasElement;
  private fonte: string;
  private tamanhoFonte: number;
  private texto = "";
  private estilo: "geometrico" | "fonte";
  private espessura: number;
  private halo: number;
  private escala: number;
  constructor(private canvas: HTMLCanvasElement, opcoes: OpcoesCampoTexto = {}) {
    canvas.width = opcoes.largura ?? 1200; canvas.height = opcoes.altura ?? 140;
    this.nuvem = new NuvemLetras(opcoes.maximo ?? 1800, canvas.width, canvas.height);
    this.contexto = canvas.getContext("2d");
    this.mascara = document.createElement("canvas");
    this.mascara.width = canvas.width; this.mascara.height = canvas.height;
    this.fonte = opcoes.fonte ?? "'Segoe UI', Arial, sans-serif";
    this.tamanhoFonte = opcoes.tamanhoFonte ?? 84;
    this.estilo = opcoes.estilo ?? "fonte";
    this.espessura = opcoes.espessura ?? 0.13;
    this.halo = opcoes.brilho ?? 0;
    this.escala = opcoes.escalaParticula ?? 1;
  }
  definirTexto(texto: string, agora: number, imediato = false) {
    if (texto === this.texto && this.nuvem.fase !== "poeira" && this.nuvem.fase !== "dispersando") return;
    this.texto = texto;
    const m = this.mascara.getContext("2d", { willReadFrequently: true });
    if (!m || !texto.trim()) { this.limpar(); return; }
    const w = this.mascara.width, h = this.mascara.height;
    m.clearRect(0, 0, w, h); m.fillStyle = "#fff"; m.strokeStyle = "#fff";
    if (this.estilo === "geometrico" && temGlifos(texto)) {
      desenharGeometrico(m, texto, w, h, { espessura: this.espessura });
    } else {
      m.textAlign = "center"; m.textBaseline = "middle";
      m.font = `500 ${this.tamanhoFonte}px ${this.fonte}`;
      const medida = m.measureText(texto).width;
      const tamanho = Math.min(this.tamanhoFonte, this.tamanhoFonte * w * .9 / Math.max(1, medida));
      m.font = `500 ${tamanho}px ${this.fonte}`;
      m.fillText(texto, w / 2, h / 2);
    }
    const alvos = amostrarMascara(m.getImageData(0, 0, w, h).data, w, h, this.nuvem.maximo - 36);
    this.nuvem.definirAlvos(alvos, agora, imediato);
    m.clearRect(0, 0, w, h);
  }
  dispersar(agora: number) { this.nuvem.dispersar(agora); this.texto = ""; }
  limpar() {
    this.texto = ""; this.nuvem.limpar();
    this.contexto?.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.mascara.getContext("2d")?.clearRect(0, 0, this.mascara.width, this.mascara.height);
  }
  desenhar(agora: number, delta: number, cor: string, reduzido = false) {
    const c = this.contexto; if (!c) return;
    this.nuvem.passo(agora, delta, reduzido);
    c.clearRect(0, 0, this.canvas.width, this.canvas.height);
    c.fillStyle = cor;
    const n = this.nuvem;
    if (this.halo > 0 && !reduzido) {
      // Halo: um quadrado maior e quase transparente por partícula (brilho sem filtro de blur).
      for (let i = 0; i < n.quantidade; i++) {
        if (n.alpha[i] < .05) continue;
        c.globalAlpha = n.alpha[i] * this.halo;
        const r = n.tamanho[i] * this.escala * 3.2;
        c.fillRect(n.x[i] - r / 2, n.y[i] - r / 2, r, r);
      }
    }
    for (let i = 0; i < n.quantidade; i++) {
      if (n.alpha[i] < .012) continue;
      c.globalAlpha = n.alpha[i];
      const r = n.tamanho[i] * this.escala;
      c.fillRect(n.x[i] - r / 2, n.y[i] - r / 2, r, r);
    }
    c.globalAlpha = 1;
  }
}

/**
 * Escolhe até `maximo` destinos dentro da máscara (alfa > 100), espalhados por igual e com um
 * pequeno deslocamento fixo por ponto, para não formar listras da varredura. Determinístico.
 */
export function amostrarMascara(pixels: ArrayLike<number>, w: number, h: number, maximo: number): Float32Array {
  const candidatos: number[] = [];
  for (let y = 3; y < h - 3; y += 2) for (let x = 3; x < w - 3; x += 2)
    if (pixels[(y * w + x) * 4 + 3] > 100) candidatos.push(x, y);
  const total = candidatos.length / 2;
  const numero = Math.max(0, Math.min(maximo, total));
  const alvos = new Float32Array(numero * 2);
  // A alocação ocorre só na troca de glifo; os quadros reutilizam o pool fixo.
  for (let i = 0; i < numero; i++) {
    const j = Math.min(total - 1, Math.floor((i + aleatorio(i + 77) * .999) * total / numero));
    alvos[i * 2] = candidatos[j * 2] + (aleatorio(i + 501) - .5) * 1.6;
    alvos[i * 2 + 1] = candidatos[j * 2 + 1] + (aleatorio(i + 907) - .5) * 1.6;
  }
  return alvos;
}
