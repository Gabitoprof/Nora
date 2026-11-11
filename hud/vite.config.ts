import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { defineConfig } from "vite";

// HUD version and commit, written at build time, so acceptance records what was tested.
const pacote = JSON.parse(readFileSync(new URL("./package.json", import.meta.url), "utf-8"));
function commit(): string {
  if (process.env.NORA_COMMIT) return process.env.NORA_COMMIT.slice(0, 12);
  try {
    return execSync("git rev-parse --short HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return "desconhecido";
  }
}
export default defineConfig({
  define: {
    __VERSAO_NORA__: JSON.stringify(pacote.version),
    __COMMIT_NORA__: JSON.stringify(commit()),
  },
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8765",
        changeOrigin: true,
        configure(proxy) {
          proxy.on("proxyReq", (proxyReq, req) => {
            if (req.headers.origin === `http://${req.headers.host}`)
              proxyReq.setHeader("Origin", "http://127.0.0.1:8765");
          });
        },
      },
    },
  },
  build: { target: "es2022", rollupOptions: { output: { manualChunks: { three: ["three"] } } } },
});
