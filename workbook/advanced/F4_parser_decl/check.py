#!/usr/bin/env python3
"""F4 確認スクリプト — myparser.py を Step ごとにテストする

使い方:
    python3 check.py              # 同じディレクトリの myparser.py を確認
    python3 check.py path/to/myparser.py

Step 1 は型文字列を直接比べる。
Step 2 以降は、同じ入力を scaffold の Parser にも解析させて AST を構造比較する
(失敗時は両方の S 式を表示する)。
各 Step には「弾かれるべき入力」の確認も含まれる —
位置ごとの型検証(void 単独・struct 値)は、この回の主題そのものである。
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
            sig(n.init), sig(n.step), sig(n.body),
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


def check_error(label, mine_fn):
    """「弾かれるべき入力」がエラーになることを確認する。"""
    global pass_count, fail_count
    try:
        result = mine_fn()
    except SyntaxError:
        print(f"  [PASS] {label}(正しくエラー)")
        pass_count += 1
        return
    print(f"  [FAIL] {label} — エラーになるべきだが通ってしまった: {result!r}")
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


def mine(src):
    return myparser.ProgramParser(tokenize(src))


def scaffold(src):
    return ScaffoldParser(tokenize(src))


# ---------------------------------------------------------------
# Step 1: is_type_start / parse_base_and_stars / 位置ごとの型
# ---------------------------------------------------------------


def step1():
    check("is_type_start: int", mine("int x;").is_type_start(), True)
    check("is_type_start: struct", mine("struct Node n;").is_type_start(), True)
    check("is_type_start: 式の先頭", mine("x = 1;").is_type_start(), False)
    check("is_type_start: ただの識別子", mine("Point p;").is_type_start(), False)

    check("parse_base_and_stars: int **",
          mine("int **").parse_base_and_stars(), ("int", "**"))
    check("parse_base_and_stars: struct Node *",
          mine("struct Node *").parse_base_and_stars(), ("struct Node", "*"))

    # obj_type(変数宣言・sizeof の型名): struct 値は可、void 単独は不可
    check("obj_type: int", mine("int").parse_obj_type(), "int")
    check("obj_type: char *", mine("char *").parse_obj_type(), "char*")
    check("obj_type: struct Point(値)",
          mine("struct Point").parse_obj_type(), "struct Point")
    check_error("obj_type: void 単独", lambda: mine("void").parse_obj_type())

    # scalar_type(引数・フィールド): struct 値も void 単独も不可
    check("scalar_type: int *", mine("int *").parse_scalar_type(), "int*")
    check("scalar_type: void *", mine("void *").parse_scalar_type(), "void*")
    check_error("scalar_type: void 単独", lambda: mine("void").parse_scalar_type())
    check_error("scalar_type: struct 値",
                lambda: mine("struct Point").parse_scalar_type())

    check_error("型でないもの", lambda: mine("Point").parse_base_and_stars())


# ---------------------------------------------------------------
# Step 2: 局所宣言と関数本体
# ---------------------------------------------------------------

BODIES = [
    "{ int a; a = 1; return a; }",
    "{ int *p; char c; return 0; }",
    "{ struct Point p; p.x = 3; return p.x; }",
    "{ int x; if (x == 3) { x = x + 1; } return x; }",
    "{ int i; int s; s = 0; for (i = 0; i < 3; ++i) { s = s + i; } return s; }",
]


def step2():
    for src in BODIES:
        check_vs_scaffold(f"関数本体 {src[:32]!r}...",
                          lambda s=src: mine(s).parse_func_body(),
                          lambda s=src: scaffold(s).parse_func_body())
    check_error("void 型のローカル変数",
                lambda: mine("{ void v; return 0; }").parse_func_body())
    check_error("宣言は先頭のみ(途中の宣言は式文として読まれて落ちる)",
                lambda: mine("{ int a; a = 1; int b; return a; }").parse_func_body())


# ---------------------------------------------------------------
# Step 3: sizeof(型名形式のみ)
# ---------------------------------------------------------------

SIZEOFS = [
    "sizeof(int)",
    "sizeof(char *)",
    "sizeof(struct Node)",
    "sizeof(void *)",
    "sizeof(int) * 5",
]


def step3():
    for src in SIZEOFS:
        check_vs_scaffold(f"sizeof {src!r}",
                          lambda s=src: mine(s).parse_expr(),
                          lambda s=src: scaffold(s).parse_expr())
    check_error("sizeof x(式形式はない)", lambda: mine("sizeof x").parse_expr())
    check_error("sizeof(x)(式形式はない)", lambda: mine("sizeof(x)").parse_expr())
    check_error("sizeof(void)", lambda: mine("sizeof(void)").parse_expr())


# ---------------------------------------------------------------
# Step 4: 関数
# ---------------------------------------------------------------

FUNCS = [
    ("int", "add", "(int a, int b) { return a + b; }"),
    ("int", "main", "() { return 0; }"),
    ("int", "f", "(int x);"),
    ("int", "printf", "(char *fmt, ...);"),
    ("void", "g", "(int *p, char c) { *p = c; }"),
    ("struct Node*", "next_of", "(struct Node *n) { return n->next; }"),
]


def step4():
    for ty, name, rest in FUNCS:
        check_vs_scaffold(f"関数 {ty} {name}{rest[:25]!r}...",
                          lambda t=ty, n=name, r=rest:
                              mine(r).parse_func(t, n),
                          lambda t=ty, n=name, r=rest:
                              scaffold(r)._parse_func(t, n))
    check_error("引数 (void) は書けない",
                lambda: mine("(void) { return 0; }").parse_func("int", "main"))
    check_error("引数が struct 値",
                lambda: mine("(struct Point p);").parse_func("int", "f"))
    check_error("固定引数なしの ...",
                lambda: mine("(...);").parse_func("int", "f"))
    check_error("可変長の定義は書けない",
                lambda: mine("(char *fmt, ...) { return 0; }")
                        .parse_func("int", "f"))


# ---------------------------------------------------------------
# Step 5: struct 定義 / parse_program
# ---------------------------------------------------------------

PROGRAMS = [
    "int g; int main() { g = 1; return g; }",
    "char *msg; int main() { msg = \"hi\"; return 0; }",
    "int main() { int *p; p = malloc(sizeof(int) * 4); p[0] = 1; return p[0]; }",
    "struct Point { int x; int y; }; "
    "int main() { struct Point p; p.x = 3; return p.x; }",
    "struct Node; "
    "struct Node { int val; struct Node *next; }; "
    "struct Node *head; "
    "int main() { return 0; }",
    "int is_even(int n); int is_odd(int n); "
    "int is_even(int n) { if (n == 0) { return 1; } return is_odd(n - 1); } "
    "int is_odd(int n) { if (n == 0) { return 0; } return is_even(n - 1); } "
    "int main() { return is_even(10); }",
]

BAD_PROGRAMS = [
    ("空のプログラム", ""),
    ("void のグローバル変数", "void v; int main() { return 0; }"),
    ("struct 値の戻り値",
     "struct Point { int x; }; struct Point f() { struct Point p; return p; }"),
    ("フィールドが struct 値",
     "struct Inner { int x; }; struct Outer { struct Inner in; };"),
]


def step5():
    global pass_count, fail_count
    for src in PROGRAMS:
        def mine_prog(s=src):
            return myparser.ProgramParser(tokenize(s)).parse_program()

        def scaffold_prog(s=src):
            return ScaffoldParser(tokenize(s)).parse_program()

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

    for label, src in BAD_PROGRAMS:
        check_error(label, lambda s=src: mine(s).parse_program())


run_step("Step 1: 型 — is_type_start と位置ごとの 3 分類", step1)
run_step("Step 2: 局所宣言と関数本体", step2)
run_step("Step 3: sizeof", step3)
run_step("Step 4: 関数", step4)
run_step("Step 5: struct 定義 / parse_program", step5)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
