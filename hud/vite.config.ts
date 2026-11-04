import { defineConfig } from "vite";
export default defineConfig({
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
  build: { target: "es2022" },
});
