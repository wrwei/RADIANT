import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// Build output lands in ../web/static so FastAPI's existing `/` (index.html)
// and `/static` mount serve the bundle unchanged. Assets are referenced under
// /static/, matching the StaticFiles mount in web/server.py.
export default defineConfig({
  plugins: [vue()],
  base: "/static/",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    outDir: "../web/static",
    emptyOutDir: true,
    assetsDir: "assets",
  },
  server: {
    port: 5173,
    // Dev only: proxy API + WebSocket to the FastAPI backend on :8000.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
