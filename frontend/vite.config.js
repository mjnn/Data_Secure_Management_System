import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "..");

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, "");
  const appBase = env.VITE_APP_BASE || "/";

  return {
    base: appBase,
    plugins: [vue()],
    build: {
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes("node_modules/element-plus")) return "element-plus";
            if (id.includes("node_modules/echarts")) return "echarts";
            if (id.includes("node_modules/vue") || id.includes("node_modules/@vue")) return "vue-vendor";
            if (id.includes("node_modules/dompurify")) return "dompurify";
          }
        }
      }
    },
    test: {
      environment: "jsdom",
      include: ["src/**/*.test.js"]
    },
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
        },
        // 本地模拟 ECS 子路径时可设 VITE_APP_BASE=/tools/dsms/ 并走此代理
        ...(appBase !== "/"
          ? {
              [`${appBase.replace(/\/$/, "")}/api`]: {
                target: "http://127.0.0.1:8000",
                changeOrigin: true,
                rewrite: (p) => p.replace(new RegExp(`^${appBase.replace(/\/$/, "")}`), "")
              }
            }
          : {})
      }
    }
  };
});
