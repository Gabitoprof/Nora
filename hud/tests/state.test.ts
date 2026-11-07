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
        tipo === "nivel_audio" ? { nivel: 0.5, fonte: "microfone" } : tipo === "acustica" ? {fonte:"voz",rms:.2,pico:.3,envelope:.2,bandas:[0,0,0,0,0,0],centroide:.1,fluxo:0,ativo:true,reproducao_id:1,posicao_ms:0,duracao_ms:100} : tipo === "fala_temporizada" ? {id:1,duracao_ms:100,precisao:"estimada",palavras:[{texto:"Olá",inicio_ms:0,fim_ms:100,destaque:false}]} : tipo === "modo_jogo_ativo" ? {ativo:true} : {};
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

describe("reproducao_encerrada no estado da HUD", () => {
  const fala = (id: number) => ({ id, duracao_ms: 1000, precisao: "alinhada", palavras: [{ texto: "oi", inicio_ms: 0, fim_ms: 200, destaque: false }] });
  const voz = (id: number, ativo = true) => ({ fonte: "voz", rms: .2, pico: .3, envelope: .2, bandas: [0, 0, 0, 0, 0, 0], centroide: 0, fluxo: 0, ativo, reproducao_id: id, posicao_ms: 100, duracao_ms: 1000 });
  const fim = (id: number, seq: number, interrompida = false) => evento("reproducao_encerrada", { id, posicao_ms: 1000, duracao_ms: 1000, interrompida }, seq);
  const visivel = () => {
    let m = reduzir(inicial, evento("conectado", { conectado: true, privacidade: false }, 1));
    m = reduzir(m, evento("acustica", voz(4), 2));
    return reduzir(m, evento("fala_temporizada", fala(4), 3));
  };
  it("o fim apaga a fala daquela reprodução e o sinal da voz", () => {
    const m = reduzir(visivel(), fim(4, 4));
    expect(m.fala_temporizada).toBeNull(); expect(m.encerrada).toBe(4);
    expect(m.acustica?.ativo).toBe(false); expect(m.nivel_audio).toBe(0);
  });
  it("ordem: fim de uma reprodução antiga não apaga a fala atual; fora de ordem é ignorado", () => {
    let m = reduzir(visivel(), fim(3, 4));
    expect(m.fala_temporizada?.id).toBe(4);
    m = reduzir(m, fim(4, 2)); // sequência velha
    expect(m.fala_temporizada?.id).toBe(4);
  });
  it("duplicidade: o mesmo fim repetido não muda nada", () => {
    const a = reduzir(visivel(), fim(4, 4));
    const b = reduzir(a, fim(4, 5));
    expect(b.encerrada).toBe(4); expect(b.fala_temporizada).toBeNull();
    expect(reduzir(a, fim(4, 4))).toBe(a);
  });
  it("mensagem atrasada não reintroduz a fala de uma reprodução encerrada", () => {
    let m = reduzir(visivel(), fim(4, 4));
    m = reduzir(m, evento("fala_temporizada", fala(4), 5));
    expect(m.fala_temporizada).toBeNull();
    m = reduzir(m, evento("fala_temporizada", fala(5), 6)); // a próxima resposta aparece
    expect(m.fala_temporizada?.id).toBe(5);
  });
  it("reconexão: o servidor pode ter reiniciado, os ids voltam a valer", () => {
    let m = reduzir(visivel(), fim(4, 4));
    m = reduzir(m, evento("conectado", { conectado: true, privacidade: false }, 1));
    expect(m.encerrada).toBe(0);
    m = reduzir(m, evento("fala_temporizada", fala(1), 2));
    expect(m.fala_temporizada?.id).toBe(1);
  });
  it("Privado: mensagem atrasada não reintroduz texto depois de ocultar", () => {
    let m = reduzir(visivel(), evento("privacidade", { privacidade: true }, 4));
    expect(m.fala_temporizada).toBeNull();
    m = reduzir(m, evento("fala_temporizada", fala(4), 5));
    m = reduzir(m, evento("texto_visivel", { texto: "segredo", acumular: false }, 6));
    m = reduzir(m, evento("notas", { notas: [{ titulo: "nota" }] }, 7));
    expect(m.fala_temporizada).toBeNull(); expect(m.texto).toBe(""); expect(m.notas).toEqual([]);
    m = reduzir(m, fim(4, 8)); // o fim chega depois: continua tudo limpo
    expect(m.fala_temporizada).toBeNull();
  });
});
