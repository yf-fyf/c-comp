#!/usr/bin/env python3
"""F3 確認スクリプト — myparser.py を Step ごとにテストする

使い方:
    python3 check.py              # 同じディレクトリの myparser.py を確認
    python3 check.py path/to/myparser.py

期待値は parse_viewer.py と同じ S 式で書いてある。
F2(式パーサ)が未完成の場合も SKIP になるので、先に F2 を完成させること。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
SCAFFOLD = DIR.parents[1] / "scaffold"

target = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR / "myparser.py"

spec = importlib.util.spec_from_file_location("myparser_f3", target)
myparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(myparser)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize                          # noqa: E402
from parse_viewer import node_to_sexp, render_sexp  # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


def sexpr(node):
    return " ".join(render_sexp(node_to_sexp(node)).split())


def check_stmt(src, expected):
    global pass_count, fail_count
    try:
        actual = sexpr(myparser.parse_statement(tokenize(src)))
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
        myparser.parse_statement(tokenize(src))
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
# Step 1: 単純な文(return / break / continue / 式文 / 空文)
# ---------------------------------------------------------------


def step1():
    check_stmt("return 42;", '(return (num 42))')
    check_stmt("return;", '(return)')
    check_stmt("return a + b;",
               '(return (add (var "a") (var "b")))')
    check_stmt("break;", '(break)')
    check_stmt("continue;", '(continue)')
    check_stmt("x = 1;",
               '(exprstmt (assign (var "x") (num 1)))')
    check_stmt("f(1, 2);",
               '(exprstmt (call "f" (args (num 1) (num 2))))')
    check_stmt(";", '(exprstmt)')
    check_error("';' がない", "return 42")
    check_error("break の後に ';' がない", "break")


# ---------------------------------------------------------------
# Step 2: ブロック
# ---------------------------------------------------------------


def step2():
    check_stmt("{ }", '(block)')
    check_stmt("{ ; }", '(block (exprstmt))')
    check_stmt("{ x = 1; return x; }",
               '(block (exprstmt (assign (var "x") (num 1))) (return (var "x")))')
    check_stmt("{ { return 1; } }",
               '(block (block (return (num 1))))')
    check_error("'}' がない", "{ return 1;")


# ---------------------------------------------------------------
# Step 3: if(dangling else)
# ---------------------------------------------------------------


def step3():
    check_stmt("if (x) return 1;",
               '(if (cond (var "x")) (then (return (num 1))))')
    check_stmt("if (a > b) return a; else return b;",
               '(if (cond (lt (var "b") (var "a")))'
               ' (then (return (var "a")))'
               ' (else (return (var "b"))))')
    check_stmt("if (a) { x = 1; } else { x = 2; }",
               '(if (cond (var "a"))'
               ' (then (block (exprstmt (assign (var "x") (num 1)))))'
               ' (else (block (exprstmt (assign (var "x") (num 2))))))')
    # dangling else: else は最も内側の if につく
    check_stmt("if (a) if (b) return 1; else return 2;",
               '(if (cond (var "a"))'
               ' (then (if (cond (var "b"))'
               ' (then (return (num 1)))'
               ' (else (return (num 2))))))')
    check_stmt("if (a) return 1; else if (b) return 2; else return 3;",
               '(if (cond (var "a"))'
               ' (then (return (num 1)))'
               ' (else (if (cond (var "b"))'
               ' (then (return (num 2)))'
               ' (else (return (num 3))))))')
    check_error("条件のカッコがない", "if x return 1;")


# ---------------------------------------------------------------
# Step 4: while / for
# ---------------------------------------------------------------


def step4():
    check_stmt("while (i < 10) i = i + 1;",
               '(while (cond (lt (var "i") (num 10)))'
               ' (body (exprstmt (assign (var "i") (add (var "i") (num 1))))))')
    check_stmt("while (x) { break; }",
               '(while (cond (var "x")) (body (block (break))))')
    check_stmt("for (i = 0; i < 5; i = i + 1) sum = sum + i;",
               '(for (init (assign (var "i") (num 0)))'
               ' (cond (lt (var "i") (num 5)))'
               ' (step (assign (var "i") (add (var "i") (num 1))))'
               ' (body (exprstmt (assign (var "sum") (add (var "sum") (var "i"))))))')
    check_stmt("for (;;) break;",
               '(for (init none) (cond none) (step none) (body (break)))')
    check_stmt("for (; i < 3;) i = i + 1;",
               '(for (init none) (cond (lt (var "i") (num 3))) (step none)'
               ' (body (exprstmt (assign (var "i") (add (var "i") (num 1))))))')


run_step("Step 1: 単純な文", step1)
run_step("Step 2: ブロック", step2)
run_step("Step 3: if と dangling else", step3)
run_step("Step 4: while / for", step4)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
