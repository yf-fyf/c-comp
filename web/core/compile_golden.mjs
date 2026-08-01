#!/usr/bin/env node
// golden_test.py の compile() 黄金テストの補助スクリプト。
//
// stdin から JSON 配列 [{ "path": string, "source": string }, ...] を読み、
// api.bc.js の myccCore.compile(source, false) を 1 プロセス内で順に呼ぶ。
// 対象ファイルは 100 件を超えるため、ファイルごとに `node -e` を起動するより
// 1 プロセスに詰め込むほうが速く、失敗モードも単純（起動コストのゆらぎがない）。
//
// 出力は 1 件 1 行の JSON（{ "path", "ok", "text" }）を stdout に流す。
// text は ok=false のとき null。

import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";

const require = createRequire(import.meta.url);
const here = path.dirname(fileURLToPath(import.meta.url));
const apiPath = path.join(here, "_build", "default", "js", "api.bc.js");
const { myccCore } = require(apiPath);

function readStdin() {
  return new Promise((resolve, reject) => {
    let input = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => (input += chunk));
    process.stdin.on("end", () => resolve(input));
    process.stdin.on("error", reject);
  });
}

const input = await readStdin();
const items = JSON.parse(input);

for (const { path: p, source } of items) {
  let out;
  try {
    const result = JSON.parse(myccCore.compile(source, false));
    out = { path: p, ok: !!result.ok, text: result.ok ? result.text : null };
  } catch (e) {
    out = { path: p, ok: false, text: null };
  }
  process.stdout.write(JSON.stringify(out) + "\n");
}
