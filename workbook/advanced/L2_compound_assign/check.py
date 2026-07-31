#!/usr/bin/env python3
"""L2 確認スクリプト — compound.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの compound.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


comp = load("L2_compound", passes_dir / "compound.py")
langcc = load("L2_langcc", DIR / "langcc.py")

sys.path.insert(0, str(SCAFFOLD))   # scaffold の lexer / parser / ast_def を使う

pass_count = 0
fail_count = 0
skip_count = 0

# 拡張前の2文字演算子(scaffold の lexer.TWO_CHAR_PUNCTS)
BASE_PUNCTS = ['==', '!=', '<=', '>=', '&&', '||', '->', '++', '--']

_shims = {}


def shims():
    """字句と構文の shim を1度だけ作る(字句は Step 1 の実装を使う)。"""
    if not _shims:
        lexer = langcc.install_lexer_shim(comp)
        import parser as real_parser          # 字句を差し替えたあとに読む
        import ast_def
        parser = langcc.install_parser_shim(real_parser, ast_def)
        _shims['lexer'] = lexer
        _shims['parser'] = parser
    return _shims


def tokens_of(src):
    return shims()['lexer'].tokenize(src)


def token_texts(src):
    """トークン列を見た目の文字列にする(数値は val 側に入っている)。"""
    return [t.sval if t.sval else str(t.val)
            for t in tokens_of(src) if t.kind != 'TK_EOF']


def expr(src):
    return shims()['parser'].Parser(tokens_of(src)).parse_expr()


# ---- Step 3 用の偽コード生成器 ----

class FakeCG:
    """本物のコード生成器の代わり。呼ばれた順に印を残す。"""

    def __init__(self, types=None):
        self.lines = []
        self.types = types or {}

    def emit(self, line):
        self.lines.append(line.strip())

    def _note_calls(self, node):
        """部分木に関数呼び出しがあれば、評価された印を残す。"""
        if node is None:
            return
        if node.kind == 'Call':
            self.emit(f'# call {node.name}')
        for child in (node.lhs, node.rhs, node.operand):
            self._note_calls(child)

    def codegen_lval(self, node):
        self.emit('# lval')
        self._note_calls(node)

    def codegen(self, node):
        if node.kind == 'Num':
            self.emit(f'li a0, {node.val}')
        else:
            self.emit('# expr')
            self._note_calls(node)

    def push_a0(self):
        self.emit('push a0')

    def pop_into(self, reg):
        self.emit(f'pop {reg}')

    def load_ty(self, ty):
        self.emit({1: 'lb', 4: 'lw'}.get(self._size(ty), 'ld') + ' a0, 0(a0)')

    def store_ty(self, ty):
        self.emit({1: 'sb', 4: 'sw'}.get(self._size(ty), 'sd') + ' a0, 0(a1)')

    def lval_type(self, node):
        if node.kind == 'Var':
            return self.types.get(node.name, 'int')
        if node.kind == 'Deref':
            inner = self.types.get(getattr(node.operand, 'name', ''), 'int*')
            return inner[:-1] if inner.endswith('*') else inner
        return 'int'

    def ptr_elem_size(self, ty):
        return self._size(ty[:-1]) if ty.endswith('*') else 0

    @staticmethod
    def _size(ty):
        if ty.endswith('*'):
            return 8
        return {'char': 1, 'int': 4}.get(ty, 8)


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
    puncts = comp.extend_puncts(list(BASE_PUNCTS))
    check("5つの複合代入演算子が入っている",
          all(op in puncts for op in ('+=', '-=', '*=', '/=', '%=')),
          str(puncts))
    check("元の2文字演算子が消えていない",
          all(op in puncts for op in BASE_PUNCTS), str(puncts))

    toks = token_texts("x += 1;")
    check("'x += 1;' が x / += / 1 / ; の4トークンになる",
          toks == ['x', '+=', '1', ';'], str(toks))

    toks2 = token_texts("++x; y += 1;")
    check("'++' と '+=' が取り違えられない",
          toks2 == ['++', 'x', ';', 'y', '+=', '1', ';'], str(toks2))

    toks3 = token_texts("a % b; a %= b;")
    check("1文字の '%' も従来どおり読める",
          toks3 == ['a', '%', 'b', ';', 'a', '%=', 'b', ';'], str(toks3))


def step2():
    node = expr("x += 1")
    check("'x += 1' は CompoundAssign になる", node.kind == 'CompoundAssign',
          node.kind)
    check("演算子は sval に入る", node.sval == '+=', repr(node.sval))
    check("左辺・右辺が lhs / rhs に付く",
          node.lhs.kind == 'Var' and node.rhs.kind == 'Num',
          f"{node.lhs.kind}/{node.rhs.kind}")

    ops = [expr(f"x {op} 1").sval for op in ('-=', '*=', '/=', '%=')]
    check("残り4つの演算子も読める", ops == ['-=', '*=', '/=', '%='], str(ops))

    chain = expr("a += b += c")
    check("右結合(a += (b += c))",
          chain.rhs.kind == 'CompoundAssign' and chain.lhs.kind == 'Var',
          f"{chain.lhs.kind}/{chain.rhs.kind}")

    plain = expr("x = 1")
    check("ふつうの代入は Assign のまま", plain.kind == 'Assign', plain.kind)

    mixed = expr("x += y == 1")
    check("右辺は比較まで含めて読む(x += (y == 1))",
          mixed.rhs.kind == 'Eq', mixed.rhs.kind)


def step3():
    cg = FakeCG({'x': 'int'})
    comp.gen_compound_assign(cg, expr("x += 3"))
    check("アドレス → 値 → 右辺 → 演算 → 書き戻しの順",
          cg.lines == ['# lval', 'push a0', 'lw a0, 0(a0)', 'push a0',
                       'li a0, 3', 'pop a1', 'add a0, a1, a0',
                       'pop a1', 'sw a0, 0(a1)'],
          str(cg.lines))

    insns = []
    for op in ('-=', '*=', '/=', '%='):
        cg2 = FakeCG({'x': 'int'})
        comp.gen_compound_assign(cg2, expr(f"x {op} 3"))
        insns.append(next((l.split()[0] for l in cg2.lines
                           if l.split()[0] in ('add', 'sub', 'mul', 'div', 'rem')), '?'))
    check("演算子ごとに命令が変わる", insns == ['sub', 'mul', 'div', 'rem'],
          str(insns))

    cg3 = FakeCG({'p': 'int*'})
    comp.gen_compound_assign(cg3, expr("p += 2"))
    check("ポインタは要素サイズ倍してから足す",
          'li a1, 4' in cg3.lines and 'mul a0, a0, a1' in cg3.lines,
          str(cg3.lines))
    check("ポインタは8バイトで読み書きする",
          'ld a0, 0(a0)' in cg3.lines and 'sd a0, 0(a1)' in cg3.lines,
          str(cg3.lines))

    cg4 = FakeCG({'s': 'char*'})
    comp.gen_compound_assign(cg4, expr("s += 2"))
    check("char* は要素サイズ1なので掛け算を出さない",
          not any(l.startswith('mul') for l in cg4.lines), str(cg4.lines))

    cg5 = FakeCG({})
    comp.gen_compound_assign(cg5, expr("*bump() += 1"))
    check("左辺のアドレス計算は1回だけ",
          cg5.lines.count('# lval') == 1, str(cg5.lines))
    check("左辺の関数呼び出しも1回だけ",
          cg5.lines.count('# call bump') == 1, str(cg5.lines))


run_step("Step 1: extend_puncts(字句の拡張)", step1)
run_step("Step 2: 構文(CompoundAssign ノード)", step2)
run_step("Step 3: gen_compound_assign(コード生成)", step3)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
