#!/usr/bin/env python3
"""O1 golden test — ベンチマークを正しさと2つの物差しで測る

使い方:
    python3 golden.py
    OPT_COMPILER=... python3 golden.py
    python3 golden.py path/to/passes_dir      # 教員用参照実装で確認する

1. bench/*.c が全部正しく動くこと
2. 静的命令数と動的命令数を表にすること
3. 「静的が同じくらいでも動的は桁違い」という関係が見えること
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
BENCH = DIR / "bench"
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
OPTCC = DIR.parent / "optcc.py"

passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O1_measure" / "measure.py").is_file():
    passes_dir = passes_dir / "O1_measure"
spec = importlib.util.spec_from_file_location("O1_measure", passes_dir / "measure.py")
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)

COMPILER = Path(os.environ.get("OPT_COMPILER", WORKBOOK / "final" / "mycc.py"))
GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")


def build(csrc, workdir):
    r = subprocess.run([sys.executable, str(COMPILER), str(csrc)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{csrc.name}: コンパイル失敗\n{r.stderr[:300]}")
    asm = r.stdout
    exe = workdir / csrc.stem
    link = subprocess.run([GCC, "-x", "assembler", "-static", "-", "-o", str(exe)],
                          input=asm, capture_output=True, text=True)
    if link.returncode != 0:
        raise RuntimeError(f"{csrc.name}: アセンブル失敗\n{link.stderr[:300]}")
    return asm, exe


def main():
    print("=== 1. ベンチマークが正しく動くことを確認 ===")
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(OPTCC), "--tests", str(BENCH)],
        text=True, capture_output=True, env=os.environ,
    )
    print("\n".join(r.stdout.strip().splitlines()[-3:]))
    if r.returncode != 0:
        print("\nベンチマークが通らない。まず final/mycc.py を完成させる。")
        return 1

    print()
    print("=== 2. 2つの物差しで測る ===")
    print(f"{'ベンチマーク':<14} {'静的':>7} {'動的':>10} {'増幅率':>8}")
    print("-" * 44)
    rows = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for csrc in sorted(BENCH.glob("*.c")):
                asm, exe = build(csrc, Path(tmp))
                static = me.count_static(asm)
                names = me.function_names(asm)
                dyn, _total = me.count_dynamic(exe, names)
                ratio = dyn / static if static else 0
                rows.append((csrc.stem, static, dyn, ratio))
                print(f"{csrc.stem:<14} {static:>7} {dyn:>10} {ratio:>7.0f}x")
    except NotImplementedError as e:
        print(f"\n未実装: {e}")
        print("(先に check.py を全 PASS にする)")
        return 1

    print()
    ratios = [r[3] for r in rows]
    lo = min(ratios)
    hi = max(ratios)
    print(f"増幅率の幅: {lo:.0f}x 〜 {hi:.0f}x")
    if hi < lo * 3:
        print("増幅率に差が出ていない。ベンチマークが単調すぎないか確認する。")
        return 1

    print()
    print("静的命令数が近くても、動的命令数は桁違いになる。")
    print("「どこを速くすべきか」は静的命令数だけでは分からない —— これが測る理由。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
