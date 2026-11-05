import { createRequire } from "node:module";
import { describe, expect, it } from "vitest";

// A versão corrigida é resolvida a partir dos consumidores transitivos reais.
// Exercita as APIs de glob que o parser e o ESLint usam após o override de segurança.
const require = createRequire(import.meta.url);
const doTypeScriptESLint = createRequire(require.resolve("typescript-eslint"));
const doParser = createRequire(
  doTypeScriptESLint.resolve("@typescript-eslint/typescript-estree"),
);
const doESLint = createRequire(require.resolve("eslint"));

type Opcoes = { dot?: boolean; matchBase?: boolean };
type API = {
  minimatch: (caminho: string, padrao: string, opcoes?: Opcoes) => boolean;
  Minimatch: new (padrao: string, opcoes?: Opcoes) => {
    match: (caminho: string) => boolean;
  };
};

describe.each([
  ["typescript-eslint", doParser],
  ["eslint", doESLint],
] as const)("compatibilidade da correção minimatch em %s", (_nome, resolver) => {
  const api = resolver("minimatch") as API;

  it("mantém matching nominal, dotfiles e separação de extensões", () => {
    expect(api.minimatch("src/main.ts", "src/**/*.ts")).toBe(true);
    expect(api.minimatch("src/scene/render.ts", "src/**/*.ts")).toBe(true);
    expect(api.minimatch("src/main.js", "src/**/*.ts")).toBe(false);
    expect(api.minimatch("src/.interno.ts", "src/*.ts", { dot: true })).toBe(true);
    expect(api.minimatch("src/.interno.ts", "src/*.ts")).toBe(false);
  });

  it("mantém o construtor e os padrões utilizados na seleção de arquivos", () => {
    const matcher = new api.Minimatch("{src,tests}/**/*.{ts,tsx}", { dot: true });
    expect(matcher.match("tests/state.test.ts")).toBe(true);
    expect(matcher.match("src/components/card.tsx")).toBe(true);
    expect(matcher.match("docs/README.md")).toBe(false);
    const negado = new api.Minimatch("!docs/**", { dot: true });
    expect(negado.match("docs/README.md")).toBe(false);
    expect(negado.match("src/main.ts")).toBe(true);
  });
});
