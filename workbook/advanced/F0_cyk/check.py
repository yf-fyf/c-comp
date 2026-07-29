#!/usr/bin/env python3
"""F0 確認スクリプト — cyk.py を Step ごとにテストする

使い方:
    python3 check.py              # 同じディレクトリの cyk.py を確認
    python3 check.py path/to/cyk.py

未実装(NotImplementedError)の Step は [SKIP] になる。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
target = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR / "cyk.py"

spec = importlib.util.spec_from_file_location("cyk", target)
cyk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cyk)

pass_count = 0
fail_count = 0
skip_count = 0


def check(label, actual, expected):
    global pass_count, fail_count
    if actual == expected:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label} — expected={expected!r}, got={actual!r}")
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
# Step 1: tokenize
# ---------------------------------------------------------------


def step1():
    check("1+2*3",
          cyk.tokenize("1+2*3"),
          [("num", 1), ("+", None), ("num", 2), ("*", None), ("num", 3)])
    check("空白の読み飛ばし",
          cyk.tokenize("  1 +  2 "),
          [("num", 1), ("+", None), ("num", 2)])
    check("複数桁の数(最長一致)",
          cyk.tokenize("12 + 345"),
          [("num", 12), ("+", None), ("num", 345)])
    check("カッコ",
          cyk.tokenize("(1)"),
          [("(", None), ("num", 1), (")", None)])
    check("空文字列", cyk.tokenize(""), [])
    try:
        cyk.tokenize("1 @ 2")
        check("不正な文字で SyntaxError", "例外なし", "SyntaxError")
    except SyntaxError:
        check("不正な文字で SyntaxError", "SyntaxError", "SyntaxError")


# ---------------------------------------------------------------
# Step 2: cyk_chart(受理判定)
# ---------------------------------------------------------------

ACCEPT_CASES = [
    ("42", True),
    ("1 + 2", True),
    ("1 + 2 * 3", True),
    ("(1 + 2) * 3", True),
    ("((1))", True),
    ("1 + * 2", False),
    ("1 + 2)", False),
    ("(1 + 2", False),
    ("+ 1", False),
    ("1 2", False),
]


def step2():
    for src, expected in ACCEPT_CASES:
        tokens = cyk.tokenize(src)
        for gname, grammar in [("G1", cyk.GRAMMAR_AMBIG),
                               ("G2", cyk.GRAMMAR_PREC)]:
            check(f"受理判定 {gname}: {src!r}",
                  cyk.accepts(tokens, grammar), expected)


# ---------------------------------------------------------------
# Step 3: build_tree(G2 で一意な木を S 式に)
# ---------------------------------------------------------------

SEXPR_CASES = [
    ("42", "(num 42)"),
    ("1 + 2 * 3", "(add (num 1) (mul (num 2) (num 3)))"),
    ("1 * 2 + 3", "(add (mul (num 1) (num 2)) (num 3))"),
    ("(1 + 2) * 3", "(mul (add (num 1) (num 2)) (num 3))"),
    ("1 + 2 + 3", "(add (add (num 1) (num 2)) (num 3))"),
]


def step3():
    for src, expected in SEXPR_CASES:
        tokens = cyk.tokenize(src)
        chart = cyk.cyk_chart(tokens, cyk.GRAMMAR_PREC)
        tree = cyk.build_tree(chart, 0, len(tokens), "E")
        check(f"構文木 {src!r}", cyk.to_sexpr(cyk.to_ast(tree)), expected)


# ---------------------------------------------------------------
# Step 4: count_trees(曖昧性)
# ---------------------------------------------------------------

COUNT_CASES = [
    ("42", 1, 1),
    ("1 + 2", 1, 1),
    ("1 + 2 * 3", 2, 1),
    ("1 + 2 * 3 + 4", 5, 1),
    ("(1 + 2) * 3", 1, 1),
]


def step4():
    for src, expected_g1, expected_g2 in COUNT_CASES:
        tokens = cyk.tokenize(src)
        for gname, grammar, expected in [
            ("G1", cyk.GRAMMAR_AMBIG, expected_g1),
            ("G2", cyk.GRAMMAR_PREC, expected_g2),
        ]:
            chart = cyk.cyk_chart(tokens, grammar)
            check(f"木の本数 {gname}: {src!r}",
                  cyk.count_trees(chart, 0, len(tokens), "E"), expected)


# ---------------------------------------------------------------
# Step 5: eval_ast
# ---------------------------------------------------------------

EVAL_CASES = [
    ("42", 42),
    ("1 + 2 * 3", 7),
    ("(1 + 2) * 3", 9),
    ("2 * 3 + 4 * 5", 26),
    ("10 * (2 + 3)", 50),
]


def step5():
    for src, expected in EVAL_CASES:
        tokens = cyk.tokenize(src)
        chart = cyk.cyk_chart(tokens, cyk.GRAMMAR_PREC)
        ast = cyk.to_ast(cyk.build_tree(chart, 0, len(tokens), "E"))
        check(f"評価 {src!r}", cyk.eval_ast(ast), expected)


run_step("Step 1: tokenize", step1)
run_step("Step 2: cyk_chart(受理判定)", step2)
run_step("Step 3: build_tree(構文木の復元)", step3)
run_step("Step 4: count_trees(曖昧性)", step4)
run_step("Step 5: eval_ast(評価)", step5)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
