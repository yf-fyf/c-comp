#!/usr/bin/env python3
"""R3 確認スクリプト — 自前 malloc をテストする

使い方:
    python3 check.py                 # 同じディレクトリの mymalloc.c
    python3 check.py path/to/dir     # 別ディレクトリ(教員用参照実装など)

各テストは、tests/*.c と mymalloc.c を自作コンパイラで一緒にコンパイルし、
qemu で実行して終了コードを .ans と比較する。
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
src_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
TESTS = DIR / "tests"

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")
QEMU = os.environ.get("QEMU", "qemu-riscv64")
COMPILER = Path(os.environ.get("R3_COMPILER", WORKBOOK / "final" / "mycc.py"))

HINTS = {
    1: "解放したブロックが再利用されていない(find_free を確認)",
    2: "heap_used が合わない(free フラグの設定を確認)",
    99: "確保し続けられてしまう(プールの終端チェックを確認)",
}

pass_count = 0
fail_count = 0

for tool in (GCC, QEMU):
    if shutil.which(tool) is None:
        print(f"{tool} が見つかりません。docker/rv64 環境で実行してください。",
              file=sys.stderr)
        raise SystemExit(2)

impl = src_dir / "mymalloc.c"
if not impl.is_file():
    print(f"mymalloc.c が見つかりません: {impl}", file=sys.stderr)
    raise SystemExit(2)
if not COMPILER.is_file():
    print(f"コンパイラが見つかりません: {COMPILER}", file=sys.stderr)
    raise SystemExit(2)

for csrc in sorted(TESTS.glob("*.c")):
    label = csrc.name
    expected = int(csrc.with_suffix(".ans").read_text().strip())

    r = subprocess.run([sys.executable, str(COMPILER), str(csrc), str(impl)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [FAIL] {label} — コンパイルに失敗: {r.stderr.strip()[:300]}")
        fail_count += 1
        continue

    with tempfile.TemporaryDirectory() as tmp:
        asm = Path(tmp) / "prog.s"
        asm.write_text(r.stdout)
        exe = Path(tmp) / "a.out"
        link = subprocess.run([GCC, "-x", "assembler", "-static",
                               str(asm), "-o", str(exe)],
                              capture_output=True, text=True)
        if link.returncode != 0:
            print(f"  [FAIL] {label} — アセンブルに失敗: {link.stderr.strip()[:300]}")
            fail_count += 1
            continue
        run = subprocess.run([QEMU, str(exe)], capture_output=True, text=True)

    if run.returncode == expected:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        hint = HINTS.get(run.returncode, "")
        print(f"  [FAIL] {label} — 期待 {expected}, 実際 {run.returncode}"
              + (f" ({hint})" if hint else ""))
        fail_count += 1

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}")
print("=============================")
if fail_count == 0:
    print("自前 malloc が動いた! ヒープの管理が自分のものになった。")
if fail_count > 0:
    raise SystemExit(1)
