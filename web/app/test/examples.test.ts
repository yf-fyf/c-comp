// 手書きサンプル（web/examples/asm/*.s）が意図どおりに動くことを確かめる。
// プリセットが壊れたまま配信されるのを防ぐ。
import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { assemble } from "../src/sim/assembler";
import { Machine } from "../src/sim/machine";

const HERE = dirname(fileURLToPath(import.meta.url));
const ASM_DIR = join(HERE, "../../examples/asm");

interface Result {
  exitCode: number | null;
  stdout: string;
  kinds: string[];
  aborted: string | null;
}

function runFile(name: string): Result {
  const text = readFileSync(join(ASM_DIR, name), "utf8");
  const m = new Machine(assemble(text), 5000);
  let aborted: string | null = null;
  try {
    while (!m.halted) m.step();
  } catch (e) {
    aborted = (e as Error).message;
  }
  return {
    exitCode: m.exitCode,
    stdout: m.stdout,
    kinds: m.warnings.map((w) => w.kind),
    aborted,
  };
}

const files = readdirSync(ASM_DIR).filter((f) => f.endsWith(".s")).sort();

describe("手書きサンプル", () => {
  it("すべてアセンブルできて、題名と説明が付いている", () => {
    expect(files.length).toBeGreaterThan(0);
    for (const f of files) {
      const text = readFileSync(join(ASM_DIR, f), "utf8");
      expect(text, `${f} に @title がない`).toMatch(/^#\s*@title\s+\S/m);
      expect(text, `${f} に @desc がない`).toMatch(/^#\s*@desc\s+\S/m);
      expect(() => assemble(text), `${f} がアセンブルできない`).not.toThrow();
    }
  });

  it("01_prologue: 3 + 4 = 7、警告なし", () => {
    const r = runFile("01_prologue.s");
    expect(r.exitCode).toBe(7);
    expect(r.kinds).toEqual([]);
  });

  it("02_recursion: fact(5) = 120、警告なし", () => {
    const r = runFile("02_recursion.s");
    expect(r.exitCode).toBe(120);
    expect(r.kinds).toEqual([]);
  });

  it("03_bug_sp_align: 答えは合うが sp-align の警告が出る", () => {
    const r = runFile("03_bug_sp_align.s");
    expect(r.exitCode).toBe(42);
    expect(r.kinds).toContain("sp-align");
  });

  it("04_bug_ra: 無限ループになり ra-clobber の警告が出る", () => {
    const r = runFile("04_bug_ra.s");
    expect(r.aborted).toMatch(/無限ループ/);
    expect(r.kinds).toContain("ra-clobber");
  });

  it("05_array_index: 30 + 40 = 70、警告なし", () => {
    const r = runFile("05_array_index.s");
    expect(r.exitCode).toBe(70);
    expect(r.kinds).toEqual([]);
  });

  it("06_printf: 書式が展開される", () => {
    const r = runFile("06_printf.s");
    expect(r.stdout).toBe("42 and hi\n");
    expect(r.exitCode).toBe(0);
  });

  it("07_bug_exit_range: 300 を返すと 44 になり警告が出る", () => {
    const r = runFile("07_bug_exit_range.s");
    expect(r.exitCode).toBe(44);
    expect(r.kinds).toContain("exit-range");
  });
});

// 参照実装（OCaml 版）が出したアセンブリは、教材の手本として配信される。
// 呼び出し規約違反が混ざっていないことを、シミュレータ自身の検査で確かめる。
// 以前 gen_call の padding が引数の個数だけを見ていたため、
// 一時値を積んだまま call する形（`n * fact(n - 1)` など）で sp が 8 ずれていた。
describe("参照実装プリセット", () => {
  const examples = JSON.parse(
    readFileSync(join(HERE, "../public/sim-examples.json"), "utf8"),
  ) as { label: string; gated: boolean; source: string }[];
  const generated = examples.filter((e) => e.gated);

  it("プリセットが生成されている", () => {
    expect(generated.length).toBeGreaterThan(0);
  });

  it("call の直前で sp が 16 バイト境界から外れない", () => {
    const offenders: string[] = [];
    let checked = 0;
    for (const ex of generated) {
      let m: Machine;
      try {
        // main を持たない翻訳単位（複数ファイル教材のライブラリ側）は動かせない
        m = new Machine(assemble(ex.source), 200000);
      } catch {
        continue;
      }
      checked++;
      try {
        while (!m.halted) m.step();
      } catch {
        // 実行時エラーは他のテストの担当。ここでは警告だけを見る
      }
      const hit = m.warnings.find((w) => w.kind === "sp-align");
      if (hit) offenders.push(`${ex.label}: ${hit.line} 行目 ${hit.message}`);
    }
    expect(offenders).toEqual([]);
    expect(checked).toBeGreaterThan(50);
  });
});
