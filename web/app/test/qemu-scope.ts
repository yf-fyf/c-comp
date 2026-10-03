import type { Program } from "../src/sim/assembler";

// design/webapps.md の libc シムの対象外。未知の呼び出し全般は除外しない。
const STREAM_IO = new Set(["fdopen", "fprintf", "fopen", "fread", "fclose"]);

export function conformanceExclusion(program: Program): string | null {
  const names = new Set<string>();
  for (const insn of program.insns) {
    if (insn.op === "call" && insn.target !== null && STREAM_IO.has(insn.target)
        && !program.textLabels.has(insn.target)) {
      names.add(insn.target);
    }
  }
  return names.size > 0
    ? `未対応のストリームI/O: ${[...names].sort().join(", ")}`
    : null;
}
