// シミュレータの正しさを qemu との照合で担保する（design/webapps.md 4章）。
//
// workbook の全テストを参照実装 lecture15 でアセンブリ化し、
//   (a) riscv64-linux-gnu-gcc + qemu-riscv64 で実行した結果
//   (b) TypeScript シミュレータで実行した結果
// の終了コードと標準出力を突き合わせる。
// 比べる相手は .ans ではなく qemu の実測値である。ここで試験したいのは
// コンパイラではなくシミュレータだから。
//
// ストリームI/Oと main のない補助ソースは理由を表示して除外する。
// 使い方: npm run test:qemu -- [-v]

import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { conformanceExclusion } from "./qemu-scope";

const HERE = dirname(fileURLToPath(import.meta.url));
const APP = join(HERE, "..");
const DEV = join(APP, "../..");
const WORKBOOK = join(DEV, "workbook");
const LECTURE15 = join(WORKBOOK, "ocaml/_build/default/sessions/lecture15.exe");
const GCC = process.env.GCC ?? "riscv64-linux-gnu-gcc";
const QEMU = process.env.QEMU ?? "qemu-riscv64";

const verbose = process.argv.includes("-v");

function have(cmd: string): boolean {
  return spawnSync(cmd, ["--version"], { encoding: "utf8" }).status === 0;
}

if (!existsSync(LECTURE15)) {
  console.error(`参照コンパイラがない: ${LECTURE15}\n  cd workbook/ocaml && dune build`);
  process.exit(2);
}
for (const tool of [GCC, QEMU]) {
  if (!have(tool)) {
    console.error(`必要なツールがない: ${tool}（docker/rv64 経由なら動く）`);
    process.exit(2);
  }
}

// テスト対象の .c を集める
const testDirs = [
  "final/tests",
  ...readdirSync(join(WORKBOOK, "sessions")).map((s) => `sessions/${s}/tests`),
];
const sources: string[] = [];
for (const rel of testDirs) {
  const dir = join(WORKBOOK, rel);
  if (!existsSync(dir)) continue;
  for (const f of readdirSync(dir)) {
    if (f.endsWith(".c")) sources.push(join(dir, f));
  }
}
sources.sort();

const { Machine } = await import("../src/sim/machine");
const { assemble } = await import("../src/sim/assembler");

const tmp = mkdtempSync(join(tmpdir(), "simconf-"));
let ok = 0;
const skipped: [string, string][] = [];
const failures: [string, string][] = [];

for (const src of sources) {
  const rel = relative(WORKBOOK, src);
  // 追加ソース（コマ14 の複数ファイル）
  const filesList = src.replace(/\.c$/, ".files");
  const extra = existsSync(filesList)
    ? readFileSync(filesList, "utf8")
        .split("\n").map((s) => s.trim()).filter(Boolean)
        .map((n) => join(dirname(src), n))
    : [];

  let asm;
  try {
    // #include "lib.h" は scaffold/ を cwd 相対で探すので workbook から実行する
    asm = execFileSync(LECTURE15, [src, ...extra], {
      encoding: "utf8", timeout: 20000, cwd: WORKBOOK,
    });
  } catch {
    failures.push([rel, "参照コンパイラがコンパイルできない"]);
    continue;
  }

  let program;
  try {
    program = assemble(asm);
  } catch (e) {
    failures.push([rel, `シミュレータのアセンブラが例外: ${(e as Error).message}`]);
    continue;
  }
  if (!program.textLabels.has("main") && !program.textLabels.has("_start")) {
    skipped.push([rel, "エントリポイントのない補助ソース"]);
    continue;
  }
  const excluded = conformanceExclusion(program);
  if (excluded !== null) {
    skipped.push([rel, excluded]);
    continue;
  }

  // (a) qemu
  const asmPath = join(tmp, "p.s");
  const binPath = join(tmp, "p.bin");
  writeFileSync(asmPath, asm);
  const build = spawnSync(GCC, ["-x", "assembler", "-static", asmPath, "-o", binPath], {
    encoding: "utf8",
  });
  if (build.status !== 0) {
    failures.push([rel, "アセンブル・リンクできない"]);
    continue;
  }
  const qemu = spawnSync(QEMU, [binPath], { encoding: "utf8", timeout: 15000 });
  if (qemu.error || qemu.signal) {
    failures.push([rel, `qemu が終わらない/異常終了（${qemu.signal ?? qemu.error}）`]);
    continue;
  }

  // (b) シミュレータ
  let simCode: number | null;
  let simOut: string;
  try {
    const m = new Machine(program, 20_000_000, [binPath]);
    while (!m.halted) m.step();
    simCode = m.exitCode;
    simOut = m.stdout;
  } catch (e) {
    failures.push([rel, `シミュレータが例外: ${(e as Error).message}`]);
    continue;
  }

  const qemuCode = qemu.status;
  if (simCode !== qemuCode) {
    failures.push([rel, `終了コード qemu=${qemuCode} sim=${simCode}`]);
  } else if (simOut !== qemu.stdout) {
    failures.push([rel, `標準出力 qemu=${JSON.stringify(qemu.stdout)} sim=${JSON.stringify(simOut)}`]);
  } else {
    ok++;
    if (verbose) console.log(`[一致] ${rel} exit=${qemuCode}`);
  }
}

rmSync(tmp, { recursive: true, force: true });

console.log(`\n一致 ${ok} / 不一致 ${failures.length} / skip ${skipped.length}（対象 ${sources.length}）`);
if (skipped.length > 0) {
  console.log("\nskip:");
  for (const [rel, why] of skipped) console.log(`  ${rel}  ${why}`);
}
if (failures.length > 0) {
  console.log("\n不一致:");
  for (const [rel, why] of failures) console.log(`  ${rel}\n    ${why}`);
  process.exit(1);
}
if (ok === 0) {
  console.error("照合できたテストがないため、成功として扱わない");
  process.exit(1);
}
