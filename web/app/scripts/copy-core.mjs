// OCaml コアのビルド成果物 (api.bc.js) を public/ へコピーする。
// dev/web/core で `dune build` を済ませてから実行する。
import { copyFileSync, mkdirSync, existsSync, rmSync, chmodSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = join(here, "../../core/_build/default/js/api.bc.js");
const dst = join(here, "../public/core/api.bc.js");

if (!existsSync(src)) {
  console.error(`コアが見つからない: ${src}\n先に dev/web/core で dune build を実行する`);
  process.exit(1);
}
mkdirSync(dirname(dst), { recursive: true });
rmSync(dst, { force: true }); // dune の成果物は読み取り専用なので前回分を消してから上書きする
copyFileSync(src, dst);
chmodSync(dst, 0o644);
console.log(`copied: ${dst}`);
