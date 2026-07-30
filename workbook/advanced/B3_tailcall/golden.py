#!/usr/bin/env python3
"""B3 golden test — 深い末尾再帰が動くこと + fixed15 が壊れないこと

使い方:
    python3 golden.py
    TCCC_COMPILER=... TCCC_PASSES=... python3 golden.py
"""

import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
sys.path.insert(0, str(DIR.parent))
compiler = Path(os.environ.get("TCCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


from basecc import ensure_base  # noqa: E402
ensure_base(compiler, "TCCC_COMPILER")
def run_tests(comp, tests):
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(comp), "--tests", str(tests)],
        text=True, capture_output=True, env=os.environ,
    )
    return r.returncode == 0, r.stdout


def main():
    tests = DIR / "tests"

    print("=== 1. 最適化なしでは深い末尾再帰が落ちることを確認 ===")
    ok_plain, out_plain = run_tests(compiler, tests)
    if ok_plain:
        print("(このコンパイラ/環境では最適化なしでも通ってしまった。"
              "tests/deep_sum.c の再帰の深さを増やすと差が出る)")
    else:
        print("最適化なし: FAIL（スタックがあふれた）— 期待どおり")

    print()
    print("=== 2. 最適化ありで深い末尾再帰が動く ===")
    ok_tc, out_tc = run_tests(DIR / "tccc.py", tests)
    print("\n".join(out_tc.strip().splitlines()[-3:]))
    if not ok_tc:
        if "NotImplementedError" in out_tc:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 3. fixed15 が壊れていないことを確認 ===")
    ok_fixed, out_fixed = run_tests(DIR / "tccc.py", WORKBOOK / "final" / "tests")
    print("\n".join(out_fixed.strip().splitlines()[-3:]))
    if not ok_fixed:
        print("\n末尾呼び出しの判定が広すぎるかもしれない。"
              "return f(x) + 1; のような形を誤って変換していないか確認する。")
        return 1

    print()
    print("深い末尾再帰が動き、既存のテストも壊れていない。最適化成功!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
