#!/usr/bin/env python3
"""B2 golden test — 正しさ(fixed15 全通)と効果(命令数)を確認する

使い方:
    python3 golden.py
    REGCC_COMPILER=... REGCC_PASSES=... python3 golden.py
"""

import os
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
TESTS = WORKBOOK / "final" / "tests"

sys.path.insert(0, str(DIR.parent))
from count_insns import count  # noqa: E402

compiler = Path(os.environ.get("REGCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


from basecc import ensure_base  # noqa: E402
ensure_base(compiler, "REGCC_COMPILER")
def compile_with(prog, src):
    r = subprocess.run([sys.executable, str(prog), str(src)],
                       capture_output=True, text=True, env=os.environ)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return r.stdout


def main():
    print("=== 正しさの確認(fixed15 をレジスタスタック版で実行)===")
    runner = subprocess.run(
        [sys.executable, str(WORKBOOK / "scaffold" / "test_runner.py"),
         "--compiler", str(DIR / "regcc.py"), "--tests", str(TESTS)],
        text=True, capture_output=True, env=os.environ,
    )
    print("\n".join(runner.stdout.strip().splitlines()[-3:]))
    if runner.returncode != 0:
        print("\nテストが落ちている。次の点を確認する:")
        print("  - push と pop で depth の増減が対称か")
        print("  - call をまたぐ t レジスタを退避・復元しているか")
        print("  - メモリ退避のとき sp の増減が一致しているか")
        if "NotImplementedError" in runner.stdout + runner.stderr:
            print("  (未実装の Step がある場合は先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 命令数の削減 ===")
    print(f"{'テスト':<24} {'メモリ版':>10} {'レジスタ版':>10} {'削減':>8}")
    tb = ta = 0
    for src in sorted(TESTS.glob("*.c")):
        b = count(compile_with(compiler, src))
        a = count(compile_with(DIR / "regcc.py", src))
        tb += b
        ta += a
        pct = (b - a) * 100 // b if b else 0
        print(f"{src.name:<24} {b:>10} {a:>10} {pct:>7}%")
    pct = (tb - ta) * 100 // tb
    print("-" * 56)
    print(f"{'合計':<24} {tb:>10} {ta:>10} {pct:>7}%")

    if ta >= tb:
        print("\n命令数が減っていない。レジスタ退避が使われているか確認する。")
        return 1
    print("\n全テスト PASS + 命令数削減。スタックマシンを卒業!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
