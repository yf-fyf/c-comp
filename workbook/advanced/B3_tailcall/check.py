#!/usr/bin/env python3
"""B3 確認スクリプト — tailcall.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの tailcall.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("B3_tailcall", passes_dir / "tailcall.py")
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize            # noqa: E402
from parser import Parser             # noqa: E402
from ast_def import Node, ND_DECL     # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


class FakeCG:
    """末尾呼び出しの生成に必要な最小限のコード生成器もどき。"""

    def __init__(self, func_name, params):
        self.lines = []
        self.tc_func_name = func_name
        self.tc_params = [Node(ND_DECL, name=p, ty_str='int') for p in params]
        self.tc_label = f'.Ltc_{func_name}'
        self._locals = {p: (-24 - 8 * i, 'int') for i, p in enumerate(params)}
        self._depth = 0

    def emit(self, line):
        self.lines.append(line.strip())

    def codegen(self, node):
        self.emit(f'# eval {node.kind}')

    def _push_a0(self):
        self.emit('push a0')
        self._depth += 1

    def _pop_into(self, reg):
        self._depth -= 1
        self.emit(f'pop {reg}')


def parse_stmt(src):
    return Parser(tokenize(src)).parse_stmt()


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


# ---------------------------------------------------------------
# Step 1: is_self_tail_call
# ---------------------------------------------------------------


def step1():
    cg = FakeCG('sum_to', ['n', 'acc'])
    check("自分自身への末尾呼び出し",
          tc.is_self_tail_call(cg, parse_stmt("return sum_to(n - 1, acc + n);")), True)
    check("別の関数の呼び出しは対象外",
          tc.is_self_tail_call(cg, parse_stmt("return helper(n, acc);")), False)
    check("呼び出しの後に演算が残る形は対象外",
          tc.is_self_tail_call(cg, parse_stmt("return sum_to(n - 1, acc) + 1;")), False)
    check("ただの値を返す return は対象外",
          tc.is_self_tail_call(cg, parse_stmt("return acc;")), False)
    check("値なしの return は対象外",
          tc.is_self_tail_call(cg, parse_stmt("return;")), False)
    check("return 以外の文は対象外",
          tc.is_self_tail_call(cg, parse_stmt("x = sum_to(n, acc);")), False)
    check("引数の個数が違う呼び出しは対象外",
          tc.is_self_tail_call(cg, parse_stmt("return sum_to(n);")), False)

    cg9 = FakeCG('f', [f'p{i}' for i in range(9)])
    args = ", ".join(f'p{i}' for i in range(9))
    check("引数9個(レジスタに収まらない)は対象外",
          tc.is_self_tail_call(cg9, parse_stmt(f"return f({args});")), False)


# ---------------------------------------------------------------
# Step 2: gen_tail_call
# ---------------------------------------------------------------


def step2():
    cg = FakeCG('sum_to', ['n', 'acc'])
    tc.gen_tail_call(cg, parse_stmt("return sum_to(n - 1, acc + n);"))
    expected = [
        '# eval Sub', 'push a0',       # 第1引数を評価して退避
        '# eval Add', 'push a0',       # 第2引数を評価して退避
        'pop a1', 'pop a0',            # 逆順に取り出す
        'sd a0, -24(s0)',              # n のスロットへ
        'sd a1, -32(s0)',              # acc のスロットへ
        'j .Ltc_sum_to',
    ]
    check("引数の評価 → 詰め替え → ジャンプ", cg.lines, expected)
    check("push と pop の数が合っている", cg._depth, 0)

    cg2 = FakeCG('loop', ['i'])
    tc.gen_tail_call(cg2, parse_stmt("return loop(i + 1);"))
    check("引数1個の場合",
          cg2.lines,
          ['# eval Add', 'push a0', 'pop a0', 'sd a0, -24(s0)', 'j .Ltc_loop'])

    check("最後は必ずジャンプで終わる(call を出さない)",
          any('call' in l for l in cg.lines + cg2.lines), False)


run_step("Step 1: is_self_tail_call", step1)
run_step("Step 2: gen_tail_call", step2)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
