#!/usr/bin/env python3
"""S3 確認スクリプト — ptrdiff.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの ptrdiff.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("S3_ptrdiff", passes_dir / "ptrdiff.py")
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize   # noqa: E402
from parser import Parser    # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0

SIZES = {'int': 4, 'char': 1, 'Pair': 8}


class FakeCG:
    """型と emit だけを持つコード生成器もどき。変数の型は types で与える。"""

    def __init__(self, types):
        self.lines = []
        self.types = types
        self._struct_defs = {}

    def emit(self, line):
        self.lines.append(line.strip())

    def codegen(self, node):
        self.emit(f'# eval {node.kind}')

    def _push_a0(self):
        self.emit('push a0')

    def _pop_into(self, reg):
        self.emit(f'pop {reg}')

    def _type_of_expr(self, node):
        if node.kind == 'Var':
            return self.types.get(node.name, 'int')
        if node.kind == 'Num':
            return 'int'
        return 'int'

    @staticmethod
    def size_of_ty_str(ty, struct_defs=None):
        return SIZES.get(ty, 8 if ty.endswith('*') else 4)


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
    cg = FakeCG({'p': 'int*', 'q': 'int*', 'i': 'int', 's': 'char*'})
    check("int* - int* は対象", pd.is_ptr_diff(cg, expr("p - q")) is True)
    check("char* - char* は対象", bool(pd.is_ptr_diff(cg, expr("s - s"))))
    check("ポインタ - 整数は対象外", not pd.is_ptr_diff(cg, expr("p - 3")))
    check("整数 - 整数は対象外", not pd.is_ptr_diff(cg, expr("i - i")))
    check("足し算は対象外", not pd.is_ptr_diff(cg, expr("p + q")))
    check("整数 - ポインタは対象外", not pd.is_ptr_diff(cg, expr("i - p")))


def step2():
    cg = FakeCG({'p': 'int*', 'q': 'int*'})
    pd.gen_ptr_diff(cg, expr("q - p"))
    check("退避・復元・引き算の順になっている",
          cg.lines[:5] == ['# eval Var', 'push a0', '# eval Var',
                           'pop a1', 'sub a0, a1, a0'],
          str(cg.lines))
    check("要素サイズ 4 で割っている",
          cg.lines[5:] == ['li a1, 4', 'div a0, a0, a1'], str(cg.lines))

    cg2 = FakeCG({'s': 'char*'})
    pd.gen_ptr_diff(cg2, expr("s - s"))
    check("char* では割らない(要素サイズが 1)",
          not any(l.startswith('div') for l in cg2.lines), str(cg2.lines))

    cg3 = FakeCG({'a': 'Pair*', 'b': 'Pair*'})
    pd.gen_ptr_diff(cg3, expr("a - b"))
    check("構造体ポインタでは 8 で割っている",
          'li a1, 8' in cg3.lines, str(cg3.lines))


run_step("Step 1: is_ptr_diff", step1)
run_step("Step 2: gen_ptr_diff", step2)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
