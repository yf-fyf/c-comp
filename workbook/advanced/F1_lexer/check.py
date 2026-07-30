#!/usr/bin/env python3
"""F1 確認スクリプト — mylexer.py を Step ごとにテストする

使い方:
    python3 check.py              # 同じディレクトリの mylexer.py を確認
    python3 check.py path/to/mylexer.py

未実装(NotImplementedError)の Step は [SKIP] になる。
Step 1〜4 は (kind, val, sval) のみを比べ、Step 5 で行番号まで比べる。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
SCAFFOLD = DIR.parents[1] / "scaffold"

target = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR / "mylexer.py"

spec = importlib.util.spec_from_file_location("mylexer", target)
mylexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mylexer)

sys.path.insert(0, str(SCAFFOLD))
import lexer as scaffold_lexer  # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


def sig3(tokens):
    return [(t.kind, t.val, t.sval) for t in tokens]


def sig4(tokens):
    return [(t.kind, t.val, t.sval, t.line) for t in tokens]


def check(label, actual, expected):
    global pass_count, fail_count
    if actual == expected:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}")
        print(f"         expected={expected!r}")
        print(f"         got     ={actual!r}")
        fail_count += 1


def check_tokens(label, src, expected):
    """expected は (kind, val, sval) のリスト。末尾の EOF は自動で足す。"""
    expected = list(expected) + [("TK_EOF", 0, "")]
    check(label, sig3(mylexer.tokenize(src)), expected)


def check_error(label, src):
    global pass_count, fail_count
    try:
        mylexer.tokenize(src)
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
# Step 1: 空白・コメント・数
# ---------------------------------------------------------------


def step1():
    check_tokens("数1個", "42", [("TK_NUM", 42, "")])
    check_tokens("空白の読み飛ばし", "  12 \t 345 ",
                 [("TK_NUM", 12, ""), ("TK_NUM", 345, "")])
    check_tokens("行コメント", "1 // comment\n2",
                 [("TK_NUM", 1, ""), ("TK_NUM", 2, "")])
    check_tokens("ブロックコメント", "1 /* a\n b */ 2",
                 [("TK_NUM", 1, ""), ("TK_NUM", 2, "")])
    check_tokens("空文字列", "", [])
    check_error("終端しないブロックコメント", "1 /* comment")


# ---------------------------------------------------------------
# Step 2: 識別子・キーワード
# ---------------------------------------------------------------


def step2():
    check_tokens("キーワードと識別子", "int a",
                 [("TK_KW", 0, "int"), ("TK_IDENT", 0, "a")])
    check_tokens("_ で始まる識別子", "_tmp",
                 [("TK_IDENT", 0, "_tmp")])
    check_tokens("キーワードが前につく識別子", "if ifx return returned",
                 [("TK_KW", 0, "if"), ("TK_IDENT", 0, "ifx"),
                  ("TK_KW", 0, "return"), ("TK_IDENT", 0, "returned")])
    check_tokens("英数字の混在", "x1 var_2",
                 [("TK_IDENT", 0, "x1"), ("TK_IDENT", 0, "var_2")])


# ---------------------------------------------------------------
# Step 3: 記号(最長一致)
# ---------------------------------------------------------------


def step3():
    check_tokens("2文字演算子", "a <= b",
                 [("TK_IDENT", 0, "a"), ("TK_PUNCT", 0, "<="),
                  ("TK_IDENT", 0, "b")])
    check_tokens("<= と < = の区別", "a < = b",
                 [("TK_IDENT", 0, "a"), ("TK_PUNCT", 0, "<"),
                  ("TK_PUNCT", 0, "="), ("TK_IDENT", 0, "b")])
    check_tokens("アロー演算子", "p->next",
                 [("TK_IDENT", 0, "p"), ("TK_PUNCT", 0, "->"),
                  ("TK_IDENT", 0, "next")])
    check_tokens("シフトと比較", "a << 2 >= b",
                 [("TK_IDENT", 0, "a"), ("TK_PUNCT", 0, "<<"),
                  ("TK_NUM", 2, ""), ("TK_PUNCT", 0, ">="),
                  ("TK_IDENT", 0, "b")])
    check_tokens("可変長引数の ...", "int printf(char *fmt, ...);",
                 [("TK_KW", 0, "int"), ("TK_IDENT", 0, "printf"),
                  ("TK_PUNCT", 0, "("), ("TK_KW", 0, "char"),
                  ("TK_PUNCT", 0, "*"), ("TK_IDENT", 0, "fmt"),
                  ("TK_PUNCT", 0, ","), ("TK_PUNCT", 0, "..."),
                  ("TK_PUNCT", 0, ")"), ("TK_PUNCT", 0, ";")])
    check_tokens("a-->b はどうなるか", "a-->b",
                 [("TK_IDENT", 0, "a"), ("TK_PUNCT", 0, "-"),
                  ("TK_PUNCT", 0, "->"), ("TK_IDENT", 0, "b")])
    check_error("未知の文字", "a @ b")


# ---------------------------------------------------------------
# Step 4: 文字・文字列リテラル
# ---------------------------------------------------------------


def step4():
    check_tokens("文字リテラル", "'a'", [("TK_CHAR", 97, "")])
    check_tokens("エスケープ文字", "'\\n' '\\0' '\\\\'",
                 [("TK_CHAR", 10, ""), ("TK_CHAR", 0, ""),
                  ("TK_CHAR", 92, "")])
    check_tokens("文字列リテラル", '"hi"', [("TK_STR", 0, "hi")])
    check_tokens("エスケープ入り文字列", '"x=%d\\n"',
                 [("TK_STR", 0, "x=%d\n")])
    check_tokens("タブと引用符", '"a\\tb\\"c"',
                 [("TK_STR", 0, 'a\tb"c')])
    check_error("終端しない文字列", '"abc')
    check_error("終端しない文字リテラル", "'a")


# ---------------------------------------------------------------
# Step 5: 行番号(scaffold と完全一致)
# ---------------------------------------------------------------

STEP5_SNIPPETS = [
    "int main() {\n    // comment\n    return 42;\n}\n",
    "1 /* a\n b\n c */ 2\n3",
    'char *s;\ns = "a\\nb";\n',
    "int x;\n\n\nint y;\n",
]


def step5():
    for src in STEP5_SNIPPETS:
        expected = sig4(scaffold_lexer.tokenize(src))
        actual = sig4(mylexer.tokenize(src))
        check(f"行番号つき比較 {src[:20]!r}...", actual, expected)


run_step("Step 1: 空白・コメント・数", step1)
run_step("Step 2: 識別子・キーワード", step2)
run_step("Step 3: 記号(最長一致)", step3)
run_step("Step 4: 文字・文字列リテラル", step4)
run_step("Step 5: 行番号", step5)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
