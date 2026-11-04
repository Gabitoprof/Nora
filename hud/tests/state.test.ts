import { describe, expect, it } from "vitest";
import contrato from "../../src/nora/hud_contrato.json";
import { aleatorio, onda } from "../src/scene-math";
import {
  cores,
  desconectar,
  eventoValido,
  inicial,
  reduzir,
  snapshot,
  type Evento,
} from "../src/state";
const evento = (tipo: string, dados = {}, sequencia = 2): Evento => ({
  versao: 1,
  sequencia,
  tipo,
  dados,
  instante: "2026-11-03T10:00:00",
});
describe("contrato compartilhado com o Python", () => {
  it("rejeita versões, tipos e amplitudes inválidas", () => {
    expect(eventoValido({ ...evento("ociosa"), versao: 2 })).toBe(false);
    expect(eventoValido(evento("tipo_desconhecido"))).toBe(false);
    for (const nivel of [-1, 1.01, Infinity, NaN, "0.5"])
      expect(eventoValido(evento("nivel_audio", { nivel }))).toBe(false);
    expect(
      eventoValido(evento("nivel_audio", { nivel: 0.7, fonte: "voz" })),
    ).toBe(true);
    expect(eventoValido({ ...evento("ociosa"), sequencia: -2 })).toBe(false);
    expect(eventoValido({ ...evento("ociosa"), dados: [] })).toBe(false);
  });
  it("cada tipo do contrato Python é reconhecido sem manter lista paralela", () => {
    for (const tipo of Object.keys(contrato.campos)) {
      const dados =
        tipo === "nivel_audio" ? { nivel: 0.5, fonte: "microfone" } : {};
      expect(eventoValido(evento(tipo, dados)), tipo).toBe(true);
    }
  });
  it("ignora eventos antigos e aceita snapshot após reinício", () => {
    const conectado = snapshot({ ...inicial, conectado: true, sequencia: 80 });
    expect(reduzir(conectado, evento("pensando", {}, 79))).toBe(conectado);
    const novo = reduzir(
      conectado,
      evento(
        "conectado",
        { ...inicial, estado: "ouvindo", conectado: true },
        1,
      ),
    );
    expect(novo.sequencia).toBe(1);
    expect(novo.estado).toBe("ouvindo");
  });
  it("conexão SSE não inventa núcleo ativo", () => {
    const novo = reduzir(
      inicial,
      evento("conectado", { ...inicial, conectado: false }),
    );
    expect(novo.conectado).toBe(false);
    expect(novo.estado).toBe("desconectado");
  });
  it("não acumula conteúdo pessoal enquanto a privacidade estiver ativa", () => {
    const oculto = reduzir(
      inicial,
      evento("texto_visivel", { texto: "texto pessoal" }),
    );
    expect(oculto.texto).toBe("");
    const novo = snapshot({
      ...inicial,
      privacidade: true,
      texto: "segredo",
      notas: [{ titulo: "pessoal" }],
    });
    expect(novo.texto).toBe("");
    expect(novo.notas).toEqual([]);
  });
  it("limita texto progressivo e apaga conteúdo ao ocultar/desconectar", () => {
    let m = { ...inicial, conectado: true, privacidade: false };
    m = reduzir(
      m,
      evento("texto_visivel", { texto: "Olá ", acumular: false }, 3),
    );
    m = reduzir(
      m,
      evento("texto_visivel", { texto: "mundo", acumular: true }, 4),
    );
    expect(m.texto).toBe("Olá mundo");
    const grande = reduzir(
      m,
      evento("texto_visivel", { texto: "x".repeat(7000), acumular: true }, 5),
    );
    expect(grande.texto.length).toBe(contrato.limite_texto);
    expect(
      reduzir(m, evento("privacidade", { privacidade: true }, 6)).texto,
    ).toBe("");
    expect(desconectar(m).texto).toBe("");
    expect(desconectar(m).nivel_audio).toBe(0);
  });
  it("preserva 6000 pontos Unicode sem cortar pares substitutos", () => {
    const emoji = "🌊".repeat(6000);
    const m = reduzir(
      { ...inicial, privacidade: false },
      evento("texto_visivel", { texto: emoji }, 3),
    );
    expect(m.texto).toBe(emoji);
    const proximo = reduzir(
      m,
      evento("texto_visivel", { texto: "fim", acumular: true }, 4),
    );
    expect(Array.from(proximo.texto)).toHaveLength(6000);
    expect(proximo.texto.endsWith("fim")).toBe(true);
  });
  it("atualiza modelo/voz/emoção só por eventos do núcleo", () => {
    let m = reduzir(
      inicial,
      evento("modelo_ativo", { modelo: "modelo real" }, 3),
    );
    m = reduzir(m, evento("voz_ativa", { motor: "piper" }, 4));
    m = reduzir(m, evento("emocao", { nome: "alegre" }, 5));
    expect(m.modelo).toBe("modelo real");
    expect(m.voz).toBe("piper");
    expect(m.emocao).toBe("alegre");
  });
});
describe("geometria e paleta visual", () => {
  it("onda deixa o centro vazio e não vira uma esfera preenchida", () => {
    for (let i = 0; i < 100; i++) {
      const [x, y, z] = onda((i / 100) * Math.PI * 2, 0.5, 0, "ociosa", 0);
      expect(Math.hypot(x, y)).toBeGreaterThan(2.5);
      expect(Number.isFinite(z)).toBe(true);
    }
  });
  it("amplitude real afeta a fala e modo jogo ignora esse nível", () => {
    expect(onda(0, 0.5, 0, "falando", 1)).not.toEqual(
      onda(0, 0.5, 0, "falando", 0),
    );
    expect(onda(0, 0.5, 0, "modo_jogo", 1)).toEqual(
      onda(0, 0.5, 0, "modo_jogo", 0),
    );
  });
  it("distribuição visual é determinística e emoções reais têm cores previstas", () => {
    expect(aleatorio(42)).toBe(aleatorio(42));
    expect(aleatorio(42)).toBeGreaterThanOrEqual(0);
    expect(aleatorio(42)).toBeLessThan(1);
    for (const emocao of [
      "alegre",
      "empolgada",
      "carinhosa",
      "calma",
      "seria",
      "triste",
      "curiosa",
      "sussurro",
      "risada",
      "suspiro",
      "neutra",
    ])
      expect(cores[emocao]).toMatch(/^#[A-Fa-f0-9]{6}$/);
  });
});
