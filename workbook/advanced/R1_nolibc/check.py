#!/usr/bin/env python3
"""R1 確認スクリプト — libc なしのビルドと実行を確認する

使い方:
    python3 check.py                 # 同じディレクトリの hello.s / tests
    python3 check.py path/to/dir     # 別ディレクトリ(教員用参照実装など)

Step 1: hello.s が "Hello, no libc!" を表示し、終了コード 42 を返す
Step 2: mycc がコンパイルした C を syscall.s とリンクして libc なしで動かす

編集対象がアセンブリなので、未実装は `TODO(...)` コメントで表してある。
TODO が残っている間は、その Step を SKIP として報告する（他系列で
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
COMPILER = Path(os.environ.get("R1_COMPILER", WORKBOOK / "final" / "mycc.py"))

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


def skip(label, detail):
    global skip_count
    print(f"  [SKIP] 未実装: {label} — {detail}")
    skip_count += 1


def exit_detail(code):
    """終了コードの説明。負の値はシグナルによる異常終了である。"""
    if code < 0:
        return (f"実際は {code}(シグナル {-code} で異常終了。"
                "終了コードを返す前に落ちている)")
    return f"実際は {code}"


def check(label, ok, detail=""):
    global pass_count, fail_count
    if ok:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}{(' — ' + detail) if detail else ''}")
        fail_count += 1


def build_and_run(asm_files, label):
    """-nostdlib でリンクして qemu で実行し、(exit code, stdout) を返す。"""
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "a.out"
        r = subprocess.run([GCC, "-nostdlib", "-static", *map(str, asm_files),
                            "-o", str(exe)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [FAIL] {label} — リンクに失敗:\n{r.stderr.strip()[:400]}")
            return None
        run = subprocess.run([QEMU, str(exe)], capture_output=True, text=True)
        return run.returncode, run.stdout


for tool in (GCC, QEMU):
    if shutil.which(tool) is None:
        print(f"{tool} が見つかりません。docker/rv64 環境で実行してください。",
              file=sys.stderr)
        raise SystemExit(2)

# ---------------------------------------------------------------
# Step 1: hello.s 単体
# ---------------------------------------------------------------
print("--- Step 1: hello.s(libc なしの Hello World)---")
hello = src_dir / "hello.s"
if not hello.is_file():
    check("hello.s がある", False, f"{hello} が見つからない")
elif remaining_todos(hello):
    skip("hello.s",
         f"{hello.name} に TODO が残っている({', '.join(remaining_todos(hello))})。"
         "ecall を1つも発行しないので、実行してもシグナルで落ちるだけになる")
else:
    got = build_and_run([hello], "hello.s")
    if got is not None:
        code, out = got
        check("終了コードが 42", code == 42, exit_detail(code))
        check("Hello, no libc! と表示される",
              out.strip() == "Hello, no libc!", f"実際の出力: {out!r}")

# ---------------------------------------------------------------
# Step 2: mycc の出力 + syscall.s
# ---------------------------------------------------------------
print("--- Step 2: 自作コンパイラの出力を libc なしで動かす ---")
syscall_s = src_dir / "syscall.s"
if not COMPILER.is_file():
    print(f"  [SKIP] コンパイラが見つからない: {COMPILER}")
elif not syscall_s.is_file():
    check("syscall.s がある", False, f"{syscall_s} が見つからない")
else:
    for csrc in sorted(TESTS.glob("*.c")):
        ans = int(csrc.with_suffix(".ans").read_text().strip())
        expected_out = csrc.with_suffix(".stdout")
        expected_out = expected_out.read_text() if expected_out.exists() else ""
        r = subprocess.run([sys.executable, str(COMPILER), str(csrc)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            check(f"{csrc.name} のコンパイル", False, r.stderr.strip()[:200])
            continue
        with tempfile.TemporaryDirectory() as tmp:
            asm = Path(tmp) / "prog.s"
            asm.write_text(r.stdout)
            got = build_and_run([asm, syscall_s], csrc.name)
        if got is None:
            continue
        code, out = got
        check(f"{csrc.name} の終了コードが {ans}", code == ans, exit_detail(code))
        if expected_out:
            check(f"{csrc.name} の出力", out == expected_out,
                  f"実際の出力: {out!r}")

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")
if fail_count == 0 and skip_count == 0:
    print("libc なしで動いた! gcc とライブラリに任せていた部分が1つ減った。")
if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
    print("hello.s の TODO を埋めてから、もう一度 check.py を回す。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
