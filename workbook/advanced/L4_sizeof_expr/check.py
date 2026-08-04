#!/usr/bin/env python3
"""L4 確認スクリプト — sizeofexpr.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの sizeofexpr.py
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


comp = load("L4_sizeofexpr", passes_dir / "sizeofexpr.py")
langcc = load("L4_langcc", DIR / "langcc.py")

sys.path.insert(0, str(SCAFFOLD))   # scaffold の lexer / parser / ast_def を使う

pass_count = 0
fail_count = 0
skip_count = 0

_shims = {}


def shims():
    """構文の shim を1度だけ作る(字句は標準トラックのまま)。"""
    if not _shims:
        import lexer
        import parser as real_parser
        import ast_def
        _shims['lexer'] = lexer
        _shims['parser'] = langcc.install_parser_shim(real_parser, ast_def)
    return _shims


def expr(src):
    toks = shims()['lexer'].tokenize(src)
    return shims()['parser'].Parser(toks).parse_expr()


def operand(src):
    """'sizeof …' を読んで、そのオペランドのノードを返す。"""
    return expr(src).operand


# ---- 偽コード生成器 ----

class FakeCG:
    """本物のコード生成器の代わり。

    codegen が呼ばれた回数を数える。sizeof はオペランドを評価しないので、
    この回数は最後まで 0 でなければならない。
    """

    VARS = {'a': 'int', 'c': 'char', 'p': 'int*', 's': 'char*',
            'pt': 'struct Point', 'pp': 'struct Point*', 'v': 'void*'}
    MEMBERS = {'x': 'int', 'y': 'int'}
    STRUCTS = ('struct Point',)

    def __init__(self):
        self.lines = []
        self.codegen_calls = 0

    # --- 学習者が使ってよい部品 ---

    def emit(self, line):
        self.lines.append(line.strip())

    def type_size(self, ty):
        if ty.endswith('*'):
            return 8
        return {'char': 1, 'int': 4, 'struct Point': 8}.get(ty, 8)

    def is_ptr(self, ty):
        return ty.endswith('*')

    def elem_ty(self, ty):
        return ty[:-1] if ty.endswith('*') else ty

    def var_type(self, name, line=0):
        return self.VARS.get(name, 'int')

    def lval_type(self, node):
        if node.kind == 'Var':
            return self.var_type(node.name)
        if node.kind == 'Deref':
            return self.elem_ty(static(self, node.operand))
        if node.kind == 'Index':
            return self.elem_ty(static(self, node.lhs))
        if node.kind == 'Member':
            return self.MEMBERS.get(node.name, 'int')
        return 'int'

    def struct_tags(self):
        return self.STRUCTS

    # --- 呼ばれてはいけないもの ---

    def codegen(self, node):
        self.codegen_calls += 1
        self.lines.append('# codegen(評価してしまった)')

    def codegen_lval(self, node):
        self.codegen_calls += 1
        self.lines.append('# codegen_lval(評価してしまった)')


def static(cg, node):
    return comp.static_type_of(cg, node)


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


# ---- 構文(langcc.py が用意済み。実装前でも通る) ----

def syntax():
    node = expr("sizeof a")
    check("'sizeof a' は SizeofExpr になる",
          node.kind == langcc.ND_SIZEOF_EXPR, node.kind)
    check("オペランドは operand に付く",
          node.operand.kind == 'Var', node.operand.kind)

    tn = expr("sizeof(int)")
    check("'sizeof(int)' は従来どおり SizeofType のまま",
          tn.kind == 'SizeofType' and tn.ty_str == 'int',
          f"{tn.kind}/{tn.ty_str}")

    paren = expr("sizeof (a)")
    check("'sizeof (a)' は式形式(型キーワードで始まらないので)",
          paren.kind == langcc.ND_SIZEOF_EXPR and paren.operand.kind == 'Var',
          paren.kind)

    prec = expr("sizeof c + 1")
    check("'sizeof c + 1' は (sizeof c) + 1 と読まれる",
          prec.kind == 'Add' and prec.lhs.kind == langcc.ND_SIZEOF_EXPR,
          f"{prec.kind}/{prec.lhs.kind}")

    deref = expr("sizeof *p")
    check("'sizeof *p' のオペランドは Deref(丸ごと取る)",
          deref.operand.kind == 'Deref', deref.operand.kind)

    nest = expr("sizeof sizeof a")
    check("sizeof は入れ子にできる",
          nest.operand.kind == langcc.ND_SIZEOF_EXPR, nest.operand.kind)


# ---- Step 1: static_type_of ----

def step1():
    cases = [
        ("sizeof a", 'int', "変数(int)"),
        ("sizeof c", 'char', "変数(char)"),
        ("sizeof p", 'int*', "変数(ポインタ)"),
        ("sizeof pt", 'struct Point', "変数(構造体)"),
        ("sizeof *p", 'int', "間接参照は指す先の型"),
        ("sizeof *s", 'char', "char* の間接参照"),
        ("sizeof p[0]", 'int', "添字も指す先の型"),
        ("sizeof pt.x", 'int', "メンバ"),
        ("sizeof pp->y", 'int', "アロー"),
        ("sizeof &a", 'int*', "アドレス取得は1段深いポインタ"),
        ("sizeof &c", 'char*', "char のアドレス"),
        ('sizeof "abc"', 'char*', "文字列リテラルは char*"),
        ("sizeof (a + 1)", 'int', "int どうしの加算"),
        ("sizeof (p + 1)", 'int*', "ポインタ + int はポインタ"),
        ("sizeof (1 + p)", 'int*', "int + ポインタ もポインタ"),
        ("sizeof (p - 1)", 'int*', "ポインタ - int はポインタ"),
        ("sizeof (a = 1)", 'int', "代入式は左辺の型"),
        ("sizeof ++c", 'char', "前置 ++ は左辺の型"),
        ("sizeof -a", 'int', "単項 -"),
        ("sizeof (a < 1)", 'int', "比較は int"),
        ("sizeof f()", 'int', "関数呼び出しは int"),
        ("sizeof sizeof a", 'int', "sizeof 自身の型は int"),
        ("sizeof(int)", 'int', "型名形式のノードも int 扱いでよい"),
    ]
    for src, want, label in cases:
        cg = FakeCG()
        got = static(cg, operand(src) if src != "sizeof(int)" else expr(src))
        check(f"{label}: {src} → {want}", got == want, f"got {got!r}")

    cg = FakeCG()
    static(cg, operand("sizeof (a + f() + *p)"))
    check("型を求めるだけで命令を1行も出さない", cg.lines == [], str(cg.lines))
    check("型を求めるだけで codegen を呼ばない",
          cg.codegen_calls == 0, f"{cg.codegen_calls} 回")


# ---- Step 2: gen_sizeof_expr ----

def step2():
    for ty, want in (('int', 4), ('char', 1), ('int*', 8), ('char*', 8),
                     ('struct Point', 8)):
        cg = FakeCG()
        comp.gen_sizeof_expr(cg, ty)
        check(f"{ty} → li a0, {want}", cg.lines == [f'li a0, {want}'],
              str(cg.lines))

    cg = FakeCG()
    comp.gen_sizeof_expr(cg, 'int')
    check("出す命令は1つだけ", len(cg.lines) == 1, str(cg.lines))

    # 教育的核心: sizeof bump() で bump() が呼ばれてはならない
    cg = FakeCG()
    node = operand("sizeof bump()")
    ty = static(cg, node)
    comp.gen_sizeof_expr(cg, ty)
    check("sizeof bump() の答えは 4(int のサイズ)",
          cg.lines == ['li a0, 4'], str(cg.lines))
    check("sizeof bump() で codegen が0回(bump が呼ばれない)",
          cg.codegen_calls == 0, f"{cg.codegen_calls} 回")

    cg2 = FakeCG()
    node2 = operand("sizeof (a = 99)")
    comp.gen_sizeof_expr(cg2, static(cg2, node2))
    check("sizeof (a = 99) でも codegen が0回(代入が起きない)",
          cg2.codegen_calls == 0, f"{cg2.codegen_calls} 回")


# ---- Step 3: reject_incomplete ----

def step3():
    def rejects(ty):
        try:
            comp.reject_incomplete(FakeCG(), ty, 7)
        except NotImplementedError:
            raise
        except Exception as e:
            return True, str(e)
        return False, ""

    bad, msg = rejects('void')
    check("void は弾く", bad, "通ってしまった")
    if bad:
        check("エラーに行番号が入る", '7' in msg, msg)

    bad2, _ = rejects('struct Unknown')
    check("本体の無い構造体(不完全型)は弾く", bad2, "通ってしまった")

    for ty in ('int', 'char', 'int*', 'char*', 'void*', 'struct Point',
               'struct Point*', 'struct Unknown*'):
        ok, msg = rejects(ty)
        check(f"{ty} は通す", not ok, msg)


run_step("構文: SizeofExpr(langcc.py が用意済み)", syntax)
run_step("Step 1: static_type_of(オペランドの静的な型)", step1)
run_step("Step 2: gen_sizeof_expr(コード生成)", step2)
run_step("Step 3: reject_incomplete(不完全型を弾く)", step3)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
