#!/usr/bin/env python3
"""コマ1 確認スクリプト — RV64 の実行と AST の構造を確認"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")
QEMU = os.environ.get("QEMU", "qemu-riscv64")
DIR = Path(__file__).resolve().parent
ROOT = DIR.parent.parent

gcc_bin = shutil.which(GCC)
if gcc_bin is None:
    print(f"gcc not found: {GCC}", file=sys.stderr)
    raise SystemExit(2)

qemu_bin = shutil.which(QEMU)
if qemu_bin is None:
    print(f"qemu not found: {QEMU}", file=sys.stderr)
    raise SystemExit(2)

fail_count = 0


def check_assembly(label: str, source: Path, expected: int) -> None:
    global fail_count
    with tempfile.NamedTemporaryFile(suffix=".out", delete=False) as tmp:
        bin_path = Path(tmp.name)

    try:
        compile_result = subprocess.run(
            [gcc_bin, "-static", str(source), "-o", str(bin_path)],
            capture_output=True,
            text=True,
        )
        if compile_result.returncode != 0:
            print(f"[FAIL] {label} — assemble/link error")
            if compile_result.stderr.strip():
                print(compile_result.stderr.strip())
            fail_count += 1
            return
        actual = subprocess.run([qemu_bin, str(bin_path)], capture_output=True).returncode
    finally:
        bin_path.unlink(missing_ok=True)

    if actual == expected:
        print(f"[PASS] {label} exit code = {expected}")
    else:
        print(f"[FAIL] {label} exit code: expected={expected}, got={actual}")
        fail_count += 1


check_assembly("hello.s", DIR / "hello.s", 42)
for name in ("sub", "three_numbers"):
    expected = int((DIR / "tests" / f"{name}.ans").read_text().strip())
    check_assembly(f"tests/{name}.s", DIR / "tests" / f"{name}.s", expected)

sys.path.insert(0, str(ROOT / "scaffold"))
try:
    from lexer import preprocess, tokenize
    from parser import parse

    ast_source = ROOT / "sessions" / "02_interpreter" / "tests" / "add_mul.c"
    source = preprocess(ast_source.read_text(), str(ast_source))
    program = parse(tokenize(source, str(ast_source)))
    main = next(node for node in program if node.kind == "FuncDef" and node.name == "main")
    expression = main.body.stmts[0].operand
    if expression.kind == "Add" and expression.rhs.kind == "Mul":
        print("[PASS] add_mul.c AST: Add の右部分木が Mul")
    else:
        print("[FAIL] add_mul.c AST: Add の右部分木が Mul ではありません")
        fail_count += 1
except Exception as error:
    print(f"[FAIL] add_mul.c AST — {error}")
    fail_count += 1

if fail_count:
    raise SystemExit(1)
