import {
  desconectar,
  inicial,
  limiteEvento,
  objeto,
  reduzir,
  snapshot,
  type Evento,
  type Modelo,
} from "./state";
/** SSE só recebe eventos; comandos explícitos usam POST autenticado na mesma origem. */
export class Ponte {
  modelo = { ...inicial };
  private fonte?: EventSource;
  private tentativa = 0;
  private timer?: ReturnType<typeof setTimeout>;
  private fechada = false;
  private token = "";
  constructor(private atualizar: (modelo: Modelo, evento?: Evento) => void) {}
  async iniciar() {
    this.fechada = false;
    try {
      const resposta = await fetch("/api/estado", { cache: "no-store" });
      if (!resposta.ok) throw new Error("Núcleo indisponível");
      const estado: unknown = await resposta.json();
      if (this.fechada) return;
      this.modelo = snapshot(estado);
      this.atualizar(this.modelo);
    } catch {
      this.desconectar();
    }
    if (!this.fechada) this.conectar();
  }
  private conectar() {
    if (this.fechada) return;
    this.fonte = new EventSource("/api/eventos");
    const receber = (e: MessageEvent<string>) => {
      try {
        if (new TextEncoder().encode(e.data).length > limiteEvento) return;
        const evento: unknown = JSON.parse(e.data);
        const novo = reduzir(this.modelo, evento);
        if (novo === this.modelo) return;
        this.modelo = novo;
        this.tentativa = 0;
        this.atualizar(this.modelo, evento as Evento);
      } catch {
        /* Um evento malformado nunca derruba a interface. */
      }
    };
    this.fonte.onmessage = receber;
    this.fonte.addEventListener("nora", receber as EventListener);
    this.fonte.onerror = () => {
      if (this.fechada) return;
      this.fonte?.close();
      this.desconectar();
      const espera = Math.min(30000, 1000 * 2 ** Math.min(this.tentativa++, 5));
      this.timer = setTimeout(() => this.conectar(), espera);
    };
  }
  private desconectar() {
    this.modelo = desconectar(this.modelo);
    this.atualizar(this.modelo);
  }
  private async sessao() {
    const r = await fetch("/api/sessao", { cache: "no-store" });
    if (!r.ok) throw new Error("Não foi possível validar a sessão local.");
    const sessao: unknown = await r.json();
    if (!objeto(sessao) || typeof sessao.token !== "string")
      throw new Error("Sessão local inválida.");
    this.token = sessao.token;
  }
  async comando(
    caminho: "decisao" | "privacidade",
    dados: Record<string, unknown>,
  ) {
    if (!this.token) await this.sessao();
    const enviar = () =>
      fetch(`/api/${caminho}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Nora-Token": this.token,
        },
        body: JSON.stringify(dados),
        cache: "no-store",
      });
    let r = await enviar();
    // Uma rejeição explícita de autenticação não executou a ação: renovar só uma vez.
    if (r.status === 403) {
      this.token = "";
      await this.sessao();
      r = await enviar();
    }
    if (!r.ok) {
      this.token = "";
      throw new Error("O núcleo não confirmou a alteração. Tente novamente.");
    }
    return r.json() as Promise<unknown>;
  }
  fechar() {
    this.fechada = true;
    clearTimeout(this.timer);
    this.fonte?.close();
    this.desconectar();
  }
}
