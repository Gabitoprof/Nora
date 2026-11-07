import type { Acustica } from "./scene-audio";
import type { Evento, FalaTemporizada, Modelo, PalavraTemporizada } from "./state";
import { CampoParticulasTexto } from "./text-particle-field";

/** Relógio da mídia: estado e chegada da timeline não fazem a locução avançar. */
export class RelogioFala {
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
  limpar() { this.amostra = null; this.recebida = -Infinity; this.encerrado = -1; this.resultado.palavra = { texto: "", inicio_ms: 0, fim_ms: 0, destaque: false }; this.resultado.posicao = 0; }
  palavra(fala: FalaTemporizada | null, agora: number) {
    const a = this.amostra;
    // RAF pode preceder a chegada SSE dentro do mesmo frame: jamais voltar o relógio.
    const decorrido = Math.max(0, agora - this.recebida);
    if (!a?.ativo || !fala || fala.id !== a.reproducao_id || decorrido > 300 || a.rms < .002) return null;
    const posicao = Math.min(a.duracao_ms || fala.duracao_ms, a.posicao_ms + Math.min(decorrido, 250));
    let inicio = 0, fim = fala.palavras.length - 1;
    while (inicio <= fim) {
      const meio = (inicio + fim) >>> 1, palavra = fala.palavras[meio];
      if (posicao < palavra.inicio_ms) fim = meio - 1;
      else if (posicao >= palavra.fim_ms) inicio = meio + 1;
      else { this.resultado.palavra = palavra; this.resultado.posicao = posicao; return this.resultado; }
    }
    return null;
  }
  /** Há amostra recente da reprodução desta fala (entre palavras ou numa pausa curta). */
  ativo(fala: FalaTemporizada | null, agora: number) {
    const a = this.amostra;
    return !!(a?.ativo && fala && fala.id === a.reproducao_id && agora - this.recebida <= 300);
  }
}

/** Quanto a palavra segura entre uma e outra (pausa curta) antes de se desfazer. */
export const SEGURAR_MS = 320;
/** Quantas palavras já ditas ficam visíveis à esquerda da atual. */
export const ANTERIORES = 3;

/** Validação temporal do fim natural; cancelamento nunca oferece uma última palavra. */
export function ultimaPalavraDevida(fala: FalaTemporizada | null, id: number, posicao: number, duracao: number, interrompida: boolean) {
  if (interrompida || !fala || fala.id !== id || posicao < duracao - 30 || posicao > duracao + 30) return null;
  const ultima = fala.palavras[fala.palavras.length - 1];
  return ultima && ultima.inicio_ms <= posicao && ultima.fim_ms <= duracao + 1 ? ultima : null;
}

/** Um único glifo semântico por vez; as mesmas partículas fazem a transição e a dissolução. */
export class PalavrasParticulas {
  private relogio = new RelogioFala();
  private ultimaAmostra: Acustica | null = null;
  private fala: FalaTemporizada | null = null;
  private ultimaFala: FalaTemporizada | null = null;
  private ativa = false;
  private reduzido = false;
  private chave = "";
  private anterior = 0;
  private maiorId = 0;
  private encerrado = 0;
  private final: { palavra: PalavraTemporizada; id: number; ate: number; precisao: string } | null = null;
  /** Palavras já ditas desta fala (só as que já tocaram; nunca as próximas). */
  private anteriores: string[] = [];
  private idAnteriores = 0;
  private palavraAtual = "";
  private semPalavra = 0;
  readonly campo: CampoParticulasTexto;
  constructor(private canvas: HTMLCanvasElement, private legenda: HTMLElement) {
    this.campo = new CampoParticulasTexto(canvas, { maximo: 2000, brilho: .22, escalaParticula: 1.35 });
  }
  receberEvento(evento: Evento, agora = performance.now()) {
    if (["conectado", "desconectado", "recuperando"].includes(evento.tipo)) { this.limpar(); return; }
    if (evento.tipo !== "reproducao_encerrada") return;
    const d = evento.dados;
    if (typeof d.id !== "number" || typeof d.posicao_ms !== "number" || typeof d.duracao_ms !== "number" || typeof d.interrompida !== "boolean") return;
    if (d.id < this.maiorId || d.id <= this.encerrado) return;
    this.encerrado = d.id;
    const ultima = this.ativa ? ultimaPalavraDevida(this.ultimaFala, d.id, d.posicao_ms, d.duracao_ms, d.interrompida) : null;
    if (!ultima) { this.apagar(); this.fala = this.ultimaFala = null; this.final = null; return; }
    // Só o último glifo já devido, com retenção curta; não reproduzir palavras perdidas.
    this.final = { palavra: ultima, id: d.id, ate: agora + 120, precisao: this.ultimaFala!.precisao };
    this.fala = null;
  }
  atualizar(modelo: Modelo, habilitada: boolean, reduzido: boolean, agora = performance.now()) {
    this.ativa = habilitada && !modelo.privacidade && modelo.conectado;
    if (reduzido !== this.reduzido) { this.chave = ""; this.campo.limpar(); }
    this.reduzido = reduzido;
    if (!this.ativa) { this.limpar(); this.ultimaAmostra = modelo.acustica; return; }
    const proxima = modelo.fala_temporizada;
    if (proxima && proxima.id > this.maiorId) {
      this.apagar(); this.final = null; this.ultimaFala = null; this.maiorId = proxima.id;
    }
    if (proxima && proxima.id >= this.maiorId && proxima.id > this.encerrado) {
      this.fala = this.ultimaFala = proxima;
    } else this.fala = null;
    if (modelo.acustica !== this.ultimaAmostra) {
      this.ultimaAmostra = modelo.acustica;
      this.relogio.atualizar(modelo.acustica, agora);
      if (modelo.acustica?.fonte === "voz" && modelo.acustica.reproducao_id > this.maiorId) {
        this.maiorId = modelo.acustica.reproducao_id; this.final = null; this.fala = null; this.apagar();
      }
    }
    if (!this.fala && !this.final && ["erro", "recuperando"].includes(modelo.estado)) this.apagar();
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
    this.fala = this.ultimaFala = null; this.final = null;
    this.maiorId = this.encerrado = 0; this.anterior = 0; this.apagar();
  }
  desenhar(agora: number, cor: string, reduzido: boolean, delta?: number) {
    const dt = delta ?? (this.anterior === 0 ? 1000 / 30 : Math.max(0, agora - this.anterior)); this.anterior = agora;
    if (!this.ativa) return;
    const amostra = this.relogio.palavra(this.fala, agora);
    const final = this.final && agora <= this.final.ate ? this.final : null;
    const palavra = final?.palavra ?? amostra?.palavra;
    if (palavra) {
      const id = final?.id ?? this.fala!.id;
      const chave = `${id}:${palavra.inicio_ms}:${palavra.texto}`;
      this.semPalavra = 0;
      if (chave !== this.chave) {
        this.chave = chave;
        if (id !== this.idAnteriores) { this.anteriores = []; this.idAnteriores = id; this.palavraAtual = ""; }
        if (this.palavraAtual) this.anteriores = [...this.anteriores, this.palavraAtual].slice(-ANTERIORES);
        this.palavraAtual = palavra.texto;
        if (!reduzido) this.campo.definirTexto(palavra.texto, agora, false, this.anteriores);
        const precisao = final?.precisao ?? this.fala!.precisao;
        this.legenda.textContent = `${palavra.texto} · ${precisao === "estimada" ? "tempo estimado no áudio" : "tempo alinhado ao áudio"}`;
        this.canvas.setAttribute("aria-label", `Palavra atual: ${palavra.texto}`);
      }
      this.canvas.hidden = reduzido;
      this.legenda.hidden = false;
    } else {
      // Entre palavras, com a fala ainda tocando, a palavra segura um instante: sem piscar.
      if (this.chave && !this.final && this.relogio.ativo(this.fala, agora)) {
        if (!this.semPalavra) this.semPalavra = agora;
      }
      const segurando = this.semPalavra > 0 && agora - this.semPalavra <= SEGURAR_MS && !this.final && this.relogio.ativo(this.fala, agora);
      if (!segurando) {
        if (this.chave) { this.campo.dispersar(agora); this.chave = ""; }
        this.anteriores = []; this.palavraAtual = ""; this.semPalavra = 0;
        this.legenda.hidden = true; this.legenda.textContent = ""; this.canvas.removeAttribute("aria-label");
        if (this.final && agora > this.final.ate) { this.final = null; this.ultimaFala = null; }
      }
    }
    this.campo.desenhar(agora, dt, cor, reduzido);
    this.canvas.dataset.fase = this.campo.nuvem.fase;
    if (this.campo.nuvem.fase === "poeira") this.canvas.hidden = true;
    // Ao trocar a preferência não conservar a máscara de uma animação anterior.
    if (this.reduzido && this.campo.nuvem.quantidade > 0) this.campo.limpar();
  }
}
