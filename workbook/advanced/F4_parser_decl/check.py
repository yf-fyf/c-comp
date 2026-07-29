#!/usr/bin/env python3
"""F4 確認スクリプト — myparser.py を Step ごとにテストする

使い方:
    python3 check.py              # 同じディレクトリの myparser.py を確認
    python3 check.py path/to/myparser.py

Step 1 は型文字列を直接比べる。
Step 2 以降は、同じ入力を scaffold の Parser にも解析させて AST を構造比較する
(失敗時は両方の S 式を表示する)。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
SCAFFOLD = DIR.parents[1] / "scaffold"

target = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR / "myparser.py"

spec = importlib.util.spec_from_file_location("myparser_f4", target)
myparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(myparser)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize                          # noqa: E402
from parser import Parser as ScaffoldParser         # noqa: E402
from parse_viewer import node_to_sexp, render_sexp  # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


def sig(n):
    if n is None:
        return None
    return (n.kind, n.val, n.sval, n.name, n.is_arrow, n.ty_str,
            sig(n.lhs), sig(n.rhs), sig(n.operand),
            sig(n.cond), sig(n.then), sig(n.else_),
            sig(n.init), sig(n.step), sig(n.body), sig(n.init_expr),
            tuple(sig(a) for a in n.args),
            tuple(sig(s) for s in n.stmts),
            tuple(sig(p) for p in n.params))


def sexpr(node):
    return " ".join(render_sexp(node_to_sexp(node)).split())


def check(label, actual, expected):
    global pass_count, fail_count
    if actual == expected:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label} — expected={expected!r}, got={actual!r}")
        fail_count += 1


def check_vs_scaffold(label, mine_fn, scaffold_fn):
    """自作と scaffold の結果ノードを構造比較する。"""
    global pass_count, fail_count
    expected_node = scaffold_fn()
    try:
        actual_node = mine_fn()
    except SyntaxError as e:
        print(f"  [FAIL] {label} — 自作パーサがエラー: {e}")
        fail_count += 1
        return
    if sig(actual_node) == sig(expected_node):
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label} — AST が scaffold と不一致")
        print(f"         scaffold: {sexpr(expected_node)}")
        print(f"         自作    : {sexpr(actual_node)}")
        fail_count += 1


def run_step(name, fn):
    global skip_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


def mine(src, typedefs=()):
    p = myparser.ProgramParser(tokenize(src))
    p.typedef_names = set(typedefs)
    return p


def scaffold(src, typedefs=()):
    p = ScaffoldParser(tokenize(src))
    p.typedef_names = set(typedefs)
    return p


# ---------------------------------------------------------------
# Step 1: parse_type / is_type_start
# ---------------------------------------------------------------


def step1():
    check("parse_type: int", mine("int").parse_type(), "int")
    check("parse_type: int **", mine("int **").parse_type(), "int**")
    check("parse_type: char *", mine("char *").parse_type(), "char*")
    check("parse_type: struct Node *",
          mine("struct Node *").parse_type(), "struct Node*")
    check("parse_type: typedef 名",
          mine("Point *", typedefs=["Point"]).parse_type(), "Point*")
    check("is_type_start: int", mine("int x;").is_type_start(), True)
    check("is_type_start: struct", mine("struct Node n;").is_type_start(), True)
    check("is_type_start: 式の先頭", mine("x = 1;").is_type_start(), False)
    check("is_type_start: typedef 名",
          mine("Point p;", typedefs=["Point"]).is_type_start(), True)
    check("is_type_start: 未登録の名前",
          mine("Point p;").is_type_start(), False)


# ---------------------------------------------------------------
# Step 2: 宣言とブロック
# ---------------------------------------------------------------

BLOCKS = [
    "{ int a; a = 1; return a; }",
    "{ int a = 42; return a; }",
    "{ int a[5]; int i; return a[i]; }",
    "{ int *p; char c; return 0; }",
    "{ int x; if (x == 3) { int y; y = 4; return x + y; } return 0; }",
]


def step2():
    for src in BLOCKS:
        check_vs_scaffold(f"ブロック {src[:30]!r}...",
                          lambda s=src: mine(s).parse_block(),
                          lambda s=src: scaffold(s).parse_block())


# ---------------------------------------------------------------
# Step 3: sizeof
# ---------------------------------------------------------------

SIZEOFS = [
    ("sizeof(int)", ()),
    ("sizeof(char *)", ()),
    ("sizeof(struct Node)", ()),
    ("sizeof(Node)", ("Node",)),
    ("sizeof(x)", ()),          # x は型ではない → sizeof 式
    ("sizeof x", ()),
    ("sizeof *p", ()),
    ("sizeof(Node) + 1", ("Node",)),
]


def step3():
    for src, tds in SIZEOFS:
        check_vs_scaffold(f"sizeof {src!r}",
                          lambda s=src, t=tds: mine(s, t).parse_expr(),
                          lambda s=src, t=tds: scaffold(s, t).parse_expr())


# ---------------------------------------------------------------
# Step 4: 関数
# ---------------------------------------------------------------

FUNCS = [
    ("int", "add", "(int a, int b) { return a + b; }"),
    ("int", "main", "() { return 0; }"),
    ("int", "main", "(void) { return 0; }"),
    ("int", "f", "(int x);"),
    ("int", "printf", "(char *fmt, ...);"),
    ("void", "g", "(int *p, char c) { *p = c; }"),
]


def step4():
    for ty, name, rest in FUNCS:
        check_vs_scaffold(f"関数 {ty} {name}{rest[:25]!r}...",
                          lambda t=ty, n=name, r=rest:
                              mine(r).parse_func(t, n),
                          lambda t=ty, n=name, r=rest:
                              scaffold(r)._parse_func(t, n))


# ---------------------------------------------------------------
# Step 5: parse_program / typedef / グローバル変数
# ---------------------------------------------------------------

PROGRAMS = [
    "int g; int main() { g = 1; return g; }",
    "int base = 7; int main() { return base; }",
    "int a[10]; int main() { return a[0]; }",
    "typedef int myint; int main() { myint x; x = 1; return x; }",
    "typedef struct { int x; int y; } Point; "
    "int main() { Point p; p.x = 3; return p.x; }",
    "typedef struct Node { int val; struct Node *next; } Node; "
    "int main() { Node *n; return 0; }",
    "int is_even(int n); int is_odd(int n); "
    "int is_even(int n) { if (n == 0) { return 1; } return is_odd(n - 1); } "
    "int is_odd(int n) { if (n == 0) { return 0; } return is_even(n - 1); } "
    "int main() { return is_even(10); }",
]


def step5():
    for src in PROGRAMS:
        def mine_prog(s=src):
            return myparser.ProgramParser(tokenize(s)).parse_program()

        def scaffold_prog(s=src):
            return ScaffoldParser(tokenize(s)).parse_program()

        global pass_count, fail_count
        expected = [sig(n) for n in scaffold_prog()]
        try:
            actual = [sig(n) for n in mine_prog()]
        except SyntaxError as e:
            print(f"  [FAIL] {src[:40]!r}... — 自作パーサがエラー: {e}")
            fail_count += 1
            continue
        if actual == expected:
            print(f"  [PASS] {src[:40]!r}...")
            pass_count += 1
        else:
            print(f"  [FAIL] {src[:40]!r}... — AST が scaffold と不一致")
            fail_count += 1


run_step("Step 1: parse_type / is_type_start", step1)
run_step("Step 2: 宣言とブロック", step2)
run_step("Step 3: sizeof", step3)
run_step("Step 4: 関数", step4)
run_step("Step 5: parse_program / typedef / グローバル変数", step5)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
