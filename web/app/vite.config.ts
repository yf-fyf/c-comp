/// <reference types="vitest/config" />
import { resolve } from "node:path";
import { defineConfig } from "vite";

// base "./" — GitHub Pages のサブパス配下でも動くよう相対参照にする
export default defineConfig({
  base: "./",
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        ast: resolve(__dirname, "ast.html"),
        sim: resolve(__dirname, "sim.html"),
      },
    },
  },
  test: {
    environment: "node",
    // qemu 照合は重いので分ける（npm run test:qemu）
    exclude: ["node_modules/**", "test/qemu-conformance.ts"],
  },
});
