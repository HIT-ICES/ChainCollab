import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import * as path from "path";
// import styleImport, { AntdResolve } from "vite-plugin-style-import";
import babel from 'vite-plugin-babel';
import commonjs from '@rollup/plugin-commonjs';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // commonjs(),
    // babel({
    //   include: ['/node_modules/chor-js/'],
    // })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      '~': path.resolve(__dirname, './'),
    },
  },
  server: {
    fs: {
      cachedChecks: false
    }
  }
});
