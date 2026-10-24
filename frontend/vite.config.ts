// `defineConfig` comes from vitest/config so the `test` block typechecks.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { fileURLToPath, URL } from "node:url";

// The bundle is committed and served by the Python process from frontend/dist
// (backend/src/api/server.py). `npm run dev` proxies /api to the running app
// on 8890 -- never 8888, which is FOREX Trader.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
  server: {
    port: 5174,
    proxy: { "/api": { target: "http://127.0.0.1:8890", changeOrigin: false } },
  },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"], css: false },
});
