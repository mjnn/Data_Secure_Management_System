import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");

export default defineConfig({
  base: process.env.VITE_APP_BASE || "/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@dsms-ref": path.join(repoRoot, "ref")
    }
  },
  server: {
    port: 5173,
    fs: {
      allow: [repoRoot]
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true
      }
    }
  }
});
