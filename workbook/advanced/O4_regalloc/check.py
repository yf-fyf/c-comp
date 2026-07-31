#!/usr/bin/env python3
"""O4 確認スクリプト — regalloc.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの regalloc.py
    python3 check.py path/to/answers_dir
"""

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O4_regalloc" / "regalloc.py").is_file():
    passes_dir = passes_dir / "O4_regalloc"

spec = importlib.util.spec_from_file_location("O4_regalloc", passes_dir / "regalloc.py")
ra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ra)

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


class N:
    """テスト用の AST ノード(本物と同じく kind と属性を持つ)。"""

    def __init__(self, kind, **kw):
        self.kind = kind
        for k, v in kw.items():
            setattr(self, k, v)


class FakeCG:
    """テスト用のコード生成器。emit された行を集める。"""

    def __init__(self, locals_=None):
        self.out = []
        self._locals = locals_ or {}

    def emit(self, line):
        self.out.append(line.strip())

    def codegen(self, node):
        self.out.append(f'<{node.kind} を生成>')


# int *p; int x; int *a;
#   p = &x;
#   f(&a[0]);
FUNC = N('FuncDef', name='main', params=[], body=N('Block', stmts=[
    N('ExprStmt', expr=N('Assign', lhs=N('Var', name='p'),
                         rhs=N('Addr', operand=N('Var', name='x')))),
    N('ExprStmt', expr=N('Call', name='f', args=[
        N('Addr', operand=N('Index', lhs=N('Var', name='a'),
                            rhs=N('Num', val=0)))])),
]))

# 呼び出しを含まない関数: n = n + 1; を2回
LEAF = N('FuncDef', name='inc', params=[], body=N('Block', stmts=[
    N('ExprStmt', expr=N('Assign', lhs=N('Var', name='n'),
                         rhs=N('Add', lhs=N('Var', name='n'),
                               rhs=N('Num', val=1)))),
    N('ExprStmt', expr=N('Assign', lhs=N('Var', name='n'),
                         rhs=N('Add', lhs=N('Var', name='n'),
                               rhs=N('Num', val=1)))),
]))

LOCALS = {
    'n': (-24, 'int'),
    's': (-32, 'char*'),
    'pt': (-56, 'struct Point'),
    'q': (-64, 'struct Point*'),
    'x': (-72, 'int'),
}


# ---------------------------------------------------------------
# Step 1: escaped_vars
# ---------------------------------------------------------------


def step1():
    check("&x を取られた変数を見つける", ra.escaped_vars(FUNC), {'x'})
    check("&a[0] は Var ではないので a は入らない",
          'a' in ra.escaped_vars(FUNC), False)
    check("& が無ければ空", ra.escaped_vars(LEAF), set())


# ---------------------------------------------------------------
# Step 2: promotable
# ---------------------------------------------------------------


def step2():
    check("int とポインタだけ残る",
          ra.promotable(LOCALS, set()), ['n', 's', 'q', 'x'])
    check("struct 値は外れる", 'pt' in ra.promotable(LOCALS, set()), False)
    check("struct へのポインタは残る", 'q' in ra.promotable(LOCALS, set()), True)
    check("アドレスを取られた変数は外れる",
          ra.promotable(LOCALS, {'x'}), ['n', 's', 'q'])
    check("全部外れることもある",
          ra.promotable({'pt': (-8, 'struct Point')}, set()), [])

    check("レジスタを順に割り当てる", ra.assign(['n', 's']),
          {'n': 's1', 's': 's2'})
    check("11個を超えたぶんはメモリのまま",
          len(ra.assign([f'v{i}' for i in range(15)])), 11)


# ---------------------------------------------------------------
# Step 3: emit_var_read / emit_var_assign
# ---------------------------------------------------------------


def step3():
    cg = FakeCG()
    ra.emit_var_read(cg, 's1')
    check("読み出しは mv 1命令", cg.out, ['mv a0, s1'])

    node = N('Assign', lhs=N('Var', name='n'), rhs=N('Add'))
    cg = FakeCG(LOCALS)
    ra.emit_var_assign(cg, node, 's1')
    check("int への代入: 右辺を生成してから sext.w",
          cg.out, ['<Add を生成>', 'sext.w s1, a0'])

    node = N('Assign', lhs=N('Var', name='s'), rhs=N('Num'))
    cg = FakeCG(LOCALS)
    ra.emit_var_assign(cg, node, 's2')
    check("ポインタへの代入は mv(切り詰めない)",
          cg.out, ['<Num を生成>', 'mv s2, a0'])

    check("store_op: int は sext.w", ra.store_op('int'), 'sext.w')
    check("store_op: ポインタは mv", ra.store_op('char*'), 'mv')


# ---------------------------------------------------------------
# Step 4: save_restore
# ---------------------------------------------------------------


def step4():
    cg = FakeCG({'__save_s1': (-40, 'long'), '__save_s2': (-48, 'long')})
    ra.save_restore(cg, ['s1', 's2'], 'sd')
    check("退避", cg.out, ['sd s1, -40(s0)', 'sd s2, -48(s0)'])

    cg = FakeCG({'__save_s1': (-40, 'long'), '__save_s2': (-48, 'long')})
    ra.save_restore(cg, ['s1', 's2'], 'ld')
    check("復帰", cg.out, ['ld s1, -40(s0)', 'ld s2, -48(s0)'])

    cg = FakeCG({})
    ra.save_restore(cg, [], 'sd')
    check("使うレジスタが無ければ何も出さない", cg.out, [])


# ---------------------------------------------------------------
# Step 5: assign_counts / has_call
# ---------------------------------------------------------------


def step5():
    check("代入回数を数える", ra.assign_counts(LEAF), {'n': 2})
    check("代入されない変数は表に入らない",
          ra.assign_counts(FUNC), {'p': 1})
    check("呼び出しがある", ra.has_call(FUNC), True)
    check("葉関数", ra.has_call(LEAF), False)


# ---------------------------------------------------------------
# Step 6: worth_promoting
# ---------------------------------------------------------------


def step6():
    check("葉関数は退避が要らないので全部置く",
          ra.worth_promoting(['n', 'x'], {'n': 2}, False), ['n', 'x'])
    check("呼び出しがあるなら、代入される変数だけ",
          ra.worth_promoting(['n', 'x'], {'n': 2}, True), ['n'])
    check("代入が無ければ1つも残らない(fib の n がこれ)",
          ra.worth_promoting(['n'], {}, True), [])


# ---------------------------------------------------------------
# 通し: decide_promotions
# ---------------------------------------------------------------


def step7():
    prom = ra.decide_promotions({'p': (-24, 'int *'), 'x': (-32, 'int')}, FUNC)
    check("&x を取られた x は入らず、p だけがレジスタへ",
          prom, {'p': 's1'})


# ---------------------------------------------------------------
# 提供コード: 前置 ++/--(patch が横取りする。実装 Step ではない)
# ---------------------------------------------------------------


def step8():
    class FakeCls:
        """patch() を当てる先のダミーのコード生成クラス。"""

        def __init__(self, locals_, prom):
            self.out = []
            self._locals = locals_
            self._prom = prom
            self._struct_defs = {}

        def emit(self, line):
            self.out.append(line.strip())

        def codegen(self, node):
            self.out.append(f'<{node.kind} を生成>')

        def gen_func(self, node):
            pass

    # mycc.py の型サイズ関数のうち、patch が使う2つだけを真似る
    MYCC = SimpleNamespace(
        size_of_ty_str=lambda ty, defs=None:
            8 if ty.endswith('*') else (1 if ty == 'char' else 4),
        elem_ty_str=lambda ty: ty[:-1] if ty.endswith('*') else ty,
    )
    ra.patch(FakeCls, MYCC)
    locals_ = {'i': (-24, 'int'), 'p': (-32, 'int*'), 'k': (-40, 'int')}
    prom = {'i': 's1', 'p': 's2'}

    cg = FakeCls(locals_, prom)
    FakeCls.codegen(cg, N('PreInc', operand=N('Var', name='i')))
    check("昇格した int の ++ はレジスタを直接進める(値は新しい値)",
          cg.out, ['addiw s1, s1, 1', 'mv a0, s1'])

    cg = FakeCls(locals_, prom)
    FakeCls.codegen(cg, N('PreDec', operand=N('Var', name='i')))
    check("昇格した int の -- も同じ経路",
          cg.out, ['addiw s1, s1, -1', 'mv a0, s1'])

    cg = FakeCls(locals_, prom)
    FakeCls.codegen(cg, N('PreInc', operand=N('Var', name='p')))
    check("昇格したポインタの ++ は要素サイズだけ進む",
          cg.out, ['addi s2, s2, 4', 'mv a0, s2'])

    cg = FakeCls(locals_, prom)
    FakeCls.codegen(cg, N('PreInc', operand=N('Var', name='k')))
    check("昇格していない変数は元の生成に任せる",
          cg.out, ['<PreInc を生成>'])


run_step("Step 1: escaped_vars", step1)
run_step("Step 2: promotable / assign", step2)
run_step("Step 3: emit_var_read / emit_var_assign", step3)
run_step("Step 4: save_restore", step4)
run_step("Step 5: assign_counts / has_call", step5)
run_step("Step 6: worth_promoting", step6)
run_step("通し: decide_promotions", step7)
run_step("提供コード: 前置 ++/--", step8)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
