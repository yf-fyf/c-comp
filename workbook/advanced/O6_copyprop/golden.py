#!/usr/bin/env python3
"""O6 golden test — 「前に何を掛けたか」で効果が変わることを測る

使い方:
    python3 golden.py
    OPT_COMPILER=... OPT_ANSWERS=... python3 golden.py

同じ死コード除去でも、レジスタ割り当ての前と後では結果がまったく違う。
それを4つの構成で測って並べる(phase ordering)。
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
OPTDIR = DIR.parent
WORKBOOK = DIR.parents[1]
BENCH = OPTDIR / "O1_measure" / "bench"
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
OPTCC = OPTDIR / "optcc.py"

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")

# (見出し, regalloc を使うか, パスの並び)
CONFIGS = [
    ("isel だけ(基準)",          False, "isel"),
    ("isel,copyprop,dce",         False, "isel,copyprop,dce"),
    ("regalloc + isel",           True,  "isel"),
    ("regalloc + 全部",           True,  "isel,copyprop,dce"),
]


def _measure_path():
    answers = os.environ.get("OPT_ANSWERS")
    if answers:
        cand = Path(answers) / "O1_measure" / "measure.py"
        if cand.is_file():
            return cand
    return OPTDIR / "O1_measure" / "measure.py"


spec = importlib.util.spec_from_file_location("O1_measure", _measure_path())
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)


def run_tests(tests, regalloc, passes):
    env = dict(os.environ, OPT_PASSES=passes,
               OPT_REGALLOC="1" if regalloc else "0")
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(OPTCC), "--tests", str(tests)],
        text=True, capture_output=True, env=env,
    )
    return r.returncode == 0, r.stdout


def build(csrc, regalloc, passes, workdir, tag):
    args = [sys.executable, str(OPTCC)]
    if regalloc:
        args.append("--regalloc")
    args += ["--passes", passes, str(csrc)]
    r = subprocess.run(args, capture_output=True, text=True, env=os.environ)
    if r.returncode != 0:
        raise RuntimeError(f"{csrc.name}: コンパイル失敗\n{r.stderr[-400:]}")
    asm = r.stdout
    exe = workdir / f"{csrc.stem}_{tag}"
    link = subprocess.run([GCC, "-x", "assembler", "-static", "-", "-o", str(exe)],
                          input=asm, capture_output=True, text=True)
    if link.returncode != 0:
        raise RuntimeError(f"{csrc.name}: アセンブル失敗\n{link.stderr[:300]}")
    return asm, exe


def main():
    print("=== 1. 正しさの確認 ===")
    for label, regalloc, passes in CONFIGS[1:]:
        ok, out = run_tests(WORKBOOK / "final" / "tests", regalloc, passes)
        last = out.strip().splitlines()[-2] if out.strip() else ""
        print(f"{label:<22} fixed17: {last.strip()}")
        if not ok:
            if "NotImplementedError" in out:
                print("(未実装の Step がある。先に check.py を全 PASS にする)")
                return 1
            print()
            print("意味が変わっている。よくある原因:")
            print("  - copy_prop_block で、元のレジスタが書き換わった後も伝播している")
            print("  - is_dead がストアや call を消している")
            return 1

    print()
    ok, out = run_tests(BENCH, True, "isel,copyprop,dce")
    print("ベンチマーク:", out.strip().splitlines()[-2].strip())
    if not ok:
        return 1

    print()
    print("=== 2. 同じ dce でも、前に何を掛けたかで結果が変わる ===")
    try:
        me.count_static("  ret\n")
    except NotImplementedError:
        print("O1(measure.py)が未完成のため、効果の測定は省略します。")
        return 0

    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        for label, regalloc, passes in CONFIGS:
            static = dynamic = 0
            for csrc in sorted(BENCH.glob("*.c")):
                tag = f"{len(results)}_{csrc.stem}"
                asm, exe = build(csrc, regalloc, passes, Path(tmp), tag)
                static += me.count_static(asm)
                dynamic += me.count_dynamic(exe, me.function_names(asm))[0]
            results[label] = (static, dynamic)

    base = results[CONFIGS[0][0]]
    print(f"{'構成':<24} {'静的':>7} {'削減':>7} {'動的':>10} {'削減':>8}")
    print("-" * 60)
    for label, _r, _p in CONFIGS:
        s, d = results[label]
        print(f"{label:<24} {s:>7} {(base[0] - s) * 100 / base[0]:>6.1f}% "
              f"{d:>10} {(base[1] - d) * 100 / base[1]:>7.1f}%")
    print("-" * 60)

    no_ra = results[CONFIGS[1][0]][0]
    with_ra = results[CONFIGS[3][0]][0]
    ra_only = results[CONFIGS[2][0]][0]
    print()
    print(f"割り当てなしで copyprop,dce をかけても {base[0] - no_ra} 命令しか減らない。")
    print(f"割り当ての後なら、そこからさらに {ra_only - with_ra} 命令減る。")
    print()
    print("同じパスなのに効果が違う。**パスの順番が結果を決める**(phase ordering)。")
    print("O4 が `mv` を作り、O6 がそれを消す —— 最適化が最適化の機会を作っている。")

    if with_ra >= ra_only:
        print()
        print("割り当て後に減っていない。copy_prop_block が伝播できているか確認する。")
        print("  python3 ../optcc.py --regalloc --passes isel,copyprop "
              "../O1_measure/bench/loop_sum.c | grep 'add a0'")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
