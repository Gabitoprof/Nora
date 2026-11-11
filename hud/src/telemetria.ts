/**
 * HUD telemetry for acceptance: only numbers (no conversation text).
 *
 * - interval between frames (what the person sees: with a 30 FPS cap the ideal is 33.3 ms);
 * - work per frame (JavaScript ms to draw the scene and the letters);
 * - sound → word delay: how much of the word's audio had already played when it appeared;
 * - WebGL contexts created and lost (a leak or a graphics card drop);
 * - JavaScript memory (Chrome/Edge only).
 *
 * Keeps the latest samples in fixed buffers; `resumo()` computes the percentiles.
 */
export interface DiagnosticoHud {
  janela_s: number;
  quadros: number;
  intervalo_p50: number;
  intervalo_p95: number;
  intervalo_pior: number;
  trabalho_p95: number;
  palavras: number;
  atraso_palavra_p50: number;
  atraso_palavra_p95: number;
  contextos_webgl: number;
  contextos_perdidos: number;
  memoria_js_mb: number;
  fps_limite: number;
}

class Janela {
  private valores: Float32Array;
  private total = 0;
  constructor(tamanho: number) { this.valores = new Float32Array(tamanho); }
  pôr(valor: number) { this.valores[this.total % this.valores.length] = valor; this.total++; }
  get quantidade() { return Math.min(this.total, this.valores.length); }
  percentil(p: number) {
    const n = this.quantidade;
    if (!n) return 0;
    const ordenados = Array.from(this.valores.subarray(0, n)).sort((a, b) => a - b);
    return ordenados[Math.min(n - 1, Math.max(0, Math.ceil(p * n) - 1))];
  }
  pior() { return this.quantidade ? Math.max(...Array.from(this.valores.subarray(0, this.quantidade))) : 0; }
  limpar() { this.total = 0; }
}

const arredondar = (v: number) => Math.round(v * 10) / 10;

export class Telemetria {
  private intervalos = new Janela(3600);
  private trabalhos = new Janela(3600);
  private atrasos = new Janela(600);
  private inicio = performance.now();
  contextos = 0;
  perdidos = 0;
  fpsLimite = 30;
  quadro(intervalo: number, trabalho: number) {
    if (intervalo > 0 && intervalo < 5000) this.intervalos.pôr(intervalo);
    if (trabalho >= 0 && trabalho < 5000) this.trabalhos.pôr(trabalho);
  }
  palavra(atrasoMs: number) {
    if (Number.isFinite(atrasoMs)) this.atrasos.pôr(Math.max(0, atrasoMs));
  }
  resumo(agora = performance.now()): DiagnosticoHud {
    const memoria = (performance as Performance & { memory?: { usedJSHeapSize: number } }).memory;
    return {
      janela_s: Math.round((agora - this.inicio) / 1000),
      quadros: this.intervalos.quantidade,
      intervalo_p50: arredondar(this.intervalos.percentil(.5)),
      intervalo_p95: arredondar(this.intervalos.percentil(.95)),
      intervalo_pior: arredondar(this.intervalos.pior()),
      trabalho_p95: arredondar(this.trabalhos.percentil(.95)),
      palavras: this.atrasos.quantidade,
      atraso_palavra_p50: arredondar(this.atrasos.percentil(.5)),
      atraso_palavra_p95: arredondar(this.atrasos.percentil(.95)),
      contextos_webgl: this.contextos,
      contextos_perdidos: this.perdidos,
      memoria_js_mb: memoria ? arredondar(memoria.usedJSHeapSize / 1048576) : 0,
      fps_limite: this.fpsLimite,
    };
  }
  /** Short text for the Settings panel. */
  linha(): string {
    const r = this.resumo();
    if (!r.quadros) return "";
    const palavra = r.palavras ? ` · palavra p95 ${r.atraso_palavra_p95} ms` : "";
    return `Quadro p50 ${r.intervalo_p50} / p95 ${r.intervalo_p95} / pior ${r.intervalo_pior} ms${palavra} · WebGL ${r.contextos_webgl}${r.contextos_perdidos ? ` (${r.contextos_perdidos} perdido)` : ""}`;
  }
}
