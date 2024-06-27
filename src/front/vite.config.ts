import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import * as path from "path";
import babel from 'vite-plugin-babel';
import vitePluginRaw from 'vite-plugin-raw';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // babel({
    //   babelConfig: {
    //     babelrc: false,
    //     configFile: false,
    //     presets: ["@babel/preset-env"],
    //     plugins: ['transform-commonjs']
    //   },
    //   include: ['node_modules/chor-js/**/*'],
    // }),
    vitePluginRaw({
      match: /\.bpmn$/, // 匹配 .bpmn 文件
    })
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
  },
  assetsInclude: ['**/*.bpmn'] // 确保 Vite 识别 .bpmn 文件
});
