#!/usr/bin/env python3
"""L2 golden test — 初期化子が動くこと + fixed15 が壊れないこと

使い方:
    python3 golden.py
    LANGCC_COMPILER=... LANGCC_PASSES=... python3 golden.py
"""

import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
compiler = Path(os.environ.get("LANGCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


def run_tests(comp, tests):
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(comp), "--tests", str(tests)],
        text=True, capture_output=True, env=os.environ,
    )
    return r.returncode == 0, r.stdout


def main():
    tests = DIR / "tests"

    print("=== 1. 初期化子なし(いまの mycc)では構文解析すら通らないことを確認 ===")
    ok_plain, out_plain = run_tests(compiler, tests)
    if ok_plain:
        print("(すでに初期化子が実装されているコンパイラのようです)")
    else:
        print("初期化子なし: FAIL —『式が期待されましたが {』。期待どおり")

    print()
    print("=== 2. 初期化子ありで全テストが通る ===")
    ok, out = run_tests(DIR / "langcc.py", tests)
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        if "NotImplementedError" in out:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 3. fixed15 が壊れていないことを確認 ===")
    ok_fixed, out_fixed = run_tests(DIR / "langcc.py", WORKBOOK / "final" / "tests")
    print("\n".join(out_fixed.strip().splitlines()[-3:]))
    if not ok_fixed:
        print("\n初期化子のない宣言(int a[5];)を壊していないか確認する。")
        return 1

    print()
    print("初期化子リストが動き、既存のテストも壊れていない!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
