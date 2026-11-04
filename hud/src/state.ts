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
    case "desconectado":
      proximo.conectado = false;
      proximo.nivel_audio = 0;
      proximo.texto = "";
      proximo.notas = [];
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
export const cores: Record<string, string> = {
  empolgada: "#F0C66A",
  risada: "#F0C66A",
  seria: "#80A8F6",
  triste: "#DF876A",
  sussurro: "#AA9ACF",
  suspiro: "#AA9ACF",
  neutro: "#C9C9C9",
  neutra: "#C9C9C9",
  alegria: "#F0C66A",
  alegre: "#F0C66A",
  acolhimento: "#E3A4BD",
  carinhosa: "#E3A4BD",
  curiosidade: "#66D4CB",
  curiosa: "#66D4CB",
  preocupacao: "#DF876A",
  preocupação: "#DF876A",
  preocupada: "#DF876A",
  confianca: "#80A8F6",
  confiança: "#80A8F6",
  confiante: "#80A8F6",
  serenidade: "#AA9ACF",
  calma: "#AA9ACF",
};

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
