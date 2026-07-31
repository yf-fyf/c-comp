#!/usr/bin/env python3
"""L1 確認スクリプト — structcopy.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの structcopy.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("L1_structcopy",
                                              passes_dir / "structcopy.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize   # noqa: E402
from parser import Parser    # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0

STRUCTS = {
    'struct Point': {'size': 8, 'align': 4,
                      'fields': {'x': (0, 'int'), 'y': (4, 'int')}},
    # 'struct Line' は R-17(2026-07-31)によりポインタ・フィールド版へ再設計。
    # フィールドは int・char・ポインタのみという新仕様の制約により、struct 値の
    # 入れ子(旧: 'a': (0, 'struct Point') 等)はもう書けない。
    'struct Line': {'size': 16, 'align': 8,
                     'fields': {'a': (0, 'struct Point*'), 'b': (8, 'struct Point*')}},
    # 'struct Small' は参照実装の自然整列では発生しないレイアウト(char の後に
    # int が続くと本来はパディングが入る)。ここでは端数バイトのコピー
    # (sw + sb)を検査するための合成フィクスチャとして size=5・align=1 のまま維持する。
    'struct Small': {'size': 5, 'align': 1,
                      'fields': {'c': (0, 'char'), 'n': (1, 'int')}},
}


class FakeCG:
    def __init__(self, types):
        self.lines = []
        self.types = types
        self._struct_defs = STRUCTS

    def emit(self, line):
        self.lines.append(line.strip())

    def codegen_lval(self, node):
        self.emit(f'# lval {node.kind}')

    def _push_a0(self):
        self.emit('push a0')

    def _pop_into(self, reg):
        self.emit(f'pop {reg}')

    def _type_of_lval(self, node):
        if node.kind == 'Var':
            return self.types.get(node.name, 'int')
        if node.kind == 'Deref':
            inner = self.types.get(node.operand.name, 'int')
            return inner[:-1] if inner.endswith('*') else inner
        if node.kind == 'Member':
            base = self._type_of_lval(node.operand)
            info = STRUCTS.get(base)
            if info and node.name in info['fields']:
                return info['fields'][node.name][1]
        return 'int'


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
    cg = FakeCG({'p': 'struct Point', 'q': 'struct Point', 'l': 'struct Line',
                 'i': 'int', 'ptr': 'struct Point*'})
    check("構造体同士の代入は対象", bool(sc.is_struct_assign(cg, expr("q = p"))))
    check("ポインタ経由も対象",
          bool(sc.is_struct_assign(cg, expr("*ptr = p"))))
    # R-17(2026-07-31): struct フィールドは int・char・ポインタのみで、
    # struct 値の入れ子は書けない。'l.a' は 'struct Point*' というポインタ・
    # フィールドなので、代入は構造体コピーではなく「ただのポインタ代入」になる。
    check("ポインタ・フィールドへの代入は対象外(ポインタ代入)",
          not sc.is_struct_assign(cg, expr("l.a = ptr")))
    check("int の代入は対象外", not sc.is_struct_assign(cg, expr("i = 1")))
    check("メンバ(int)の代入は対象外",
          not sc.is_struct_assign(cg, expr("p.x = 1")))
    check("ポインタ変数の代入は対象外",
          not sc.is_struct_assign(cg, expr("ptr = ptr")))
    check("代入でない式は対象外", not sc.is_struct_assign(cg, expr("p.x + 1")))


def step2():
    cg = FakeCG({'p': 'struct Point', 'q': 'struct Point'})
    sc.gen_struct_copy(cg, expr("q = p"))
    check("左辺→退避→右辺→復元の順",
          cg.lines[:4] == ['# lval Var', 'push a0', '# lval Var', 'pop a1'],
          str(cg.lines))
    check("8バイト1回でコピーしている(Point は 8 バイト)",
          cg.lines[4:6] == ['ld a2, 0(a0)', 'sd a2, 0(a1)'], str(cg.lines))
    check("最後に mv a0, a1 で左辺のアドレスを残す",
          cg.lines[-1] == 'mv a0, a1', str(cg.lines))

    cg2 = FakeCG({'l': 'struct Line', 'm': 'struct Line'})
    sc.gen_struct_copy(cg2, expr("m = l"))
    n_sd = sum(1 for l in cg2.lines if l.startswith('sd '))
    check("16 バイトは sd 2回でコピー", n_sd == 2, str(cg2.lines))

    cg3 = FakeCG({'a': 'struct Small', 'b': 'struct Small'})
    sc.gen_struct_copy(cg3, expr("b = a"))
    kinds = [l.split()[0] for l in cg3.lines if l[:2] in ('sd', 'sw', 'sb')]
    check("5 バイトは sw 1回 + sb 1回", kinds == ['sw', 'sb'], str(cg3.lines))


run_step("Step 1: is_struct_assign", step1)
run_step("Step 2: gen_struct_copy", step2)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
