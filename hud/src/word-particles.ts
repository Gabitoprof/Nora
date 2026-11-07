import type { Acustica } from "./scene-audio";
import type { Evento, FalaTemporizada, Modelo, PalavraTemporizada } from "./state";
import { CampoParticulasTexto, type OpcoesCampoTexto } from "./text-particle-field";

/** Relógio da mídia: estado e chegada da timeline não fazem a locução avançar. */
export class RelogioFala {
  /**
   * `idadeMaxima`: amostra mais velha que isso (ms) não vale (a palavra some);
   * `extrapolacaoMaxima`: quanto o relógio avança sozinho desde a última amostra (ms).
   */
  // Medido em tests/relogio-medicao.test.ts (docs/HOMOLOGACAO.md): 450/400 não perde palavras
  // com engasgos de até 450 ms e mantém o atraso p95 em 50 ms.
  constructor(readonly idadeMaxima = 450, readonly extrapolacaoMaxima = 400) {}
  /** Recuos menores que isso (ms) são ruído de rede: a posição não volta (sem piscar). */
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
    // RAF pode preceder a chegada SSE dentro do mesmo frame: jamais voltar o relógio.
    const decorrido = Math.max(0, agora - this.recebida);
    if (!a?.ativo || !fala || fala.id !== a.reproducao_id || decorrido > this.idadeMaxima || a.rms < .002) return null;
    let posicao = Math.min(a.duracao_ms || fala.duracao_ms, a.posicao_ms + Math.min(decorrido, this.extrapolacaoMaxima));
    // Amostra nova chega com o atraso da rede e "puxa" a posição alguns ms para trás: ignora.
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
  /** Há amostra recente da reprodução desta fala (entre palavras ou numa pausa curta). */
  ativo(fala: FalaTemporizada | null, agora: number) {
    const a = this.amostra;
    return !!(a?.ativo && fala && fala.id === a.reproducao_id && agora - this.recebida <= this.idadeMaxima);
  }
}

/** A palavra fica até a próxima começar, inclusive nas pausas, até este teto (silêncio longo). */
export const TETO_PAUSA_MS = 1500;
/**
 * Movimento das palavras: tremor leve (soltar pontos atrapalharia a leitura) e chegada rápida da
 * poeira. Medido em tests/text-particles.test.ts: legível (90% dos pontos a < 3 px) em ~116 ms,
 * meta ≤ 150 ms.
 */
export const VIDA_PALAVRAS = { tremor: .45, chegada: 30, rigidezChegada: 80 };
/** Quantas palavras já ditas ficam visíveis à esquerda da atual. */
export const ANTERIORES = 3;

/** Um único glifo semântico por vez; as mesmas partículas fazem a transição e a dissolução. */
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
  /** Teto da retenção nas pausas (ms); configurável. */
  tetoPausa = TETO_PAUSA_MS;
  /** Palavras já ditas desta fala (só as que já tocaram; nunca as próximas). */
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
    if (d.id < this.maiorId || d.id <= this.encerrado) return; // aviso antigo ou repetido
    // Fim da reprodução (natural ou interrompida): a palavra some na hora, sem segurar.
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
