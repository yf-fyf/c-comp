#!/usr/bin/env python3
"""R2 確認スクリプト — 自前 printf を libc なしで動かして確認する

使い方:
    python3 check.py                 # 同じディレクトリの myprintf.c
    python3 check.py path/to/dir     # 別ディレクトリ(教員用参照実装など)

各テストは次の手順で確認する。
    1. 自作コンパイラで myprintf.c と tests/*.c をアセンブリに変換
    2. syscall.s と一緒に -nostdlib でリンク(libc は使わない)
    3. qemu で実行し、標準出力と終了コードを .stdout / .ans と比較

編集対象が C なので、未実装は `TODO(...)` コメントで表してある。
TODO が残っている間は、テストを回さず SKIP として報告する（他系列で
`NotImplementedError` を SKIP にしているのと同じ扱い）。
"""

import os
import re
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
skip_count = 0

TODO_RE = re.compile(r"TODO\(([^)]*)\)")


def remaining_todos(path):
    """未実装マーカー `TODO(...)` の見出しを、現れた順に重複なく返す。

    `TODO(Step 1, Step 2)` のように1つのマーカーが複数の Step を指すことがあるので、
    読点で割ってから重複を落とす。
    """
    labels = []
    for group in TODO_RE.findall(path.read_text(encoding="utf-8")):
        for label in re.split(r"[,、]", group):
            label = label.strip()
            if label and label not in labels:
                labels.append(label)
    return labels


def exit_detail(code):
    """終了コードの説明。負の値はシグナルによる異常終了である。"""
    if code < 0:
        return (f"実際は {code}(シグナル {-code} で異常終了。"
                "終了コードを返す前に落ちている)")
    return f"実際は {code}"


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

todos = remaining_todos(impl)

for csrc in sorted(TESTS.glob("*.c")):
    label = csrc.name
    if todos:
        print(f"  [SKIP] 未実装: {label} — {impl.name} に TODO が残っている"
              f"({', '.join(todos)})")
        skip_count += 1
        continue
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
          run.returncode == expected_code, exit_detail(run.returncode))
    if expected_out:
        check(f"{label} の出力",
              run.stdout == expected_out,
              f"期待: {expected_out!r} / 実際: {run.stdout!r}")

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")
if fail_count == 0 and skip_count == 0:
    print("libc なしで printf 相当が動いた! 出力まわりが自分のものになった。")
if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
    print(f"{impl.name} の TODO を埋めてから、もう一度 check.py を回す。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
