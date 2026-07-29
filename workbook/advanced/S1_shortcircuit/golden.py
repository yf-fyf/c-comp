#!/usr/bin/env python3
"""S1 golden test — 短絡が必要なテストが通ること + fixed15 が壊れないこと

使い方:
    python3 golden.py
    SEMCC_COMPILER=... SEMCC_PASSES=... python3 golden.py
"""

import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
compiler = Path(os.environ.get("SEMCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


def run_tests(comp, tests):
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(comp), "--tests", str(tests)],
        text=True, capture_output=True, env=os.environ,
    )
    return r.returncode == 0, r.stdout


def main():
    tests = DIR / "tests"

    print("=== 1. 短絡なし(いまの mycc)では落ちることを確認 ===")
    ok_plain, out_plain = run_tests(compiler, tests)
    tail = out_plain.strip().splitlines()[-2:-1]
    print("\n".join(tail) if tail else out_plain.strip()[-200:])
    if ok_plain:
        print("(すでに短絡が実装されているコンパイラのようです)")
    else:
        print("→ 短絡しないと NULL 参照やゼロ除算で落ちる。期待どおり")

    print()
    print("=== 2. 短絡ありで全テストが通る ===")
    ok_sc, out_sc = run_tests(DIR / "semcc.py", tests)
    print("\n".join(out_sc.strip().splitlines()[-3:]))
    if not ok_sc:
        if "NotImplementedError" in out_sc:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 3. fixed15 が壊れていないことを確認 ===")
    ok_fixed, out_fixed = run_tests(DIR / "semcc.py", WORKBOOK / "final" / "tests")
    print("\n".join(out_fixed.strip().splitlines()[-3:]))
    if not ok_fixed:
        print("\n&& / || が返す値(1 か 0)が変わっていないか確認する。")
        return 1

    print()
    print("短絡評価が動き、既存のテストも壊れていない。C の意味論に一歩近づいた!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
