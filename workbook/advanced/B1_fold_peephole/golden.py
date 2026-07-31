#!/usr/bin/env python3
"""B1 golden test — 正しさ(fixed17 全通)と効果(命令数の削減)を確認する

使い方:
    python3 golden.py                     # final/mycc.py をベースに確認
    OPTCC_COMPILER=... python3 golden.py  # ベースのコンパイラを差し替え

1. fixed17 を foldcc.py(fold + peephole つき)でコンパイルして全テスト実行
2. 各テストの命令数を最適化なし/ありで数えて表にする

「全テスト PASS」かつ「命令数が減っている」ことがこの回の完了条件。
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

compiler = Path(os.environ.get("OPTCC_COMPILER", WORKBOOK / "final" / "mycc.py"))


from basecc import ensure_base  # noqa: E402
ensure_base(compiler, "OPTCC_COMPILER")
def compile_with(args, src):
    result = subprocess.run(
        [sys.executable, *args, str(src)],
        capture_output=True, text=True, env=os.environ,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout


def main():
    # ---- 1. 正しさ: fixed17 を foldcc 経由で全実行 ----
    print("=== 正しさの確認(fixed17 を foldcc 経由で実行)===")
    runner = subprocess.run(
        [sys.executable, str(WORKBOOK / "scaffold" / "test_runner.py"),
         "--compiler", str(DIR / "foldcc.py"), "--tests", str(TESTS)],
        text=True, capture_output=True, env=os.environ,
    )
    tail = runner.stdout.strip().splitlines()[-3:]
    print("\n".join(tail))
    if runner.returncode != 0:
        print("\n最適化によってテストが壊れている。意味を変える置換がないか確認する。")
        if "未実装" in runner.stdout or "NotImplementedError" in runner.stderr:
            print("(未実装の Step がある場合は、先に check.py を全 PASS にする)")
        return 1

    # ---- 2. 効果: 命令数の before / after ----
    print()
    print("=== 命令数の削減 ===")
    print(f"{'テスト':<24} {'最適化なし':>10} {'あり':>8} {'削減':>8}")
    total_before = 0
    total_after = 0
    for src in sorted(TESTS.glob("*.c")):
        before = count(compile_with([str(compiler)], src))
        after = count(compile_with([str(DIR / "foldcc.py")], src))
        total_before += before
        total_after += after
        pct = (before - after) * 100 // before if before else 0
        print(f"{src.name:<24} {before:>10} {after:>8} {pct:>7}%")

    pct = (total_before - total_after) * 100 // total_before
    print("-" * 54)
    print(f"{'合計':<24} {total_before:>10} {total_after:>8} {pct:>7}%")

    if total_after >= total_before:
        print("\n命令数が減っていない。パスが適用されているか確認する。")
        return 1

    print("\n全テスト PASS + 命令数削減。意味を保ったまま速くなった!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
