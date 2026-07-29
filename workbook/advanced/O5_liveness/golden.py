#!/usr/bin/env python3
"""O5 golden test — 解析が意味を持つのはいつかを測る

使い方:
    python3 golden.py
    OPT_COMPILER=... OPT_ANSWERS=... python3 golden.py

この回は命令数を減らさない。**解析そのもの**が成果物である。
そこで「ブロックの境界で何本のレジスタが生きているか」を測り、
レジスタ割り当て(O4)の前後で比べる。
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
OPTDIR = DIR.parent
WORKBOOK = DIR.parents[1]
BENCH = OPTDIR / "O1_measure" / "bench"
OPTCC = OPTDIR / "optcc.py"
OUTDIR = DIR / "cfg_out"

passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O5_liveness" / "liveness.py").is_file():
    passes_dir = passes_dir / "O5_liveness"
spec = importlib.util.spec_from_file_location("O5_liveness", passes_dir / "liveness.py")
lv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lv)
cfg = lv.cfg

# 値を運ぶわけではないレジスタ(常に生きている)は数えない
PLUMBING = {'sp', 's0', 'ra'}
# 割り当てに使う callee-saved レジスタ(sp や s0 は含めない)
SAVED = re.compile(r's([1-9]|1[01])$')


def compile_asm(csrc, regalloc):
    args = [sys.executable, str(OPTCC)]
    if regalloc:
        args.append("--regalloc")
    args += ["--passes", "isel", str(csrc)]
    r = subprocess.run(args, capture_output=True, text=True, env=os.environ)
    if r.returncode != 0:
        raise RuntimeError(f"{csrc.name}: コンパイル失敗\n{r.stderr[-400:]}")
    return r.stdout


def measure(csrc, regalloc):
    blocks, edges = cfg.build_cfg(compile_asm(csrc, regalloc).splitlines())
    _live_in, live_out = lv.solve(blocks, edges)
    carried = [len(s - PLUMBING) for s in live_out]
    regs = {r for s in live_out for r in s if SAVED.match(r)}
    return blocks, edges, sum(carried) / max(len(blocks), 1), sorted(regs)


def main():
    print("=== 1. 解析が動くことを確認 ===")
    try:
        rows = []
        for csrc in sorted(BENCH.glob("*.c")):
            before = measure(csrc, False)
            after = measure(csrc, True)
            rows.append((csrc.stem, before, after))
            print(f"{csrc.stem:<12} OK")
    except NotImplementedError as e:
        print(f"\n未実装: {e}")
        print("(先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 2. ブロックの境界で生きているレジスタの平均本数 ===")
    print("(sp / s0 / ra は常に生きているので数えない)")
    print()
    print(f"{'ベンチマーク':<12} {'ブロック':>8} {'割当なし':>10} {'割当あり':>10}   "
          f"値を運ぶ s レジスタ")
    print("-" * 70)
    tot_before = tot_after = 0.0
    for name, before, after in rows:
        tot_before += before[2]
        tot_after += after[2]
        print(f"{name:<12} {len(before[0]):>8} {before[2]:>10.2f} {after[2]:>10.2f}   "
              f"{', '.join(after[3]) or '(なし)'}")
    print("-" * 70)
    n = len(rows)
    print(f"{'平均':<12} {'':>8} {tot_before / n:>10.2f} {tot_after / n:>10.2f}")

    if tot_after <= tot_before:
        print()
        print("割り当ての前後で差が出ていない。O4 が効いているか確認する。")
        print("  python3 ../optcc.py --regalloc --passes isel "
              "../O1_measure/bench/loop_sum.c | grep 'mv a0, s'")
        return 1

    print()
    print("=== 3. 呼び出しをまたいで生きるレジスタ ===")
    for name, _before, after in rows:
        blocks, edges = after[0], after[1]
        ncall = sum(1 for b in blocks for i in b.insns if i.split()[0] == 'call')
        if ncall == 0:
            print(f"{name:<12} 呼び出しなし")
            continue
        across = lv.live_across_calls(blocks, edges)
        callee = sorted(r for r in across if SAVED.match(r))
        print(f"{name:<12} call {ncall:>2}回  callee-saved が要るもの: "
              f"{', '.join(callee) or '(なし)'}")

    print()
    print("=== 4. 図を書き出す ===")
    OUTDIR.mkdir(exist_ok=True)
    dot = shutil.which("dot")
    for name, _before, after in rows:
        blocks, edges = after[0], after[1]
        annot = lv.annotate(blocks, edges)
        for func in sorted({b.func for b in blocks}):
            path = OUTDIR / f"{name}_{func}_live.dot"
            path.write_text(cfg.to_dot(blocks, edges, annot=annot, func=func),
                            encoding="utf-8")
            if dot:
                subprocess.run([dot, "-Tpng", str(path),
                                "-o", str(path.with_suffix(".png"))], check=True)
    print(f"{OUTDIR}/ に書き出した" + ("(PNG つき)" if dot else "(dot が無いので .dot のみ)"))

    print()
    print("レジスタ割り当ての**前**は、ブロックをまたいで生きる値がほとんど無い。")
    print("値をすぐスタックへ逃がしているので、解析しても新しいことが分からない。")
    print("割り当ての**後**は s1〜s11 が変数を運ぶので、解析が意味を持つ。")
    print("—— 解析の役に立ち方は、コードの表現の仕方で決まる。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
