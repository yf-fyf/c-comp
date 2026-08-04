#!/usr/bin/env python3
"""L5 golden test — struct の値渡し・値返しが動くこと + fixed17 が壊れないこと

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

    print("=== 1. 値渡し・値返しなし(いまの mycc)では構文エラーになることを確認 ===")
    ok_plain, out_plain = run_tests(compiler, tests)
    if ok_plain:
        print("(すでに struct の値渡し・値返しが実装されているコンパイラのようです)")
    else:
        print("値渡し・値返しなし: FAIL —"
              "『struct 値はここでは使えません』『struct 値の戻り値は使えません』。期待どおり")

    print()
    print("=== 2. 値渡し・値返しありで全テストが通る ===")
    ok, out = run_tests(DIR / "langcc.py", tests)
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        if "NotImplementedError" in out:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 3. fixed17 が壊れていないことを確認 ===")
    ok_fixed, out_fixed = run_tests(DIR / "langcc.py", WORKBOOK / "final" / "tests")
    print("\n".join(out_fixed.strip().splitlines()[-3:]))
    if not ok_fixed:
        print("\nint やポインタの引数・戻り値まで struct 扱いしていないか確認する。")
        return 1

    print()
    print("struct の値渡し・値返しが動き、既存のテストも壊れていない!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
