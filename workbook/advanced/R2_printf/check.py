#!/usr/bin/env python3
"""R2 確認スクリプト — 自前 printf を libc なしで動かして確認する

使い方:
    python3 check.py                 # 同じディレクトリの myprintf.c
    python3 check.py path/to/dir     # 別ディレクトリ(教員用参照実装など)

各テストは次の手順で確認する。
    1. 自作コンパイラで myprintf.c と tests/*.c をアセンブリに変換
    2. syscall.s と一緒に -nostdlib でリンク(libc は使わない)
    3. qemu で実行し、標準出力と終了コードを .stdout / .ans と比較
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
COMPILER = Path(os.environ.get("R2_COMPILER", WORKBOOK / "final" / "mycc.py"))

pass_count = 0
fail_count = 0


def fail(label, detail):
    global fail_count
    print(f"  [FAIL] {label} — {detail}")
    fail_count += 1


def check(label, ok, detail=""):
    global pass_count
    if ok:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        fail(label, detail)


def compile_c(path, out_s):
    r = subprocess.run([sys.executable, str(COMPILER), str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return r.stderr.strip()[:300]
    out_s.write_text(r.stdout)
    return None


for tool in (GCC, QEMU):
    if shutil.which(tool) is None:
        print(f"{tool} が見つかりません。docker/rv64 環境で実行してください。",
              file=sys.stderr)
        raise SystemExit(2)

impl = src_dir / "myprintf.c"
syscall_s = DIR / "syscall.s"
if not impl.is_file():
    print(f"myprintf.c が見つかりません: {impl}", file=sys.stderr)
    raise SystemExit(2)
if not COMPILER.is_file():
    print(f"コンパイラが見つかりません: {COMPILER}", file=sys.stderr)
    raise SystemExit(2)

for csrc in sorted(TESTS.glob("*.c")):
    label = csrc.name
    expected_code = int(csrc.with_suffix(".ans").read_text().strip())
    out_file = csrc.with_suffix(".stdout")
    expected_out = out_file.read_text() if out_file.exists() else ""

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        err = compile_c(impl, tmp / "impl.s")
        if err:
            fail(label, f"myprintf.c のコンパイルに失敗: {err}")
            continue
        err = compile_c(csrc, tmp / "main.s")
        if err:
            fail(label, f"{csrc.name} のコンパイルに失敗: {err}")
            continue

        exe = tmp / "a.out"
        r = subprocess.run([GCC, "-nostdlib", "-static",
                            str(tmp / "main.s"), str(tmp / "impl.s"),
                            str(syscall_s), "-o", str(exe)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            fail(label, f"リンクに失敗: {r.stderr.strip()[:300]}")
            continue

        run = subprocess.run([QEMU, str(exe)], capture_output=True, text=True)

    check(f"{label} の終了コードが {expected_code}",
          run.returncode == expected_code, f"実際は {run.returncode}")
    if expected_out:
        check(f"{label} の出力",
              run.stdout == expected_out,
              f"期待: {expected_out!r} / 実際: {run.stdout!r}")

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}")
print("=============================")
if fail_count == 0:
    print("libc なしで printf 相当が動いた! 出力まわりが自分のものになった。")
if fail_count > 0:
    raise SystemExit(1)
