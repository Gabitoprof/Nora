import paleta from "../../src/nora/paleta.json";
import type { Acustica } from "./scene-audio";
import contrato from "../../src/nora/hud_contrato.json";
/** Contrato v1 compartilhado com o núcleo Python. */
export type Estado =
  | "conectado"
  | "desconectado"
  | "ociosa"
  | "ouvindo"
  | "fala_detectada"
  | "transcrevendo"
  | "pensando"
  | "falando"
  | "modo_jogo"
  | "erro"
  | "recuperando";
export const estados: readonly Estado[] = [
  ...contrato.estados,
  "conectado",
] as Estado[];
export const limiteEvento = contrato.limite_evento;
export type Dados = Record<string, unknown>;
export interface Evento {
  versao: 1;
  sequencia: number;
  tipo: string;
  dados: Dados;
  instante: string;
}
export interface Proposta {
  id: number;
  titulo: string;
  status: string;
  prioridade?: string;
}
export interface Nota {
  titulo: string;
  caminho?: string;
}
export interface Relatorio {
  data: string;
  propostas?: number;
}
export interface PalavraTemporizada { texto: string; inicio_ms: number; fim_ms: number; destaque: boolean; }
export interface FalaTemporizada { id: number; duracao_ms: number; precisao: "estimada" | "alinhada"; palavras: PalavraTemporizada[]; }
const finito = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const unitario = (v: unknown): v is number => finito(v) && v >= 0 && v <= 1;
export function lerAcustica(v: unknown): Acustica | null {
  if (!objeto(v) || !["microfone","voz"].includes(String(v.fonte)) || ![v.rms,v.pico,v.envelope,v.centroide,v.fluxo].every(unitario) || !Array.isArray(v.bandas) || v.bandas.length !== 6 || !v.bandas.every(unitario) || typeof v.ativo !== "boolean" || !Number.isSafeInteger(v.reproducao_id) || Number(v.reproducao_id)<0 || !finito(v.posicao_ms) || v.posicao_ms<0 || !finito(v.duracao_ms) || v.duracao_ms<0 || v.duracao_ms>contrato.acustica.max_duracao_ms || v.posicao_ms>v.duracao_ms) return null;
  if(v.fonte==="microfone" && (v.reproducao_id!==0||v.posicao_ms!==0||v.duracao_ms!==0))return null;
  return {...v,bandas:[...v.bandas]} as unknown as Acustica;
}
export function lerFala(v: unknown): FalaTemporizada | null {
  if(!objeto(v)||!Number.isSafeInteger(v.id)||Number(v.id)<1||!finito(v.duracao_ms)||v.duracao_ms<=0||v.duracao_ms>contrato.acustica.max_duracao_ms||!["estimada","alinhada"].includes(String(v.precisao))||!Array.isArray(v.palavras)||v.palavras.length===0||v.palavras.length>contrato.fala_temporizada.limite_palavras) return null;
  let fim=0, total=0;
  for(const p of v.palavras) {
    if(!objeto(p)||typeof p.texto!=="string"||Array.from(p.texto).length>contrato.fala_temporizada.limite_palavra||!p.texto.trim()||!finito(p.inicio_ms)||!finito(p.fim_ms)||p.inicio_ms<fim||p.fim_ms<=p.inicio_ms||p.fim_ms>v.duracao_ms||typeof p.destaque!=="boolean") return null;
    fim=p.fim_ms;total+=Array.from(p.texto).length;
  }
  if(total>contrato.limite_texto) return null;
  return {...v,palavras:v.palavras.map(p=>({...p}))} as unknown as FalaTemporizada;
}
export interface Modelo {
  versao: 1;
  sequencia: number;
  estado: Estado;
  conectado: boolean;
  nome: string;
  modelo: string;
  origem: string;
  voz: string;
  emocao: string;
  nivel_audio: number;
  texto: string;
  privacidade: boolean;
  notas: Nota[];
  relatorio: Relatorio | null;
  latencia_ms?: number;
  acustica: Acustica | null;
  fala_temporizada: FalaTemporizada | null;
  jogo: boolean;
}
export const inicial: Modelo = {
  versao: 1,
  sequencia: -1,
  estado: "desconectado",
  conectado: false,
  nome: "Nora",
  modelo: "",
  origem: "",
  voz: "",
  emocao: "neutro",
  nivel_audio: 0,
  texto: "",
  privacidade: true,
  notas: [],
  relatorio: null,
  acustica: null,
  fala_temporizada: null,
  jogo: false,
};
export function objeto(dado: unknown): dado is Dados {
  return dado !== null && typeof dado === "object" && !Array.isArray(dado);
}
const limitarTexto = (dado: string, fim = false) =>
  Array.from(dado)
    .slice(
      fim ? -contrato.limite_texto : 0,
      fim ? undefined : contrato.limite_texto,
    )
    .join("");
const texto = (dado: unknown, padrao = "") =>
  typeof dado === "string" ? limitarTexto(dado) : padrao;
export function eventoValido(dado: unknown): dado is Evento {
  if (
    !objeto(dado) ||
    dado.versao !== 1 ||
    !Number.isSafeInteger(dado.sequencia) ||
    Number(dado.sequencia) < 0 ||
    typeof dado.tipo !== "string" ||
    !objeto(dado.dados) ||
    typeof dado.instante !== "string"
  )
    return false;
  if (dado.tipo === "acustica") return lerAcustica(dado.dados) !== null;
  if (dado.tipo === "fala_temporizada") return lerFala(dado.dados) !== null;
  if (dado.tipo === "modo_jogo_ativo") return typeof dado.dados.ativo === "boolean";
  if (dado.tipo === "nivel_audio")
    return (
      typeof dado.dados.nivel === "number" &&
      Number.isFinite(dado.dados.nivel) &&
      dado.dados.nivel >= 0 &&
      dado.dados.nivel <= 1
    );
  return Object.hasOwn(contrato.campos, dado.tipo);
}
export function snapshot(dados: unknown, anterior: Modelo = inicial): Modelo {
  if (!objeto(dados) || dados.versao !== 1) return anterior;
  const privado = dados.privacidade !== false;
  return {
    ...anterior,
    versao: 1,
    sequencia: Number.isSafeInteger(dados.sequencia)
      ? Number(dados.sequencia)
      : anterior.sequencia,
    estado: estados.includes(dados.estado as Estado)
      ? (dados.estado as Estado)
      : anterior.estado,
    conectado: dados.conectado === true,
    nome: texto(dados.nome, anterior.nome),
    modelo: texto(dados.modelo),
    origem: texto(dados.origem),
    voz: texto(dados.voz),
    emocao: texto(dados.emocao, "neutro"),
    privacidade: privado,
    acustica: dados.conectado === true ? lerAcustica(dados.acustica) : null,
    fala_temporizada: privado || dados.conectado !== true ? null : lerFala(dados.fala_temporizada),
    jogo: dados.jogo === true,
    nivel_audio:
      typeof dados.nivel_audio === "number" &&
      Number.isFinite(dados.nivel_audio)
        ? Math.min(1, Math.max(0, dados.nivel_audio))
        : 0,
    texto: privado ? "" : texto(dados.texto),
    notas:
      !privado && Array.isArray(dados.notas)
        ? dados.notas
            .filter((n): n is Nota => objeto(n) && typeof n.titulo === "string")
            .slice(0, 12)
        : [],
    latencia_ms:
      typeof dados.latencia_ms === "number" ? dados.latencia_ms : undefined,
    relatorio:
      objeto(dados.relatorio) && typeof dados.relatorio.data === "string"
        ? (dados.relatorio as unknown as Relatorio)
        : null,
  };
}
export function reduzir(anterior: Modelo, evento: unknown): Modelo {
  if (!eventoValido(evento)) return anterior;
  if (evento.tipo === "conectado")
    return snapshot(
      {
        ...evento.dados,
        versao: 1,
        sequencia: evento.sequencia,
        conectado: evento.dados.conectado === true,
      },
      anterior,
    );
  if (evento.sequencia <= anterior.sequencia) return anterior;
  const proximo = { ...anterior, sequencia: evento.sequencia };
  if (evento.tipo === "latencia" && typeof evento.dados.ms === "number")
    proximo.latencia_ms = evento.dados.ms;
  const d = evento.dados;
  if (estados.includes(evento.tipo as Estado))
    proximo.estado = evento.tipo as Estado;
  switch (evento.tipo) {
    case "acustica":
      proximo.acustica = lerAcustica(d);
      proximo.nivel_audio=proximo.acustica?.ativo?proximo.acustica.rms:0;
      if(proximo.acustica?.fonte === "voz" && !proximo.acustica.ativo) proximo.fala_temporizada=null;
      break;
    case "fala_temporizada":
      if(!proximo.privacidade && proximo.conectado) proximo.fala_temporizada=lerFala(d);
      break;
    case "modo_jogo_ativo":
      proximo.jogo=d.ativo===true;
      break;
    case "desconectado":
      proximo.conectado = false;
      proximo.nivel_audio = 0;
      proximo.texto = "";
      proximo.notas = [];
      proximo.acustica = null;
      proximo.fala_temporizada = null;
      break;
    case "nivel_audio":
      proximo.nivel_audio = Number(d.nivel);
      break;
    case "emocao":
      proximo.emocao = texto(d.nome, "neutro");
      break;
    case "modelo_ativo":
      proximo.modelo = texto(d.modelo);
      break;
    case "origem_resposta":
      proximo.origem = texto(d.origem);
      if (typeof d.latencia_ms === "number")
        proximo.latencia_ms = d.latencia_ms;
      break;
    case "voz_ativa":
      proximo.voz = texto(d.motor);
      break;
    case "texto_visivel":
      if (!proximo.privacidade)
        proximo.texto = limitarTexto(
          d.acumular === true
            ? anterior.texto + texto(d.texto)
            : texto(d.texto),
          true,
        );
      break;
    case "privacidade":
      proximo.privacidade = d.privacidade !== false;
      if (proximo.privacidade) {
        proximo.texto = "";
        proximo.notas = [];
        proximo.fala_temporizada = null;
      }
      break;
    case "relatorio_pronto":
      if (typeof d.data === "string")
        proximo.relatorio = {
          data: d.data,
          propostas: typeof d.propostas === "number" ? d.propostas : undefined,
        };
      break;
    case "notas":
      if (!proximo.privacidade && Array.isArray(d.notas))
        proximo.notas = d.notas
          .filter((n): n is Nota => objeto(n) && typeof n.titulo === "string")
          .slice(0, 12);
      break;
  }
  if (["ociosa","desconectado","erro","recuperando"].includes(evento.tipo)) proximo.fala_temporizada=null;
  return proximo;
}
export function desconectar(anterior: Modelo): Modelo {
  return {
    ...anterior,
    conectado: false,
    estado: "desconectado",
    texto: "",
    notas: [],
    nivel_audio: 0,
    acustica: null,
    fala_temporizada: null,
  };
}
export const nomesEstado: Record<Estado, string> = {
  conectado: "Conectada",
  desconectado: "Aguardando conexão",
  ociosa: "Em repouso",
  ouvindo: "Ouvindo você",
  fala_detectada: "Fala detectada",
  transcrevendo: "Transcrevendo",
  pensando: "Pensando",
  falando: "Falando com você",
  modo_jogo: "Modo jogo",
  erro: "Atenção necessária",
  recuperando: "Reconectando",
};
/** Base da identidade dark: branco-prateado com ciano discreto. */
export const PRATA = "#C9D6DC";
/** Quanto da cor da emoção entra no prata (o resto é prata): a emoção vira um matiz, não a cor. */
export const MATIZ_EMOCAO = 0.2;
/** Mistura linear de duas cores hex (#RRGGBB). */
export function misturar(base: string, cor: string, peso: number): string {
  const canal = (hex: string, i: number) => parseInt(hex.slice(1 + i * 2, 3 + i * 2), 16);
  return "#" + [0, 1, 2].map(i => Math.round(canal(base, i) * (1 - peso) + canal(cor, i) * peso)
    .toString(16).padStart(2, "0")).join("").toUpperCase();
}
/** Cores das emoções vêm da fonte única (src/nora/paleta.json, a mesma do Second Brain); na HUD
 * elas aparecem contidas no prata, para manter o visual dark aprovado. */
export const coresDaEmocao: Record<string,string> = Object.fromEntries(Object.entries(paleta.aliases).map(([nome,grupo])=>[nome,paleta.cores[grupo as keyof typeof paleta.cores]]));
export const cores: Record<string,string> = Object.fromEntries(Object.entries(coresDaEmocao).map(([nome,cor])=>[nome,misturar(PRATA,cor,MATIZ_EMOCAO)]));

/** RMS linear (0–1) em escala de decibéis: −60 dBFS = 0, 0 dBFS = 1. Fala comum (RMS 0,005 a
 * 0,1) fica entre 23% e 67%, em vez de 0% a 10% na escala linear. */
export function nivelPerceptivo(rms: number): number {
  if (!(rms > 0)) return 0;
  return Math.min(1, Math.max(0, (20 * Math.log10(rms) + 60) / 60));
}
/** Mesma regra da onda central (scene-math `onda`): o microfone só conta enquanto ela escuta e
 * a voz só enquanto ela fala. Fora disso (pensando, repouso), a última medida não vale mais. */
function sinalDaOnda(m: Modelo): number {
  const escutando = m.estado === "ouvindo" || m.estado === "fala_detectada";
  const a = m.acustica;
  if (a?.ativo)
    return (a.fonte === "microfone" && escutando) || (a.fonte === "voz" && m.estado === "falando")
      ? Math.max(a.rms, a.envelope)
      : 0;
  return escutando || m.estado === "falando" ? m.nivel_audio : 0;
}
/** O que o painel lateral mostra. Usa o mesmo sinal que move a onda central: a medida acústica
 * da fonte em uso (RMS ou envelope, o maior, como a onda, que segura o envelope na soltura).
 * Com sinal, nunca mostra "0%" nem "Em silêncio" (antes, RMS 0,004 virava "0%" enquanto a onda
 * já se mexia); sem a onda reagir (pensando, repouso), não mostra nível antigo. */
export function leituraDoPainel(m: Modelo): { nivel: number; rotulo: string } {
  if (!m.conectado) return { nivel: 0, rotulo: "Sem dados" };
  const sinal = sinalDaOnda(m);
  const nivel = nivelPerceptivo(sinal);
  if (!(sinal > 0)) return { nivel: 0, rotulo: "Em silêncio" };
  const porcento = Math.round(nivel * 100);
  return { nivel, rotulo: porcento < 1 ? "<1%" : `${porcento}%` };
}
export function expressaoEmocional(emocao:string) {
  const grupo=paleta.aliases[emocao as keyof typeof paleta.aliases]??"neutra";
  return paleta.dinamica[grupo as keyof typeof paleta.dinamica];
}

/** A resposta HTTP é snapshot autoritativo, mesmo se o SSE já aplicou a decisão. */
export function privacidadeConfirmada(
  anterior: Modelo,
  resposta: unknown,
): Modelo {
  if (!objeto(resposta) || resposta.versao !== 1)
    throw new Error("O núcleo retornou uma resposta inválida.");
  // SSE pode ter entregue a confirmação e novos tokens antes do HTTP terminar.
  // Nesse caso a resposta HTTP é somente um recibo antigo, não um novo estado.
  if (anterior.conectado && typeof resposta.sequencia === "number" && resposta.sequencia < anterior.sequencia) return anterior;
  return snapshot(resposta, anterior);
}
