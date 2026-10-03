/// <reference types="vitest/config" />
import { resolve } from "node:path";
import { defineConfig } from "vite";

// base "./" — GitHub Pages のサブパス配下でも動くよう相対参照にする
export default defineConfig({
  base: "./",
  build: {
    outDir: "dist",
    // app.html は CodeMirror + d3-hierarchy を含む単一ページアプリで、
    // 構造・命令・実行が同じ作業状態を共有するため分割点がない。
    // gzip後は185kB程度で実害もないため、閾値だけ上げる。
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        app: resolve(__dirname, "app.html"),
      },
    },
  },
  test: {
    environment: "node",
    // qemu 照合は重いので分ける（npm run test:qemu）
    exclude: ["node_modules/**", "test/qemu-conformance.ts"],
  },
});
