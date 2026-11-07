import { aleatorio } from "./scene-math";
import { desenharGeometrico, temGlifos } from "./geometric-glyphs";

export type FaseParticulas = "poeira" | "formando" | "retendo" | "dispersando";
/**
 * "Vida" das partículas enquanto a letra está formada: sem ela, a letra fica parada.
 * - tremor: raio (px) do movimento de cada ponto em volta do seu lugar na letra;
 * - fluxo: fração do tempo em que cada ponto se solta para a poeira e volta (troca contínua);
 * - poeira: brilho da poeira livre em volta das letras; extras: quantos pontos de poeira livre.
 * A energia do áudio (voz ou microfone) aumenta tremor, fluxo e brilho.
 */
export interface Vida {
  tremor: number; fluxo: number; poeira: number; extras: number;
  /** Escalonamento da chegada (ms): os pontos saem da poeira um a um, em fluxo. 0 = todos juntos. */
  chegada: number;
  /** Rigidez da mola na chegada (maior = mais rápido). */
  rigidezChegada: number;
}
export const SEM_VIDA: Vida = { tremor: 0, fluxo: 0, poeira: .025, extras: 36, chegada: 0, rigidezChegada: 48 };
/** Posição atual (no sistema do campo) do grão de poeira ligado ao ponto `i`; false se não houver. */
export type Origem = (i: number, saida: [number, number]) => boolean;
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
  /** Peso do brilho de cada destino (palavras já ditas ficam mais apagadas que a atual). */
  readonly peso: Float32Array;
  quantidade = 0;
  alvos = 0;
  fase: FaseParticulas = "poeira";
  private inicio = 0;
  vida: Vida = SEM_VIDA;
  /** Se definida, a poeira livre é a poeira da cena: os pontos saem dela e voltam para ela. */
  origem?: Origem;
  private readonly atraso: Float32Array;
  private readonly tmp: [number, number] = [0, 0];
  /** Energia do áudio agora (0–1): voz quando ela fala, microfone quando escuta. */
  energia = 0;
  // Parâmetros fixos de cada ponto (frequências, fases, direção e período do fluxo).
  private readonly freqA: Float32Array;
  private readonly freqB: Float32Array;
  private readonly faseA: Float32Array;
  private readonly faseB: Float32Array;
  private readonly dirX: Float32Array;
  private readonly dirY: Float32Array;
  private readonly periodo: Float32Array;
  private readonly alcance: Float32Array;
  constructor(readonly maximo = 1800, readonly largura = 1200, readonly altura = 140) {
    this.ids = new Uint16Array(maximo);
    this.x = new Float32Array(maximo); this.y = new Float32Array(maximo);
    this.vx = new Float32Array(maximo); this.vy = new Float32Array(maximo);
    this.alpha = new Float32Array(maximo); this.tamanho = new Float32Array(maximo);
    this.alvoX = new Float32Array(maximo); this.alvoY = new Float32Array(maximo);
    this.livreX = new Float32Array(maximo); this.livreY = new Float32Array(maximo);
    this.brilho = new Float32Array(maximo);
    this.peso = new Float32Array(maximo).fill(1);
    this.freqA = new Float32Array(maximo); this.freqB = new Float32Array(maximo);
    this.faseA = new Float32Array(maximo); this.faseB = new Float32Array(maximo);
    this.dirX = new Float32Array(maximo); this.dirY = new Float32Array(maximo);
    this.periodo = new Float32Array(maximo); this.alcance = new Float32Array(maximo);
    this.atraso = new Float32Array(maximo);
    for (let i = 0; i < maximo; i++) {
      this.freqA[i] = .7 + aleatorio(i + 1501) * 1.6; this.freqB[i] = .6 + aleatorio(i + 1709) * 1.7;
      this.faseA[i] = aleatorio(i + 2203) * Math.PI * 2; this.faseB[i] = aleatorio(i + 2411) * Math.PI * 2;
      const angulo = aleatorio(i + 2617) * Math.PI * 2;
      this.dirX[i] = Math.cos(angulo); this.dirY[i] = Math.sin(angulo);
      this.periodo[i] = 3.5 + aleatorio(i + 2803) * 5.5;
      this.alcance[i] = 30 + aleatorio(i + 3011) * 70;
      this.atraso[i] = aleatorio(i + 4001);
      this.ids[i] = i;
      this.x[i] = this.livreX[i] = largura * (.04 + aleatorio(i + 8101) * .92);
      this.y[i] = this.livreY[i] = altura * (.09 + aleatorio(i + 1244) * .82);
      this.brilho[i] = .58 + aleatorio(i + 3341) * .37;
      this.tamanho[i] = .68 + aleatorio(i + 9981) * .52;
    }
  }
  definirAlvos(coordenadas: ArrayLike<number>, agora: number, imediato = false, pesos?: ArrayLike<number>) {
    this.alvos = Math.min(this.maximo, Math.floor(coordenadas.length / 2));
    this.quantidade = Math.min(this.maximo, Math.max(this.quantidade, this.alvos + this.vida.extras));
    this.inicio = agora;
    this.fase = imediato ? "retendo" : "formando";
    for (let i = 0; i < this.quantidade; i++) {
      // Com origem, o ponto parte de onde o seu grão de poeira está agora.
      if (this.origem && this.origem(i, this.tmp)) { this.livreX[i] = this.tmp[0]; this.livreY[i] = this.tmp[1]; }
      if (i < this.alvos) {
        this.alvoX[i] = coordenadas[i * 2]; this.alvoY[i] = coordenadas[i * 2 + 1];
        this.peso[i] = pesos?.[i] ?? 1;
        // Partículas apagadas voltam como poeira, jamais nascem já sobre o glifo.
        if (this.alpha[i] < .01) { this.x[i] = this.livreX[i]; this.y[i] = this.livreY[i]; this.alpha[i] = .1; }
        if (imediato) { this.x[i] = this.alvoX[i]; this.y[i] = this.alvoY[i]; this.vx[i] = this.vy[i] = 0; this.alpha[i] = this.brilho[i] * this.peso[i]; }
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
    const chegada = this.vida.chegada;
    if (this.fase === "formando" && agora - this.inicio >= (chegada > 0 ? chegada + 450 : 130)) this.fase = "retendo";
    const formando = this.fase === "formando";
    const retendo = this.fase === "retendo" || formando;
    const dt = Math.max(0, Math.min(100, delta)) / 1000;
    const origem = this.origem;
    if (origem) {
      // A poeira da cena se move: os lugares livres acompanham cada grão ligado a um ponto.
      for (let i = 0; i < this.quantidade; i++)
        if (origem(i, this.tmp)) { this.livreX[i] = this.tmp[0]; this.livreY[i] = this.tmp[1]; }
    }
    const omegaFixo = retendo ? 48 : origem ? 6.5 : 4.2;
    const amortecimentoFixo = Math.exp(-omegaFixo * dt);
    // Voltando para a poeira da cena, o ponto se apaga mais devagar: dá para ver a viagem.
    const fade = Math.exp(-dt / (retendo ? .075 : this.origem ? .3 : .135));
    const vida = this.vida, t = agora / 1000, energia = Math.max(0, Math.min(1, this.energia));
    const viva = retendo && (vida.tremor > 0 || vida.fluxo > 0);
    const tremor = vida.tremor * (1 + energia * 4);
    const fluxo = Math.min(.35, vida.fluxo * (1 + energia * 1.5));
    for (let i = 0; i < this.quantidade; i++) {
      // Na chegada escalonada, cada ponto espera a sua vez na poeira antes de partir.
      const partiu = !formando || chegada <= 0 || agora - this.inicio >= this.atraso[i] * chegada;
      const glifo = retendo && i < this.alvos && partiu;
      const omega = formando && chegada > 0 && glifo ? this.vida.rigidezChegada : omegaFixo;
      const amortecimento = omega === omegaFixo ? amortecimentoFixo : Math.exp(-omega * dt);
      let tx = glifo ? this.alvoX[i] : this.livreX[i];
      let ty = glifo ? this.alvoY[i] : this.livreY[i];
      let realce = 1;
      if (viva && !reduzido) {
        const ondaA = Math.sin(t * this.freqA[i] + this.faseA[i]), ondaB = Math.cos(t * this.freqB[i] + this.faseB[i]);
        if (glifo) {
          tx += tremor * ondaA; ty += tremor * ondaB;
          if (fluxo > 0) {
            // Cada ponto passa uma fração do seu período solto na poeira e volta para a letra.
            const ciclo = (t / this.periodo[i] + this.faseA[i] / (Math.PI * 2)) % 1;
            if (ciclo < fluxo) {
              const s = Math.sin(Math.PI * ciclo / fluxo);
              if (origem) {
                // Vai até o seu grão na órbita e volta para a letra.
                tx += (this.livreX[i] - tx) * s; ty += (this.livreY[i] - ty) * s;
                realce = 1 - .5 * s;
              } else {
                const longe = this.alcance[i] * s * (1 + energia);
                tx += this.dirX[i] * longe; ty += this.dirY[i] * longe * .55;
                realce = 1 - .7 * s;
              }
            }
          }
          // Cintilar leve; com a voz, a letra brilha mais.
          realce *= (.82 + .18 * ondaB) * (1 + .35 * energia);
        } else if (!origem) {
          tx += 16 * ondaA; ty += 7 * ondaB; // poeira livre circulando
        }
      }
      if (reduzido) {
        this.x[i] = tx; this.y[i] = ty; this.vx[i] = this.vy[i] = 0;
        this.alpha[i] = glifo ? this.brilho[i] * this.peso[i] : 0; continue;
      }
      // Solução analítica da mola criticamente amortecida, estável em 30/60/120 FPS.
      const dx = this.x[i] - tx, dy = this.y[i] - ty;
      const bx = this.vx[i] + omega * dx, by = this.vy[i] + omega * dy;
      this.x[i] = tx + (dx + bx * dt) * amortecimento;
      this.y[i] = ty + (dy + by * dt) * amortecimento;
      this.vx[i] = (this.vx[i] - omega * bx * dt) * amortecimento;
      this.vy[i] = (this.vy[i] - omega * by * dt) * amortecimento;
      // Com origem, fora da letra o ponto é a própria poeira da cena (que já aparece): some aqui.
      const alvoAlpha = glifo ? Math.min(1, this.brilho[i] * this.peso[i] * realce) : origem ? (formando && i < this.alvos ? .18 : 0) : retendo ? (viva ? vida.poeira : .025) : 0;
      this.alpha[i] = alvoAlpha + (this.alpha[i] - alvoAlpha) * fade;
    }
    if (!retendo && agora - this.inicio > (origem ? 750 : 700)) this.limpar();
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
  /** Fontes instaladas no computador para a marca, em ordem (ex.: Nasalization). Se nenhuma
   * estiver instalada, vale o alfabeto geométrico próprio. Nenhum arquivo de fonte é embutido. */
  fontesInstaladas?: string[];
  /** Movimento enquanto a letra está formada (ver `Vida`); sem isso, ela fica parada. */
  vida?: Partial<Vida>;
  /**
   * Camada compartilhada (canvas sobre a HUD inteira): o campo desenha nela, na posição do seu
   * canvas âncora, e os pontos podem sair dos limites dele (vêm da poeira da cena).
   */
  camada?: Camada;
  /** Posição na tela (px da camada) do grão de poeira `indice` da cena. */
  origemTela?: (indice: number, saida: [number, number]) => boolean;
  /** Retângulo (na camada) que o campo ocupa; padrão: o do próprio canvas. */
  retangulo?: () => { left: number; top: number; width: number };
  /** Semente para escolher grãos de poeira diferentes em cada campo. */
  semente?: number;
  /** Multiplica o tamanho das partículas (canvas que a tela reduz precisa de pontos maiores). */
  escalaParticula?: number;
}
/** Canvas transparente sobre a HUD, limpo uma vez por quadro por quem o possui. */
export interface Camada { contexto: CanvasRenderingContext2D | null; escala: number; deslocamento: () => { left: number; top: number } }

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
  private fontesInstaladas: string[];
  private camada?: Camada;
  private retangulo: () => { left: number; top: number; width: number };
  private ret = { left: 0, top: 0, width: 1 };
  private readonly tela: [number, number] = [0, 0];
  /** A fonte instalada em uso na marca, ou "" (alfabeto próprio). */
  fonteEmUso = "";
  constructor(private canvas: HTMLCanvasElement, opcoes: OpcoesCampoTexto = {}) {
    canvas.width = opcoes.largura ?? 1200; canvas.height = opcoes.altura ?? 140;
    this.nuvem = new NuvemLetras(opcoes.maximo ?? 1800, canvas.width, canvas.height);
    this.nuvem.vida = { ...SEM_VIDA, ...opcoes.vida };
    this.contexto = canvas.getContext("2d");
    this.mascara = document.createElement("canvas");
    this.mascara.width = canvas.width; this.mascara.height = canvas.height;
    this.fonte = opcoes.fonte ?? "'Segoe UI', Arial, sans-serif";
    this.tamanhoFonte = opcoes.tamanhoFonte ?? 84;
    this.estilo = opcoes.estilo ?? "fonte";
    this.espessura = opcoes.espessura ?? 0.13;
    this.halo = opcoes.brilho ?? 0;
    this.escala = opcoes.escalaParticula ?? 1;
    this.fontesInstaladas = opcoes.fontesInstaladas ?? [];
    this.camada = opcoes.camada;
    this.retangulo = opcoes.retangulo ?? (() => {
      const r = canvas.getBoundingClientRect(), d = this.camada?.deslocamento() ?? { left: 0, top: 0 };
      return { left: r.left - d.left, top: r.top - d.top, width: r.width };
    });
    const origemTela = opcoes.origemTela, semente = opcoes.semente ?? 0;
    if (this.camada && origemTela) {
      this.nuvem.origem = (i, saida) => {
        // Cada ponto fica ligado a um grão fixo da poeira (espalhado por toda a órbita).
        if (!origemTela(i * 7919 + semente, this.tela)) return false;
        const k = canvas.width / Math.max(1, this.ret.width);
        saida[0] = (this.tela[0] - this.ret.left) * k; saida[1] = (this.tela[1] - this.ret.top) * k;
        return true;
      };
    }
  }
  /**
   * Forma `texto` com as partículas. `anteriores` (palavras já ditas) entram menores e mais
   * apagadas à esquerda, na mesma nuvem: a troca de palavra vira um deslizar da linha.
   */
  definirTexto(texto: string, agora: number, imediato = false, anteriores: readonly string[] = []) {
    const chave = anteriores.length ? `${anteriores.join(" ")}\u0000${texto}` : texto;
    if (chave === this.texto && this.nuvem.fase !== "poeira" && this.nuvem.fase !== "dispersando") return;
    this.texto = chave;
    const m = this.mascara.getContext("2d", { willReadFrequently: true });
    if (!m || !texto.trim()) { this.limpar(); return; }
    const w = this.mascara.width, h = this.mascara.height;
    m.clearRect(0, 0, w, h); m.fillStyle = "#fff"; m.strokeStyle = "#fff";
    const orcamento = this.nuvem.maximo - 36;
    let alvos: Float32Array, pesos: Float32Array | undefined;
    const instalada = this.estilo === "geometrico" ? escolherFonteInstalada(m, this.fontesInstaladas) : "";
    this.fonteEmUso = instalada;
    if (instalada) {
      // Fonte do computador (ex.: Nasalization): só desenha a máscara; as partículas formam a letra.
      const maiusculo = texto.toLocaleUpperCase("pt-BR");
      m.textAlign = "center"; m.textBaseline = "middle";
      m.font = `400 100px "${instalada}"`;
      // Só maiúsculas: a letra pode ocupar quase toda a altura do canvas.
      const tamanho = Math.min(h * .82, 100 * w * .9 / Math.max(1, m.measureText(maiusculo).width));
      m.font = `400 ${tamanho}px "${instalada}"`;
      m.fillText(maiusculo, w / 2, h / 2);
      alvos = amostrarMascara(m.getImageData(0, 0, w, h).data, w, h, orcamento);
    } else if (this.estilo === "geometrico" && temGlifos(texto)) {
      desenharGeometrico(m, texto, w, h, { espessura: this.espessura });
      alvos = amostrarMascara(m.getImageData(0, 0, w, h).data, w, h, orcamento);
    } else {
      m.textAlign = "center"; m.textBaseline = "middle";
      m.font = `500 ${this.tamanhoFonte}px ${this.fonte}`;
      const medida = m.measureText(texto).width;
      // Com palavras anteriores, a atual ocupa no máximo 60% da largura (o resto é contexto).
      const limite = anteriores.length ? .6 : .9;
      const tamanho = Math.min(this.tamanhoFonte, this.tamanhoFonte * w * limite / Math.max(1, medida));
      m.font = `500 ${tamanho}px ${this.fonte}`;
      m.fillText(texto, w / 2, h / 2);
      const atual = amostrarMascara(m.getImageData(0, 0, w, h).data, w, h, anteriores.length ? Math.round(orcamento * .78) : orcamento);
      alvos = atual; pesos = undefined;
      if (anteriores.length) {
        const larguraAtual = Math.min(medida * tamanho / this.tamanhoFonte, w * limite);
        const pequeno = Math.max(20, tamanho * .46);
        const direita = w / 2 - larguraAtual / 2 - tamanho * .32;
        m.clearRect(0, 0, w, h);
        m.font = `500 ${pequeno}px ${this.fonte}`; m.textAlign = "right";
        // Só as palavras que cabem à esquerda, as mais recentes primeiro.
        const cabem: string[] = [];
        for (let i = anteriores.length - 1; i >= 0; i--) {
          const tentativa = [anteriores[i], ...cabem].join(" ");
          if (m.measureText(tentativa).width > direita - 8) break;
          cabem.unshift(anteriores[i]);
        }
        if (cabem.length) {
          m.fillText(cabem.join(" "), direita, h / 2 + tamanho * .08);
          const contexto = amostrarMascara(m.getImageData(0, 0, w, h).data, w, h, orcamento - atual.length / 2);
          alvos = new Float32Array(atual.length + contexto.length);
          alvos.set(atual); alvos.set(contexto, atual.length);
          pesos = new Float32Array(alvos.length / 2).fill(1);
          pesos.fill(.55, atual.length / 2);
        }
      }
    }
    this.nuvem.definirAlvos(alvos, agora, imediato, pesos);
    m.clearRect(0, 0, w, h);
  }
  dispersar(agora: number) { this.nuvem.dispersar(agora); this.texto = ""; }
  limpar() {
    this.texto = ""; this.nuvem.limpar();
    this.contexto?.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.mascara.getContext("2d")?.clearRect(0, 0, this.mascara.width, this.mascara.height);
  }
  desenhar(agora: number, delta: number, cor: string, reduzido = false, energia = 0) {
    const c = this.camada ? this.camada.contexto : this.contexto; if (!c) return;
    if (this.camada) this.ret = this.retangulo();
    this.nuvem.energia = energia;
    this.nuvem.passo(agora, delta, reduzido);
    if (this.camada) {
      // Coordenadas do campo → camada: escala do canvas âncora na tela e densidade de pixels.
      const k = this.ret.width / this.canvas.width * this.camada.escala;
      c.setTransform(k, 0, 0, k, this.ret.left * this.camada.escala, this.ret.top * this.camada.escala);
    } else c.clearRect(0, 0, this.canvas.width, this.canvas.height);
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
    if (!reduzido) {
      // Rastro: os pontos em viagem (da poeira para a letra e de volta) deixam um traço curto
      // na direção do movimento, todos num único traçado.
      c.beginPath();
      let algum = false;
      for (let i = 0; i < n.quantidade; i++) {
        if (n.alpha[i] < .05) continue;
        const vx = n.vx[i], vy = n.vy[i];
        if (vx * vx + vy * vy < 160 * 160) continue;
        c.moveTo(n.x[i], n.y[i]); c.lineTo(n.x[i] - vx * .045, n.y[i] - vy * .045); algum = true;
      }
      if (algum) { c.strokeStyle = cor; c.lineWidth = this.escala * .9; c.globalAlpha = .35; c.stroke(); }
    }
    for (let i = 0; i < n.quantidade; i++) {
      if (n.alpha[i] < .012) continue;
      c.globalAlpha = n.alpha[i];
      const r = n.tamanho[i] * this.escala;
      c.fillRect(n.x[i] - r / 2, n.y[i] - r / 2, r, r);
    }
    c.globalAlpha = 1;
    if (this.camada) c.setTransform(1, 0, 0, 1, 0, 0);
  }
}

/**
 * Escolhe até `maximo` destinos dentro da máscara (alfa > 100), espalhados por igual e com um
 * pequeno deslocamento fixo por ponto, para não formar listras da varredura. Determinístico.
 */
export function amostrarMascara(pixels: ArrayLike<number>, w: number, h: number, maximo: number): Float32Array {
  const candidatos: number[] = [];
  for (let y = 4; y < h - 4; y += 2) for (let x = 4; x < w - 4; x += 2)
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

/**
 * Se uma fonte está instalada no computador: compara a largura de um texto com a fonte pedida
 * e só com as genéricas. Sem baixar nada (nenhuma fonte é embutida na HUD).
 */
export function fonteInstalada(ctx: CanvasRenderingContext2D, nome: string): boolean {
  const amostra = "NORA mwWiIl 0123";
  for (const generica of ["monospace", "serif", "sans-serif"]) {
    ctx.font = `100px ${generica}`;
    const base = ctx.measureText(amostra).width;
    ctx.font = `100px "${nome}", ${generica}`;
    if (Math.abs(ctx.measureText(amostra).width - base) > 0.5) return true;
  }
  return false;
}

/** A primeira das fontes que está instalada, ou "". */
export function escolherFonteInstalada(ctx: CanvasRenderingContext2D, nomes: readonly string[]): string {
  return nomes.find(nome => fonteInstalada(ctx, nome)) ?? "";
}
