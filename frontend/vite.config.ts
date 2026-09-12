import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const API_PROXY_TARGET = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
      "/health": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
      "/ready": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
});
