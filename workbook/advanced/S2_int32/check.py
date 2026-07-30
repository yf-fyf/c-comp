#!/usr/bin/env python3
"""S2 確認スクリプト — narrow.py をテストする

使い方:
    python3 check.py                      # 同じディレクトリの narrow.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("s2_narrow", passes_dir / "narrow.py")
nr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nr)

pass_count = 0
fail_count = 0
skip_count = 0


def check(label, actual, expected):
    global pass_count, fail_count
    if actual == expected:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}")
        print(f"         expected: {expected!r}")
        print(f"         got     : {actual!r}")
        fail_count += 1


def run_step(name, fn):
    global skip_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


def step1():
    # int の算術は 32bit 版へ
    check("add → addw", nr.narrow('  add a0, a1, a0', 'int'), '  addw a0, a1, a0')
    check("sub → subw", nr.narrow('  sub a0, a1, a0', 'int'), '  subw a0, a1, a0')
    check("mul → mulw", nr.narrow('  mul a0, a1, a0', 'int'), '  mulw a0, a1, a0')
    check("div → divw", nr.narrow('  div a0, a1, a0', 'int'), '  divw a0, a1, a0')
    check("rem → remw", nr.narrow('  rem a0, a1, a0', 'int'), '  remw a0, a1, a0')
    check("sll → sllw", nr.narrow('  sll a0, a1, a0', 'int'), '  sllw a0, a1, a0')
    check("sra → sraw", nr.narrow('  sra a0, a1, a0', 'int'), '  sraw a0, a1, a0')
    check("neg → negw", nr.narrow('  neg a0, a0', 'int'), '  negw a0, a0')
    check("char も32bit扱い",
          nr.narrow('  add a0, a1, a0', 'char'), '  addw a0, a1, a0')

    # 触ってはいけないもの
    check("ポインタ型は変えない",
          nr.narrow('  add a0, a1, a0', 'int*'), '  add a0, a1, a0')
    check("型が不明(None)なら変えない",
          nr.narrow('  add a0, a1, a0', None), '  add a0, a1, a0')
    check("addi は変えない(アドレス計算に使う)",
          nr.narrow('  addi sp, sp, -8', 'int'), '  addi sp, sp, -8')
    check("ld は変えない",
          nr.narrow('  ld a0, 0(sp)', 'int'), '  ld a0, 0(sp)')
    check("li は変えない",
          nr.narrow('  li a0, 42', 'int'), '  li a0, 42')
    check("call は変えない",
          nr.narrow('  call fib', 'int'), '  call fib')
    check("ラベルは変えない", nr.narrow('.L3:', 'int'), '.L3:')
    check("ディレクティブは変えない",
          nr.narrow('  .globl main', 'int'), '  .globl main')
    check("空行は変えない", nr.narrow('', 'int'), '')

    # インデントを保つ
    check("インデントを保つ",
          nr.narrow('    add a0, a1, a0', 'int'), '    addw a0, a1, a0')


run_step("Step 1: narrow", step1)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
