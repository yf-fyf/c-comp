#!/usr/bin/env python3
"""F2 golden test — 式のコーパスで scaffold の Parser と AST を突き合わせる

使い方:
    python3 golden.py               # 同じディレクトリの myparser.py を確認
    python3 golden.py path/to/myparser.py
    python3 golden.py -v            # 全件の結果を表示(既定は FAIL のみ)

各式を scaffold の Parser と自作パーサの両方で解析し、
AST を構造で比較する(line は比較しない)。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
SCAFFOLD = DIR.parents[1] / "scaffold"

args = sys.argv[1:]
verbose = "-v" in args
args = [a for a in args if a != "-v"]
target = Path(args[0]) if args else DIR / "myparser.py"

spec = importlib.util.spec_from_file_location("myparser", target)
myparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(myparser)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize, TK_EOF        # noqa: E402
from parser import Parser                 # noqa: E402

# 式コーパス: 全演算子・優先順位の組み合わせ・結合方向・postfix の連鎖
EXPRESSIONS = [
    # リテラル・変数
    "42", "'a'", "'\\n'", '"hello"', '"x=%d\\n"', "x", "(42)",
    # 算術と優先順位
    "1 + 2 * 3", "1 * 2 + 3", "(1 + 2) * 3", "(100 - 3 * 7) / 4 + 1",
    "a - b - c", "a / b / c", "10 % 3 % 2", "1 + 2 + 3 + 4",
    # 単項
    "-x", "- - x", "!x", "!!x", "~x", "~ -x", "-1 + 2", "-(a + b)",
    "*p", "&x", "*&x", "&*p", "**pp", "-*p",
    # 比較(swap 含む)・等値
    "a < b", "a > b", "a <= b", "a >= b", "a == b", "a != b",
    "a < b == c < d", "a > b != c >= d", "x == 0",
    # シフト・ビット演算
    "1 << 2", "x >> 1", "1 << 2 + 3", "a << b >> c",
    "a & b", "a | b", "a ^ b", "a & b | c ^ d", "a ^ b & c",
    "~a & b", "a & 15 == b",
    # 論理
    "a && b", "a || b", "a && b || c", "a || b && c",
    "x != 0 && y != 0", "!(a && b)",
    # 代入(右結合・lvalue いろいろ)
    "a = 1", "a = b = c", "a = b + 1", "*p = 5", "a[i] = v",
    "p->x = 0", "s.x = s.y = 1", "x = f(x)",
    # postfix の連鎖
    "a[i]", "a[i][j]", "a[i + 1]", "p->next", "p->next->val",
    "s.x", "s.p->y", "head->next", "a[f(i)]",
    # 関数呼び出し
    "f()", "f(1)", "f(1, 2)", "f(a, b + c, d[0])", "g(f(x))",
    "add(fib(n - 1), fib(n - 2))",
    # 講義のテストに出てくる形
    "fib(n - 1) + fib(n - 2)", "head != 0", "sum = sum + head->val",
    "p->x * p->x + p->y * p->y", "i = i + 1", "a[0] = 10",
    "total = total + x", "(10 - 3) * 2",
]


def sig(n):
    """AST を line 以外のフィールドで構造比較するための署名。"""
    if n is None:
        return None
    return (n.kind, n.val, n.sval, n.name, n.is_arrow, n.ty_str,
            sig(n.lhs), sig(n.rhs), sig(n.operand),
            tuple(sig(a) for a in n.args))


def scaffold_parse_expr(tokens):
    p = Parser(tokens)
    node = p.parse_expr()
    assert p.cur.kind == TK_EOF, "コーパスの式が scaffold で読み切れない"
    return node


def main():
    pass_count = 0
    fail_count = 0
    for src in EXPRESSIONS:
        expected = sig(scaffold_parse_expr(tokenize(src)))
        try:
            actual = sig(myparser.parse_expression(tokenize(src)))
        except NotImplementedError as e:
            print(f"[SKIP] 未実装: {e}")
            return 1
        except SyntaxError as e:
            print(f"[FAIL] {src!r} — 自作パーサがエラー: {e}")
            fail_count += 1
            continue

        if actual == expected:
            pass_count += 1
            if verbose:
                print(f"[PASS] {src!r}")
        else:
            print(f"[FAIL] {src!r} — AST が scaffold と不一致")
            fail_count += 1

    print()
    print("=============================")
    print(f"  PASS: {pass_count}  FAIL: {fail_count}  (全 {len(EXPRESSIONS)} 式)")
    print("=============================")
    if fail_count == 0:
        print("scaffold と完全一致。式パーサの置き換え成功!")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
