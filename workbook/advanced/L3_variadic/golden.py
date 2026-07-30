#!/usr/bin/env python3
"""L3 golden test — 可変長引数の定義が動くこと + fixed15 が壊れないこと

使い方:
    python3 golden.py
    VARCC_COMPILER=... VARCC_PASSES=... python3 golden.py
"""

import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
sys.path.insert(0, str(DIR.parent))
compiler = Path(os.environ.get("VARCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


from basecc import ensure_base  # noqa: E402
ensure_base(compiler, "VARCC_COMPILER")
def run_tests(comp, tests):
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(comp), "--tests", str(tests)],
        text=True, capture_output=True, env=os.environ,
    )
    return r.returncode == 0, r.stdout


def main():
    tests = DIR / "tests"

    print("=== 1. 対応なし(いまの mycc)では動かないことを確認 ===")
    ok_plain, out_plain = run_tests(compiler, tests)
    if ok_plain:
        print("(すでに可変長引数が実装されているコンパイラのようです)")
    else:
        print("対応なし: FAIL — __arg が未定義の関数として呼ばれる。期待どおり")

    print()
    print("=== 2. 対応ありで全テストが通る ===")
    ok, out = run_tests(DIR / "varcc.py", tests)
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        if "NotImplementedError" in out:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 3. fixed15 が壊れていないことを確認 ===")
    ok_fixed, out_fixed = run_tests(DIR / "varcc.py", WORKBOOK / "final" / "tests")
    print("\n".join(out_fixed.strip().splitlines()[-3:]))
    if not ok_fixed:
        print("\n可変長でない関数のフレームまで大きくしていないか確認する。")
        return 1

    print()
    print("可変長引数の定義が動き、既存のテストも壊れていない!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
