import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    // Local dev: output next to the Python static dir so FastAPI serves it immediately.
    // Override with VITE_OUT_DIR env var (used in Dockerfile: VITE_OUT_DIR=dist).
    outDir: process.env.VITE_OUT_DIR ?? "../src/confscraper/web/static",
    emptyOutDir: true,
  },
});
