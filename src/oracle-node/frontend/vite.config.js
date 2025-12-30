import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/identities": "http://localhost:8010",
      "/compute-watchers": "http://localhost:8010",
      "/events": "http://localhost:8010",
      "/contracts": "http://localhost:8010",
      "/data-sources": "http://localhost:8010",
      "/local-chain": "http://localhost:8010"
    }
  }
});
