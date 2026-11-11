import type { Acustica } from "./scene-audio";
import type { Evento, FalaTemporizada, Modelo, PalavraTemporizada } from "./state";
import { CampoParticulasTexto, type OpcoesCampoTexto } from "./text-particle-field";

/** Media clock: state and timeline arrival do not move the speech forward. */
export class RelogioFala {
  /**
   * `idadeMaxima`: a sample older than this (ms) does not count (the word disappears);
   * `extrapolacaoMaxima`: how far the clock advances on its own since the last sample (ms).
   */
  // Measured in tests/relogio-medicao.test.ts (docs/HOMOLOGACAO.md): 450/400 loses no words
  // with stalls of up to 450 ms and keeps the p95 delay at 50 ms.
  constructor(readonly idadeMaxima = 450, readonly extrapolacaoMaxima = 400) {}
  /** Setbacks smaller than this (ms) are network noise: the position does not go back (no flicker). */
  static readonly TOLERANCIA_RECUO = 60;
  private ultimaPosicao = -1;
  private ultimoId = -1;
  private amostra: Acustica | null = null;
  private recebida = -Infinity;
  private encerrado = -1;
  private resultado: { palavra: PalavraTemporizada; posicao: number } = {
    palavra: { texto: "", inicio_ms: 0, fim_ms: 0, destaque: false }, posicao: 0,
  };
  atualizar(amostra: Acustica | null, agora: number) {
    if (amostra?.fonte !== "voz") return;
    if (amostra.reproducao_id <= this.encerrado) return;
    const antiga = this.amostra;
    if (antiga && (amostra.reproducao_id < antiga.reproducao_id ||
      amostra.reproducao_id === antiga.reproducao_id && amostra.ativo && amostra.posicao_ms < antiga.posicao_ms)) return;
    this.amostra = amostra; this.recebida = agora;
    if (!amostra.ativo) this.encerrado = amostra.reproducao_id;
  }
  limpar() { this.ultimaPosicao = -1; this.ultimoId = -1; this.amostra = null; this.recebida = -Infinity; this.encerrado = -1; this.resultado.palavra = { texto: "", inicio_ms: 0, fim_ms: 0, destaque: false }; this.resultado.posicao = 0; }
  palavra(fala: FalaTemporizada | null, agora: number) {
    const a = this.amostra;
    // RAF may precede the SSE arrival within the same frame: never move the clock back.
    const decorrido = Math.max(0, agora - this.recebida);
    if (!a?.ativo || !fala || fala.id !== a.reproducao_id || decorrido > this.idadeMaxima || a.rms < .002) return null;
    let posicao = Math.min(a.duracao_ms || fala.duracao_ms, a.posicao_ms + Math.min(decorrido, this.extrapolacaoMaxima));
    // A new sample arrives with the network delay and "pulls" the position a few ms back: ignore.
    if (a.reproducao_id === this.ultimoId && posicao < this.ultimaPosicao && this.ultimaPosicao - posicao < RelogioFala.TOLERANCIA_RECUO) posicao = this.ultimaPosicao;
    this.ultimaPosicao = posicao; this.ultimoId = a.reproducao_id;
    let inicio = 0, fim = fala.palavras.length - 1;
    while (inicio <= fim) {
      const meio = (inicio + fim) >>> 1, palavra = fala.palavras[meio];
      if (posicao < palavra.inicio_ms) fim = meio - 1;
      else if (posicao >= palavra.fim_ms) inicio = meio + 1;
      else { this.resultado.palavra = palavra; this.resultado.posicao = posicao; return this.resultado; }
    }
    return null;
  }
  /** There is a recent playback sample for this utterance (between words or in a short pause). */
  ativo(fala: FalaTemporizada | null, agora: number) {
    const a = this.amostra;
    return !!(a?.ativo && fala && fala.id === a.reproducao_id && agora - this.recebida <= this.idadeMaxima);
  }
}

/** The word stays until the next one starts, pauses included, up to this cap (long silence). */
export const TETO_PAUSA_MS = 1500;
/**
 * Word movement: light tremor (loosening points would hurt reading) and a fast arrival from the
 * dust. Measured in tests/text-particles.test.ts: readable (90% of the points within 3 px) in
 * ~116 ms, target ≤ 150 ms.
 */
export const VIDA_PALAVRAS = { tremor: .45, chegada: 30, rigidezChegada: 80 };
/** How many words already said stay visible to the left of the current one. */
export const ANTERIORES = 3;

/** A single semantic glyph at a time; the same particles do the transition and the dissolve. */
export class PalavrasParticulas {
  private relogio = new RelogioFala();
  private ultimaAmostra: Acustica | null = null;
  private fala: FalaTemporizada | null = null;
  private ativa = false;
  private reduzido = false;
  private chave = "";
  private anterior = 0;
  private maiorId = 0;
  private encerrado = 0;
  /** Notified when a word appears: how much of its audio had already played (ms). */
  aoMostrar?: (atrasoMs: number) => void;
  /** Cap on holding during pauses (ms); configurable. */
  tetoPausa = TETO_PAUSA_MS;
  /** Words already said in this utterance (only those already played; never the next ones). */
  private anteriores: string[] = [];
  private idAnteriores = 0;
  private palavraAtual = "";
  private semPalavra = 0;
  readonly campo: CampoParticulasTexto;
  constructor(private canvas: HTMLCanvasElement, private legenda: HTMLElement, extras: OpcoesCampoTexto = {}) {
    this.campo = new CampoParticulasTexto(canvas, {
      maximo: 2000, brilho: .34, escalaParticula: 1.35,
      vida: VIDA_PALAVRAS,
      ...extras,
    });
  }
  receberEvento(evento: Evento) {
    if (["conectado", "desconectado", "recuperando"].includes(evento.tipo)) { this.limpar(); return; }
    if (evento.tipo !== "reproducao_encerrada") return;
    const d = evento.dados;
    if (typeof d.id !== "number" || typeof d.posicao_ms !== "number" || typeof d.duracao_ms !== "number" || typeof d.interrompida !== "boolean") return;
    if (d.id < this.maiorId || d.id <= this.encerrado) return; // old or repeated notice
    // End of playback (natural or interrupted): the word disappears at once, without holding.
    this.encerrado = d.id;
    this.apagar(); this.fala = null;
  }
  atualizar(modelo: Modelo, habilitada: boolean, reduzido: boolean, agora = performance.now()) {
    this.ativa = habilitada && !modelo.privacidade && modelo.conectado;
    if (reduzido !== this.reduzido) { this.chave = ""; this.campo.limpar(); }
    this.reduzido = reduzido;
    if (!this.ativa) { this.limpar(); this.ultimaAmostra = modelo.acustica; return; }
    const proxima = modelo.fala_temporizada;
    if (proxima && proxima.id > this.maiorId) {
      this.apagar(); this.maiorId = proxima.id;
    }
    if (proxima && proxima.id >= this.maiorId && proxima.id > this.encerrado) {
      this.fala = proxima;
    } else this.fala = null;
    if (modelo.acustica !== this.ultimaAmostra) {
      this.ultimaAmostra = modelo.acustica;
      this.relogio.atualizar(modelo.acustica, agora);
      if (modelo.acustica?.fonte === "voz" && modelo.acustica.reproducao_id > this.maiorId) {
        this.maiorId = modelo.acustica.reproducao_id; this.fala = null; this.apagar();
      }
    }
    if (!this.fala && ["erro", "recuperando"].includes(modelo.estado)) this.apagar();
    if (reduzido) this.desenhar(agora, "#d8e1e5", true, 0);
  }
  private apagar() {
    this.canvas.hidden = true; this.legenda.hidden = true; this.legenda.textContent = "";
    this.canvas.removeAttribute("aria-label"); this.canvas.removeAttribute("data-fase");
    this.campo.limpar(); this.chave = "";
    this.anteriores = []; this.palavraAtual = ""; this.semPalavra = 0;
  }
  limpar() {
    this.relogio.limpar(); this.ultimaAmostra = null;
    this.fala = null;
    this.maiorId = this.encerrado = 0; this.anterior = 0; this.apagar();
  }
  desenhar(agora: number, cor: string, reduzido: boolean, delta?: number, energia = 0) {
    const dt = delta ?? (this.anterior === 0 ? 1000 / 30 : Math.max(0, agora - this.anterior)); this.anterior = agora;
    if (!this.ativa) return;
    const amostra = this.relogio.palavra(this.fala, agora);
    const palavra = amostra?.palavra;
    if (palavra) {
      const id = this.fala!.id;
      const chave = `${id}:${palavra.inicio_ms}:${palavra.texto}`;
      this.semPalavra = 0;
      if (chave !== this.chave) {
        this.chave = chave;
        if (id !== this.idAnteriores) { this.anteriores = []; this.idAnteriores = id; this.palavraAtual = ""; }
        if (this.palavraAtual) this.anteriores = [...this.anteriores, this.palavraAtual].slice(-ANTERIORES);
        this.palavraAtual = palavra.texto;
        this.aoMostrar?.(amostra!.posicao - palavra.inicio_ms);
        if (!reduzido) this.campo.definirTexto(palavra.texto, agora, false, this.anteriores);
        const precisao = this.fala!.precisao;
        this.legenda.textContent = `${palavra.texto} · ${precisao === "estimada" ? "tempo estimado no áudio" : "tempo alinhado ao áudio"}`;
        this.canvas.setAttribute("aria-label", `Palavra atual: ${palavra.texto}`);
      }
      this.canvas.hidden = reduzido;
      this.legenda.hidden = false;
    } else {
      // Entre palavras e nas pausas, com a reprodução ainda ativa, a palavra fica até a próxima
      // começar (sem tela vazia), até o teto de silêncio longo.
      const ativo = this.relogio.ativo(this.fala, agora);
      if (this.chave && ativo && !this.semPalavra) this.semPalavra = agora;
      const segurando = ativo && this.semPalavra > 0 && agora - this.semPalavra <= this.tetoPausa;
      if (!segurando) {
        if (this.chave) { this.campo.dispersar(agora); this.chave = ""; }
        this.anteriores = []; this.palavraAtual = ""; this.semPalavra = 0;
        this.legenda.hidden = true; this.legenda.textContent = ""; this.canvas.removeAttribute("aria-label");
      }
    }
    this.campo.desenhar(agora, dt, cor, reduzido, energia);
    this.canvas.dataset.fase = this.campo.nuvem.fase;
    if (this.campo.nuvem.fase === "poeira") this.canvas.hidden = true;
    // Ao trocar a preferência não conservar a máscara de uma animação anterior.
    if (this.reduzido && this.campo.nuvem.quantidade > 0) this.campo.limpar();
  }
}
