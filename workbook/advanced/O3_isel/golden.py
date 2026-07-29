#!/usr/bin/env python3
"""O3 golden test — 正しさ(fixed15)と効果(静的・動的命令数)を測る

使い方:
    python3 golden.py
    OPT_COMPILER=... OPT_ANSWERS=... python3 golden.py
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

def _measure_path():
    """O1 の measure.py を探す(OPT_ANSWERS があればそちらを優先)。"""
    answers = os.environ.get("OPT_ANSWERS")
    if answers:
        cand = Path(answers) / "O1_measure" / "measure.py"
        if cand.is_file():
            return cand
    return OPTDIR / "O1_measure" / "measure.py"


spec = importlib.util.spec_from_file_location("O1_measure", _measure_path())
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")


def run_tests(tests, passes):
    env = dict(os.environ, OPT_PASSES=passes)
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(OPTCC), "--tests", str(tests)],
        text=True, capture_output=True, env=env,
    )
    return r.returncode == 0, r.stdout


def build(csrc, passes, workdir, tag):
    r = subprocess.run(
        [sys.executable, str(OPTCC), "--passes", passes, str(csrc)],
        capture_output=True, text=True, env=os.environ,
    )
    if r.returncode != 0:
        raise RuntimeError(f"{csrc.name}: コンパイル失敗\n{r.stderr[:300]}")
    asm = r.stdout
    exe = workdir / f"{csrc.stem}_{tag}"
    link = subprocess.run([GCC, "-x", "assembler", "-static", "-", "-o", str(exe)],
                          input=asm, capture_output=True, text=True)
    if link.returncode != 0:
        raise RuntimeError(f"{csrc.name}: アセンブル失敗\n{link.stderr[:300]}")
    return asm, exe


def main():
    print("=== 1. 正しさの確認(fixed15 を isel ありで実行)===")
    ok, out = run_tests(WORKBOOK / "final" / "tests", "isel")
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        if "NotImplementedError" in out:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        else:
            print("\n畳み込みが意味を変えている。is_dead_after の判定を確認する。")
        return 1

    print()
    print("=== 2. ベンチマークの正しさ ===")
    ok, out = run_tests(BENCH, "isel")
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        return 1

    print()
    print("=== 3. 効果(静的・動的命令数)===")
    try:
        me.count_static("  ret\n")
    except NotImplementedError:
        print("O1(measure.py)が未完成のため、効果の測定は省略します。")
        print("先に O1_measure/check.py を全 PASS にしてください。")
        return 0
    print(f"{'ベンチマーク':<12} {'静的:前':>8} {'後':>7} {'削減':>6} "
          f"{'動的:前':>10} {'後':>10} {'削減':>6}")
    print("-" * 66)
    tb = ta = db = da = 0
    with tempfile.TemporaryDirectory() as tmp:
        for csrc in sorted(BENCH.glob("*.c")):
            asm0, exe0 = build(csrc, "", Path(tmp), "before")
            asm1, exe1 = build(csrc, "isel", Path(tmp), "after")
            s0, s1 = me.count_static(asm0), me.count_static(asm1)
            d0 = me.count_dynamic(exe0, me.function_names(asm0))[0]
            d1 = me.count_dynamic(exe1, me.function_names(asm1))[0]
            tb += s0
            ta += s1
            db += d0
            da += d1
            print(f"{csrc.stem:<12} {s0:>8} {s1:>7} {(s0-s1)*100//s0:>5}% "
                  f"{d0:>10} {d1:>10} {(d0-d1)*100//d0:>5}%")
    print("-" * 66)
    print(f"{'合計':<12} {tb:>8} {ta:>7} {(tb-ta)*100//tb:>5}% "
          f"{db:>10} {da:>10} {(db-da)*100//db:>5}%")

    if ta >= tb:
        print("\n命令数が減っていない。畳み込みが適用されているか確認する。")
        return 1
    print()
    print("正しさを保ったまま、静的にも動的にも命令が減った。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
