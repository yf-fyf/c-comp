#!/usr/bin/env python3
"""L2 確認スクリプト — initializer.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの initializer.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("L2_initializer",
                                              passes_dir / "initializer.py")
ini = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ini)

sys.path.insert(0, str(SCAFFOLD))
from ast_def import Node   # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


def num(v):
    return Node('Num', val=v)


def init_list(*vals):
    return Node('InitList', args=[num(v) for v in vals])


def string(s):
    return Node('Str', sval=s)


class FakeCG:
    def __init__(self):
        self.lines = []
        self.offsets = {'a': -24}

    def emit(self, line):
        self.lines.append(line.strip())

    def array_len(self, ty):
        if not ty.endswith(']'):
            return None
        return int(ty[ty.rindex('[') + 1:-1])

    def elem_size(self, ty):
        base = ty[:ty.rindex('[')] if ty.endswith(']') else ty
        return {'char': 1, 'int': 4}.get(base, 8)

    def const_value(self, node):
        return node.val

    def local_offset(self, name):
        return self.offsets[name]

    def store_insn(self, size):
        return {1: 'sb', 4: 'sw', 8: 'sd'}.get(size, 'sd')


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
    cg = FakeCG()
    check("{1,2,3} で int[3]",
          ini.init_values(cg, 'int[3]', init_list(1, 2, 3)), [1, 2, 3])
    check("{7} で int[5](足りない分は 0)",
          ini.init_values(cg, 'int[5]', init_list(7)), [7, 0, 0, 0, 0])
    check("{1,2,3,4} で int[2](多い分は捨てる)",
          ini.init_values(cg, 'int[2]', init_list(1, 2, 3, 4)), [1, 2])
    check('"hi" で char[4](NUL 終端 + 0 埋め)',
          ini.init_values(cg, 'char[4]', string('hi')), [104, 105, 0, 0])
    check('"hello" で char[6]',
          ini.init_values(cg, 'char[6]', string('hello')),
          [104, 101, 108, 108, 111, 0])
    check("{} で int[3](全部 0)",
          ini.init_values(cg, 'int[3]', Node('InitList', args=[])), [0, 0, 0])


def step2():
    cg = FakeCG()
    decl = Node('Decl', name='a', ty_str='int[3]', init_expr=init_list(1, 2, 3))
    ini.gen_local_init(cg, decl)
    check("要素ごとに li → アドレス計算 → sw",
          cg.lines,
          ['li a0, 1', 'addi a1, s0, -24', 'sw a0, 0(a1)',
           'li a0, 2', 'addi a1, s0, -20', 'sw a0, 0(a1)',
           'li a0, 3', 'addi a1, s0, -16', 'sw a0, 0(a1)'])

    cg2 = FakeCG()
    decl2 = Node('Decl', name='a', ty_str='char[3]', init_expr=string('hi'))
    ini.gen_local_init(cg2, decl2)
    check("char 配列では sb を使い、1 バイトずつ進む",
          cg2.lines,
          ['li a0, 104', 'addi a1, s0, -24', 'sb a0, 0(a1)',
           'li a0, 105', 'addi a1, s0, -23', 'sb a0, 0(a1)',
           'li a0, 0', 'addi a1, s0, -22', 'sb a0, 0(a1)'])


def step3():
    cg = FakeCG()
    check("int[4] は .word で並べる",
          ini.global_init_data(cg, 'int[4]', init_list(10, 20, 30, 40)),
          ['  .word 10', '  .word 20', '  .word 30', '  .word 40'])
    check("char[3] は .byte で並べる",
          ini.global_init_data(cg, 'char[3]', string('hi')),
          ['  .byte 104', '  .byte 105', '  .byte 0'])
    check("足りない分は 0 で埋める",
          ini.global_init_data(cg, 'int[3]', init_list(5)),
          ['  .word 5', '  .word 0', '  .word 0'])


run_step("Step 1: init_values", step1)
run_step("Step 2: gen_local_init", step2)
run_step("Step 3: global_init_data", step3)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
