#!/usr/bin/env python3
"""F2 確認スクリプト — myparser.py を Step ごとにテストする

使い方:
    python3 check.py              # 同じディレクトリの myparser.py を確認
    python3 check.py path/to/myparser.py

期待値は parse_viewer.py と同じ S 式で書いてある。
Step 1(parse_primary)が未実装の間は全 Step が SKIP になる。
まだ実装していない Step のテストは「式の後にトークンが余っています」等の
FAIL になるが、それは「素通しのまま」という意味なので順に埋めていけばよい。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
SCAFFOLD = DIR.parents[1] / "scaffold"

target = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR / "myparser.py"

spec = importlib.util.spec_from_file_location("myparser", target)
myparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(myparser)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize                          # noqa: E402
from parse_viewer import node_to_sexp, render_sexp  # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


def sexpr(node):
    """S 式を1行に正規化した文字列にする。"""
    return " ".join(render_sexp(node_to_sexp(node)).split())


def check_expr(src, expected):
    global pass_count, fail_count
    try:
        actual = sexpr(myparser.parse_expression(tokenize(src)))
    except SyntaxError as e:
        print(f"  [FAIL] {src!r}")
        print(f"         expected: {expected}")
        print(f"         got     : エラー: {e}")
        fail_count += 1
        return
    if actual == expected:
        print(f"  [PASS] {src!r}")
        pass_count += 1
    else:
        print(f"  [FAIL] {src!r}")
        print(f"         expected: {expected}")
        print(f"         got     : {actual}")
        fail_count += 1


def check_error(label, src):
    global pass_count, fail_count
    try:
        myparser.parse_expression(tokenize(src))
        print(f"  [FAIL] {label} — SyntaxError になるべき入力が通ってしまった")
        fail_count += 1
    except SyntaxError:
        print(f"  [PASS] {label}")
        pass_count += 1


def run_step(name, fn):
    global skip_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


# ---------------------------------------------------------------
# Step 1: parse_primary(リテラル・変数・カッコ)
# ---------------------------------------------------------------


def step1():
    check_expr("42", '(num 42)')
    check_expr("'a'", '(num 97)')
    check_expr('"hi"', '(str "hi")')
    check_expr("x", '(var "x")')
    check_expr("(42)", '(num 42)')
    check_expr("((x))", '(var "x")')
    check_error("閉じカッコがない", "(1")
    check_error("式がない", ")")


# ---------------------------------------------------------------
# Step 2: parse_mul / parse_add(左結合ループ)
# ---------------------------------------------------------------


def step2():
    check_expr("1 + 2 * 3", '(add (num 1) (mul (num 2) (num 3)))')
    check_expr("1 * 2 + 3", '(add (mul (num 1) (num 2)) (num 3))')
    check_expr("a - b - c", '(sub (sub (var "a") (var "b")) (var "c"))')
    check_expr("100 / 4 % 7", '(mod (div (num 100) (num 4)) (num 7))')
    check_expr("(1 + 2) * 3", '(mul (add (num 1) (num 2)) (num 3))')
    check_error("右辺がない", "1 +")


# ---------------------------------------------------------------
# Step 3: 残りの二項レベル(parse_binary への共通化と rel の swap)
# ---------------------------------------------------------------


def step3():
    check_expr("a < b", '(lt (var "a") (var "b"))')
    check_expr("a > b", '(lt (var "b") (var "a"))')
    check_expr("a <= b", '(le (var "a") (var "b"))')
    check_expr("a >= b", '(le (var "b") (var "a"))')
    check_expr("a == b != c",
               '(ne (eq (var "a") (var "b")) (var "c"))')
    check_expr("1 << 2 + 3", '(shl (num 1) (add (num 2) (num 3)))')
    check_expr("a < b << c",
               '(lt (var "a") (shl (var "b") (var "c")))')
    check_expr("a == b & c",
               '(bitand (eq (var "a") (var "b")) (var "c"))')
    check_expr("a & b ^ c | d",
               '(bitor (bitxor (bitand (var "a") (var "b")) (var "c")) (var "d"))')
    check_expr("a && b || c && d",
               '(or (and (var "a") (var "b")) (and (var "c") (var "d")))')


# ---------------------------------------------------------------
# Step 4: parse_unary / parse_postfix / 関数呼び出し
# ---------------------------------------------------------------


def step4():
    check_expr("-x", '(neg (var "x"))')
    check_expr("-1 + 2", '(add (neg (num 1)) (num 2))')
    check_expr("!x", '(not (var "x"))')
    check_expr("~x", '(bitnot (var "x"))')
    check_expr("*p", '(deref (var "p"))')
    check_expr("&x", '(addr (var "x"))')
    check_expr("*&x", '(deref (addr (var "x")))')
    check_expr("a[i]", '(index (var "a") (var "i"))')
    check_expr("a[i][j]",
               '(index (index (var "a") (var "i")) (var "j"))')
    check_expr("p->next->val",
               '(member "->" "val" (member "->" "next" (var "p")))')
    check_expr("s.x", '(member "." "x" (var "s"))')
    check_expr("f()", '(call "f" (args))')
    check_expr("f(1, 2 + 3)",
               '(call "f" (args (num 1) (add (num 2) (num 3))))')
    check_expr("g(f(x))",
               '(call "g" (args (call "f" (args (var "x")))))')
    check_expr("*p + 1", '(add (deref (var "p")) (num 1))')
    check_error("閉じ ] がない", "a[1")


# ---------------------------------------------------------------
# Step 5: parse_assign(右結合)
# ---------------------------------------------------------------


def step5():
    check_expr("a = 1", '(assign (var "a") (num 1))')
    check_expr("a = b = c",
               '(assign (var "a") (assign (var "b") (var "c")))')
    check_expr("*p = 5", '(assign (deref (var "p")) (num 5))')
    check_expr("a[i] = v",
               '(assign (index (var "a") (var "i")) (var "v"))')
    check_expr("p->x = 0",
               '(assign (member "->" "x" (var "p")) (num 0))')
    check_expr("sum = sum + a[i]",
               '(assign (var "sum") (add (var "sum") (index (var "a") (var "i"))))')


run_step("Step 1: parse_primary(リテラル・変数・カッコ)", step1)
run_step("Step 2: parse_mul / parse_add(左結合ループ)", step2)
run_step("Step 3: 残りの二項レベルと rel の正規化", step3)
run_step("Step 4: 単項・postfix・関数呼び出し", step4)
run_step("Step 5: 代入(右結合)", step5)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
