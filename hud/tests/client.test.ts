import { afterEach, describe, expect, it, vi } from "vitest";
import { Ponte } from "../src/client";
import {
  inicial,
  privacidadeConfirmada,
  reduzir,
  type Evento,
} from "../src/state";
afterEach(() => vi.unstubAllGlobals());
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
describe("decisões e reconexão autenticadas", () => {
  it("não inverte consentimento quando SSE chegou antes da confirmação HTTP", () => {
    const base = { ...inicial, conectado: true, privacidade: true };
    const e: Evento = {
      versao: 1,
      sequencia: 4,
      tipo: "privacidade",
      dados: { privacidade: false },
      instante: "2026-11-03",
    };
    const sse = reduzir(base, e);
    expect(sse.privacidade).toBe(false);
    const confirmado = privacidadeConfirmada(sse, {
      ...sse,
      privacidade: false,
    });
    expect(confirmado.privacidade).toBe(false);
    const oculto = privacidadeConfirmada(
      { ...confirmado, texto: "pessoal" },
      { ...confirmado, privacidade: true, texto: "pessoal" },
    );
    expect(oculto.texto).toBe("");
    expect(oculto.notas).toEqual([]);
    expect(() =>
      privacidadeConfirmada(inicial, { erro: "sem snapshot" }),
    ).toThrow();
  });
  it("preserva texto e fala SSE mais novos que a resposta HTTP de consentimento", () => {
    const recibo = {...inicial, conectado:true, privacidade:false, sequencia:4};
    const novo = {...recibo, sequencia:6, texto:"Resposta real", estado:"falando" as const};
    expect(privacidadeConfirmada(novo,recibo)).toBe(novo);
    expect(privacidadeConfirmada(novo,recibo).texto).toBe("Resposta real");
  });
  it("renova token depois de reinício e repete somente após rejeição explícita 403", async () => {
    const requests: { url: string; headers: HeadersInit | undefined }[] = [];
    let sessoes = 0,
      posts = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        requests.push({ url, headers: init?.headers });
        if (url === "/api/sessao")
          return json({ token: ++sessoes === 1 ? "antigo" : "novo" });
        return ++posts === 1
          ? json({ erro: "token antigo" }, 403)
          : json({ ...inicial, privacidade: false });
      }),
    );
    const ponte = new Ponte(() => {});
    const resposta = await ponte.comando("privacidade", { visivel: true });
    expect(resposta).toMatchObject({ privacidade: false });
    expect(sessoes).toBe(2);
    expect(posts).toBe(2);
    expect(requests.map((r) => r.url)).toEqual([
      "/api/sessao",
      "/api/privacidade",
      "/api/sessao",
      "/api/privacidade",
    ]);
    expect(requests[3].headers).toMatchObject({ "X-Nora-Token": "novo" });
  });
  it("não repete uma decisão em falha ambígua da aplicação", async () => {
    const fetch = vi.fn(async (url: string) =>
      url === "/api/sessao"
        ? json({ token: "teste" })
        : json({ erro: "falhou" }, 500),
    );
    vi.stubGlobal("fetch", fetch);
    const ponte = new Ponte(() => {});
    await expect(
      ponte.comando("decisao", { id: 1, acao: "aprovar", confirmar: true }),
    ).rejects.toThrow("não confirmou");
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
