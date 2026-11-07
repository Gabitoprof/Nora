import "./style.css";
import { Ponte } from "./client";
import { Cena } from "./scene";
import { PalavrasParticulas } from "./word-particles";
import { CampoParticulasTexto } from "./text-particle-field";
import { misturar } from "./state";
import {
  inicial,
  leituraDoPainel,
  nomesEstado,
  objeto,
  privacidadeConfirmada,
  type Modelo,
  type Proposta,
} from "./state";
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <main class="hud" aria-label="Interface da assistente Nora">
    <div class="frame frame-tl" aria-hidden="true"><i></i></div><div class="frame frame-tr" aria-hidden="true"><i></i></div>
    <div class="frame frame-bl" aria-hidden="true"><i></i></div><div class="frame frame-br" aria-hidden="true"><i></i></div>
    <header class="topbar">
      <div class="local"><span class="status-dot"></span><span id="connection">NÚCLEO DESCONECTADO</span></div>
      <div class="header-actions"><button id="privacy" class="icon-button" aria-pressed="false" title="Mostrar texto e notas nesta tela" aria-label="Mostrar texto e notas nesta tela"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/></svg><span id="privacy-label">Privado</span></button><button id="fullscreen" class="icon-button" aria-label="Alternar tela cheia" title="Alternar tela cheia"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5"/></svg></button><button id="settings-button" class="icon-button" aria-label="Ajustes da interface" aria-expanded="false" aria-controls="settings"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/></svg></button></div>
    </header>
    <div id="scene" class="scene" aria-hidden="true"></div>
    <div class="calibration" aria-hidden="true"><div class="outer-ring"></div><div class="ticks"></div><div class="ring-arc arc-one"></div><div class="ring-arc arc-two"></div><span class="axis axis-top"></span><span class="axis axis-bottom"></span><span class="axis axis-left"></span><span class="axis axis-right"></span></div>
    <section class="presence" aria-labelledby="assistant-name"><h1 id="assistant-name" class="sr-only">Nora</h1><canvas id="brand-particles" width="960" height="180" aria-hidden="true"></canvas><div class="state-label"><span class="state-line"></span><span id="state" role="status">Aguardando conexão</span><span class="state-line"></span></div></section>
    <div class="word-stage"><canvas id="word-particles" width="1200" height="140" aria-hidden="true" hidden></canvas><span id="word-caption" hidden></span></div>
    <aside class="side-panel system-panel" aria-labelledby="system-heading"><p class="panel-index">01 <span>SISTEMA</span></p><h2 id="system-heading">Conexão com o núcleo</h2><svg class="mini-wave" viewBox="0 0 220 70" aria-hidden="true"><g fill="none" stroke="currentColor"><path d="M0 38 Q30 10 58 38 T110 38 T160 38 T220 38"/><path d="M0 38 Q40 68 70 38 T140 38 T220 38"/><path d="M0 38 Q50 -6 80 38 T155 38 T220 38"/><path d="M0 38 Q30 52 65 38 T140 38 T220 38"/></g></svg><dl class="telemetry"><div><dt>Cérebro</dt><dd id="origin">—</dd></div><div><dt>Modelo</dt><dd id="model">—</dd></div><div><dt>Voz</dt><dd id="voice">—</dd></div><div><dt>Latência</dt><dd id="latency">—</dd></div></dl><div class="signal"><div class="signal-orbit" aria-hidden="true"><i></i><b></b></div><div><span class="micro-label">SINAL DE ÁUDIO</span><strong id="level-label">Sem dados</strong><div class="level-track" role="meter" aria-label="Nível de áudio real" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span id="level"></span></div></div></div></aside>
    <aside class="side-panel context-panel" aria-labelledby="context-heading"><p class="panel-index">02 <span>CONTEXTO</span></p><h2 id="context-heading">Tudo no seu tempo</h2><svg class="mini-constellation" viewBox="0 0 220 70" aria-hidden="true"><defs><pattern id="dust" width="9" height="7" patternUnits="userSpaceOnUse"><circle cx="2" cy="3" r="0.7" fill="currentColor"/></pattern></defs><path d="M0 55Q65 80 105 30T220 17V46Q155 25 110 50T0 65Z" fill="url(#dust)"/></svg><div class="context-row"><span class="small-dot"></span><div><strong id="report-label">Relatórios</strong><span id="report-status">Aguardando o núcleo</span></div><button id="open-improvements" class="text-button" aria-label="Ver melhorias supervisionadas">↗</button></div><div class="context-row"><span class="small-dot"></span><div><strong>Notas conectadas</strong><span id="notes-status">Conteúdo protegido</span></div><button id="open-notes" class="text-button" aria-label="Ver notas usadas na conversa">↗</button></div><p class="local-note">PRESENÇA LOCAL · CONTEÚDO PROTEGIDO</p></aside>
    <section class="response-card" aria-label="Resposta da Nora" hidden><div class="response-heading"><span>NA CONVERSA</span><span id="response-origin"></span></div><p id="response-text"></p></section>
    <footer class="bottom-bar"><div class="session-status"><span class="small-dot"></span><span id="session-label">Aguardando a Nora</span></div><div class="clock"><time id="clock">—</time><span id="date">—</span></div></footer>
    <section id="settings" class="settings floating-panel" aria-label="Ajustes visuais" hidden><h2>Ajustes da presença</h2><label>Qualidade<select id="quality"><option value="alta">Detalhada · WebGL</option><option value="baixa">Econômica · WebGL</option><option value="canvas">Leve · Canvas</option></select></label><label>Limite de quadros<select id="fps"><option value="30">30 FPS</option><option value="60">60 FPS</option><option value="120">120 FPS</option></select></label><label class="check-label"><input id="words" type="checkbox" autocomplete="off" checked/> Palavras em partículas</label><p>Palavras acompanham a reprodução. O tempo é estimado pela duração do áudio quando não há alinhamento. Com movimento reduzido, a palavra aparece sem animação.</p><p id="render-mode"></p><p id="versao" class="versao"></p></section>
    <dialog id="context-dialog" class="dialog floating-panel"><div class="dialog-header"><h2 id="dialog-title">Contexto</h2><button id="close-dialog" class="icon-button" aria-label="Fechar painel">×</button></div><div id="dialog-content"></div></dialog>
    <dialog id="confirm-dialog" class="dialog floating-panel"><h2>Confirmar decisão</h2><p id="confirm-description"></p><p>Aprovar gera apenas uma tarefa. Código e publicação continuam sob sua decisão.</p><div class="dialog-actions"><button id="cancel-decision" class="secondary-button">Cancelar</button><button id="confirm-decision" class="primary-button">Confirmar</button></div></dialog>
    <p id="feedback" class="feedback" role="status" hidden></p>
  </main>`;
const el = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const texto = (id: string, valor: string) => {
  el(id).textContent = valor;
};
const cena = new Cena(el("scene"));
texto("versao", `Nora ${__VERSAO_NORA__} · commit ${__COMMIT_NORA__}`);
let atual: Modelo = { ...inicial };
let visivel = false;
let ultimaProposta: { id: number; acao: string } | undefined;
const palavras=new PalavrasParticulas(el<HTMLCanvasElement>("word-particles"),el("word-caption"));
// Marca no alfabeto geométrico próprio (geometric-glyphs.ts), formada só por partículas.
const marca = new CampoParticulasTexto(el<HTMLCanvasElement>("brand-particles"), {
  largura: 960, altura: 180, maximo: 1500, estilo: "geometrico", espessura: 0.12, brilho: 0.3,
  escalaParticula: 1.7,
  // Viva: os pontos tremem, uns se soltam para a poeira e voltam; a voz aumenta tudo isso.
  vida: { tremor: 1.1, fluxo: .07, poeira: .16, extras: 320 },
  // Nasalization só se estiver instalada no Windows; senão, o alfabeto próprio (geometric-glyphs).
  fontesInstaladas: ["Nasalization", "Nasalization Rg", "Nasalization Regular"],
});
let nomeMarca = "";
const movimentoReduzido=matchMedia("(prefers-reduced-motion: reduce)");
cena.aoDesenhar=({agora,delta,cor,reduzido,energia})=>{
  document.documentElement.style.setProperty("--accent",cor);
  // Letras mais claras que a cena (branco-prateado com ciano), como na referência aprovada.
  const luz=misturar(cor.toUpperCase(),"#EEF9FF",.55);
  marca.desenhar(agora,delta,luz,reduzido,energia);
  palavras.desenhar(agora,luz,reduzido,delta,energia);
};
const ponte = new Ponte((modelo, evento) => {
  atual = modelo;
  if (evento) palavras.receberEvento(evento);
  renderizar();
  if (
    evento?.tipo === "proposta_melhoria" &&
    el<HTMLDialogElement>("context-dialog").open
  )
    void mostrarMelhorias();
});
function feedback(mensagem: string) {
  const p = el("feedback");
  p.textContent = mensagem;
  p.hidden = false;
  setTimeout(() => {
    p.hidden = true;
  }, 7000);
}
function renderizar() {
  el("app").dataset.estado = atual.estado;
  texto("assistant-name", atual.nome);
  const nome = atual.nome.toLocaleUpperCase("pt-BR");
  if (nome !== nomeMarca) {
    nomeMarca = nome;
    marca.definirTexto(nome, performance.now(), movimentoReduzido.matches);
    if (movimentoReduzido.matches) marca.desenhar(performance.now(), 0, "#c9d1d5", true);
  }
  texto("state", nomesEstado[atual.estado]);
  texto(
    "connection",
    atual.conectado ? "NÚCLEO CONECTADO" : "NÚCLEO DESCONECTADO",
  );
  el("connection").parentElement!.classList.toggle(
    "connected",
    atual.conectado,
  );
  texto("origin", atual.conectado ? atual.origem || "—" : "—");
  texto("model", atual.conectado ? atual.modelo || "—" : "—");
  texto("voice", atual.conectado ? atual.voz || "—" : "—");
  texto(
    "latency",
    atual.conectado && atual.latencia_ms !== undefined
      ? `${Math.round(atual.latencia_ms)} ms`
      : "—",
  );
  el("origin").title = atual.origem;
  el("model").title = atual.modelo;
  texto(
    "session-label",
    atual.conectado ? nomesEstado[atual.estado] : "Aguardando a Nora",
  );
  // Mesmo sinal da onda central, em escala de decibéis (ver leituraDoPainel).
  const painel = leituraDoPainel(atual);
  el("level").style.width = `${painel.nivel * 100}%`;
  el("level").parentElement!.setAttribute(
    "aria-valuenow",
    String(Math.round(painel.nivel * 100)),
  );
  texto("level-label", painel.rotulo);
  visivel = !atual.privacidade && atual.conectado;
  texto("privacy-label", visivel ? "Visível" : "Privado");
  el("privacy").setAttribute("aria-pressed", String(visivel));
  el("privacy").setAttribute(
    "aria-label",
    visivel
      ? "Ocultar texto e notas nesta tela"
      : "Mostrar texto e notas nesta tela",
  );
  const card = document.querySelector<HTMLElement>(".response-card")!;
  card.hidden = !visivel || !atual.texto;
  texto("response-text", visivel ? atual.texto : "");
  texto("response-origin", visivel ? atual.origem : "");
  texto(
    "report-status",
    !atual.conectado
      ? "Aguardando o núcleo"
      : atual.relatorio
        ? `Relatório de ${atual.relatorio.data}`
        : "Nenhum relatório pendente",
  );
  texto(
    "notes-status",
    !visivel
      ? "Conteúdo protegido"
      : atual.notas.length
        ? `${atual.notas.length} nota(s) nesta conversa`
        : "Nenhuma nota usada",
  );
  if (
    !visivel &&
    el<HTMLDialogElement>("context-dialog").open &&
    el("dialog-title").textContent === "Notas desta conversa"
  )
    el("dialog-content").replaceChildren();
  particulasPalavra();
  cena.atualizar(atual);
}
function clock() {
  const agora = new Date();
  texto(
    "clock",
    new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
    }).format(agora),
  );
  texto(
    "date",
    new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "long" })
      .format(agora)
      .toLocaleUpperCase("pt-BR"),
  );
}
function particulasPalavra() {
  palavras.atualizar(atual,el<HTMLInputElement>("words").checked,movimentoReduzido.matches);
}
movimentoReduzido.addEventListener("change",particulasPalavra);
el("privacy").addEventListener("click", async () => {
  if (!atual.conectado) {
    feedback("Conecte a HUD ao núcleo para alterar a privacidade.");
    return;
  }
  const botao = el<HTMLButtonElement>("privacy");
  botao.disabled = true;
  const mostrar = atual.privacidade;
  if (mostrar && !window.confirm("Mostrar temporariamente as palavras e notas nesta tela? Outras pessoas poderão vê-las. Nada será guardado no navegador.")) { botao.disabled = false; return; }
  if (!mostrar) {
    ponte.modelo = atual = {
      ...atual,
      privacidade: true,
      texto: "",
      notas: [],
      fala_temporizada: null,
    };
    renderizar();
    particulasPalavra();
  }
  try {
    const resposta = await ponte.comando("privacidade", { visivel: mostrar });
    ponte.modelo = atual = privacidadeConfirmada(atual, resposta);
    renderizar();
    particulasPalavra();
  } catch (erro) {
    feedback(
      erro instanceof Error ? erro.message : "Falha ao alterar privacidade.",
    );
  } finally {
    botao.disabled = false;
  }
});
el("fullscreen").addEventListener("click", () => {
  void (
    document.fullscreenElement
      ? document.exitFullscreen()
      : document.documentElement.requestFullscreen()
  ).catch(() => feedback("Tela cheia indisponível neste navegador."));
});
el("settings-button").addEventListener("click", () => {
  const painel = el("settings");
  painel.hidden = !painel.hidden;
  el("settings-button").setAttribute("aria-expanded", String(!painel.hidden));
  texto("render-mode", `Renderização atual: ${cena.motor}`);
});
const configurar = () => {
  cena.configurar(
    el<HTMLSelectElement>("quality").value as "alta" | "baixa" | "canvas",
    Number(el<HTMLSelectElement>("fps").value),
  );
  texto("render-mode", `Renderização atual: ${cena.motor}`);
};
el("quality").addEventListener("change", configurar);
el("fps").addEventListener("change", configurar);
el("words").addEventListener("change", particulasPalavra);
el("close-dialog").addEventListener("click", () =>
  el<HTMLDialogElement>("context-dialog").close(),
);
el("open-notes").addEventListener("click", async () => {
  texto("dialog-title", "Notas desta conversa");
  const conteudo = el("dialog-content");
  conteudo.replaceChildren();
  const p = document.createElement("p");
  p.textContent = !visivel
    ? "Ative a visibilidade para consultar apenas as notas usadas pelo núcleo nesta conversa."
    : atual.notas.length
      ? "Somente notas da pasta autorizada, efetivamente usadas na conversa."
      : "Nenhuma nota foi usada nesta conversa.";
  conteudo.append(p);
  if (visivel) {
    try {
      const r = await fetch("/api/notas", { cache: "no-store" });
      if (r.ok) {
        const d: unknown = await r.json();
        if (visivel && objeto(d) && Array.isArray(d.notas))
          atual.notas = d.notas
            .filter(
              (n): n is { titulo: string } =>
                objeto(n) && typeof n.titulo === "string",
            )
            .slice(0, 12);
      }
    } catch {
      p.textContent = "Não foi possível consultar as notas agora.";
    }
  }
  if (visivel)
    for (const nota of atual.notas) {
      const item = document.createElement("p");
      item.className = "note-card";
      item.textContent = nota.titulo;
      conteudo.append(item);
    }
  if (!el<HTMLDialogElement>("context-dialog").open)
    el<HTMLDialogElement>("context-dialog").showModal();
});
async function mostrarMelhorias() {
  texto("dialog-title", "Melhorias supervisionadas");
  const conteudo = el("dialog-content");
  conteudo.replaceChildren();
  const intro = document.createElement("p");
  intro.textContent =
    "Propostas do núcleo. Toda decisão exige sua confirmação; nenhuma ação altera código ou publica versões.";
  conteudo.append(intro);
  if (!atual.conectado) {
    intro.textContent = "Aguardando conexão com o núcleo.";
    return;
  }
  try {
    const r = await fetch("/api/propostas", { cache: "no-store" });
    if (!r.ok) throw new Error();
    const dados: unknown = await r.json();
    const propostas =
      objeto(dados) && Array.isArray(dados.propostas)
        ? dados.propostas.filter(
            (p): p is Proposta =>
              objeto(p) &&
              Number.isSafeInteger(p.id) &&
              typeof p.titulo === "string" &&
              typeof p.status === "string",
          )
        : [];
    if (!propostas.length) {
      const p = document.createElement("p");
      p.className = "empty-state";
      p.textContent = "Sem propostas para decidir.";
      conteudo.append(p);
    }
    for (const proposta of propostas) {
      const card = document.createElement("article");
      card.className = "proposal";
      const titulo = document.createElement("h3");
      titulo.textContent = `#${proposta.id} · ${proposta.titulo}`;
      card.append(titulo);
      const status = document.createElement("p");
      status.textContent = proposta.status;
      card.append(status);
      if (proposta.status === "proposta")
        for (const [acao, nome] of [
          ["aprovar", "Aprovar"],
          ["recusar", "Recusar"],
          ["adiar", "Adiar 7 dias"],
        ]) {
          const b = document.createElement("button");
          b.className = "secondary-button";
          b.textContent = nome;
          b.addEventListener("click", () => {
            ultimaProposta = { id: proposta.id, acao };
            texto("confirm-description", `${nome} a proposta #${proposta.id}?`);
            el<HTMLDialogElement>("confirm-dialog").showModal();
          });
          card.append(b);
        }
      conteudo.append(card);
    }
  } catch {
    const p = document.createElement("p");
    p.textContent = "Não foi possível consultar as propostas agora.";
    conteudo.append(p);
  }
}
el("open-improvements").addEventListener("click", () => {
  el<HTMLDialogElement>("context-dialog").showModal();
  void mostrarMelhorias();
});
el("cancel-decision").addEventListener("click", () => {
  ultimaProposta = undefined;
  el<HTMLDialogElement>("confirm-dialog").close();
});
el("confirm-decision").addEventListener("click", async () => {
  if (!ultimaProposta) return;
  const botao = el<HTMLButtonElement>("confirm-decision");
  botao.disabled = true;
  try {
    await ponte.comando("decisao", { ...ultimaProposta, confirmar: true });
    el<HTMLDialogElement>("confirm-dialog").close();
    ultimaProposta = undefined;
    feedback("Decisão registrada pelo núcleo.");
    await mostrarMelhorias();
  } catch (erro) {
    feedback(
      erro instanceof Error
        ? erro.message
        : "Não foi possível registrar a decisão.",
    );
  } finally {
    botao.disabled = false;
  }
});
clock();
const clockTimer = setInterval(clock, 1000);
renderizar();
void ponte.iniciar();
window.addEventListener("pagehide", () => {
  clearInterval(clockTimer);
  palavras.limpar();
  marca.limpar();
  movimentoReduzido.removeEventListener("change",particulasPalavra);
  ponte.fechar();
  cena.fechar();
});
