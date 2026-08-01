#!/usr/bin/env python3
"""L1 golden test — ポインタ差のテストが通ること + fixed17 が壊れないこと

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
sys.path.insert(0, str(DIR.parent))
compiler = Path(os.environ.get("LANGCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


from basecc import ensure_base  # noqa: E402
ensure_base(compiler, "LANGCC_COMPILER")
def run_tests(comp, tests):
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(comp), "--tests", str(tests)],
        text=True, capture_output=True, env=os.environ,
    )
    return r.returncode == 0, r.stdout


def main():
    tests = DIR / "tests"

    print("=== 1. 修正なし(いまの mycc)では落ちることを確認 ===")
    ok_plain, out_plain = run_tests(compiler, tests)
    tail = out_plain.strip().splitlines()[-2:-1]
    print("\n".join(tail) if tail else out_plain.strip()[-200:])
    if ok_plain:
        print("(すでにポインタ差が実装されているコンパイラのようです)")
    else:
        print("→ 要素サイズで割らないとバイト差が返る。期待どおり")

    print()
    print("=== 2. 修正ありで全テストが通る ===")
    ok_sc, out_sc = run_tests(DIR / "langcc.py", tests)
    print("\n".join(out_sc.strip().splitlines()[-3:]))
    if not ok_sc:
        if "NotImplementedError" in out_sc:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 3. fixed17 が壊れていないことを確認 ===")
    ok_fixed, out_fixed = run_tests(DIR / "langcc.py", WORKBOOK / "final" / "tests")
    print("\n".join(out_fixed.strip().splitlines()[-3:]))
    if not ok_fixed:
        print("\nポインタ − 整数(p - 3)の生成を壊していないか確認する。")
        return 1

    print()
    print("ポインタ差が要素数になり、既存のテストも壊れていない!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
