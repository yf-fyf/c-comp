#!/usr/bin/env python3
"""コマ2 確認スクリプト — mycc.py でテストケースを評価"""

import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
MYCC = DIR / "mycc.py"
TESTS = DIR / "tests"

pass_count = 0
fail_count = 0
sources = sorted(TESTS.glob("*.c"))

if not sources:
    print(f"[FAIL] テストが見つかりません: {TESTS}")
    raise SystemExit(1)

for src in sources:
    ans_file = src.with_suffix(".ans")
    if not ans_file.exists():
        print(f"[FAIL] {src} — expected answer がありません: {ans_file}")
        fail_count += 1
        continue

    expected = ans_file.read_text().strip()

    result = subprocess.run(
        [sys.executable, str(MYCC), str(src)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[FAIL] {src} — interpreter error")
        if result.stderr.strip():
            print(result.stderr.strip())
        fail_count += 1
        continue

    output = result.stdout.strip()
    expected_output = f"評価結果: {expected}"

    if output == expected_output:
        print(f"[PASS] {src}")
        pass_count += 1
    else:
        print(f"[FAIL] {src} — expected={expected_output!r}, got={output!r}")
        fail_count += 1

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
