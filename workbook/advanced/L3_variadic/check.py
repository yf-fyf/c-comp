#!/usr/bin/env python3
"""L3 確認スクリプト — variadic.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの variadic.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("L3_variadic", passes_dir / "variadic.py")
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize   # noqa: E402
from parser import Parser    # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


class FakeCG:
    """alloc_local / emit / codegen だけを持つコード生成器もどき。"""

    def __init__(self, used=0):
        self.lines = []
        self._locals = {}
        self._stack_offset = used

    def emit(self, line):
        self.lines.append(line.strip())

    def codegen(self, node):
        self.emit(f'# eval {node.kind}')

    def alloc_local(self, name, ty):
        self._stack_offset += 8
        self._locals[name] = (-(16 + self._stack_offset), ty)


def expr(src):
    return Parser(tokenize(src)).parse_expr()


def check(label, ok, detail=""):
    global pass_count, fail_count
    if ok:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}{(' — ' + detail) if detail else ''}")
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
    cg = FakeCG()
    va.reserve_save_area(cg)
    check("8個のスロットを確保している", len(cg._locals) == 8, str(cg._locals))
    check("名前は __va0〜__va7",
          sorted(cg._locals) == sorted(va.SLOT_NAMES), str(sorted(cg._locals)))
    offs = [cg._locals[n][0] for n in va.SLOT_NAMES]
    check("8バイトずつ下がる連続した領域",
          all(offs[i] - offs[i + 1] == 8 for i in range(7)), str(offs))

    # すでに使われている領域の後ろに取れること
    cg2 = FakeCG(used=16)
    va.reserve_save_area(cg2)
    check("既存のローカル変数と重ならない",
          cg2._locals['__va0'][0] < -16 - 16, str(cg2._locals['__va0']))


def step2():
    cg = FakeCG()
    va.reserve_save_area(cg)
    base = va.save_area_base(cg)
    cg.lines = []
    va.gen_save_registers(cg)
    expected = [f'sd a{i}, {base - i * 8}(s0)' for i in range(8)]
    check("a0〜a7 を順に save area へ書き出す", cg.lines == expected, str(cg.lines))


def step3():
    cg = FakeCG()
    check("__arg(0) は対象", bool(va.is_arg_builtin(cg, expr("__arg(0)"))))
    check("__arg(i) も対象", bool(va.is_arg_builtin(cg, expr("__arg(i)"))))
    check("ほかの関数は対象外", not va.is_arg_builtin(cg, expr("foo(1)")))
    check("引数2個の __arg は対象外",
          not va.is_arg_builtin(cg, expr("__arg(1, 2)")))
    check("呼び出しでない式は対象外", not va.is_arg_builtin(cg, expr("x + 1")))

    va.reserve_save_area(cg)
    base = va.save_area_base(cg)
    cg.lines = []
    va.gen_arg_access(cg, expr("__arg(i)"))
    check("添字を評価している", cg.lines[0] == '# eval Var', str(cg.lines))
    check("8 倍している",
          'li a1, 8' in cg.lines and 'mul a0, a0, a1' in cg.lines, str(cg.lines))
    check("save area の先頭から引いている",
          f'li a1, {base}' in cg.lines and 'sub a0, a1, a0' in cg.lines,
          str(cg.lines))
    check("最後に ld で読み出す", cg.lines[-1] == 'ld a0, 0(a0)', str(cg.lines))


run_step("Step 1: reserve_save_area", step1)
run_step("Step 2: gen_save_registers", step2)
run_step("Step 3: is_arg_builtin / gen_arg_access", step3)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
