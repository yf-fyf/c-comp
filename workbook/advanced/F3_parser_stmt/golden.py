#!/usr/bin/env python3
"""F3 golden test — 文のコーパスで scaffold の Parser と AST を突き合わせる

使い方:
    python3 golden.py               # 同じディレクトリの myparser.py を確認
    python3 golden.py path/to/myparser.py
    python3 golden.py -v            # 全件の結果を表示(既定は FAIL のみ)

各文を scaffold の Parser(parse_stmt)と自作パーサの両方で解析し、
AST を構造で比較する(line は比較しない)。
コーパスに宣言(int x; など)は含まない — 宣言は F4 で扱う。
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

spec = importlib.util.spec_from_file_location("myparser_f3", target)
myparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(myparser)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize, TK_EOF        # noqa: E402
from parser import Parser                 # noqa: E402

# 文コーパス: 単純な文・ブロック・if(dangling else)・ループ・入れ子
STATEMENTS = [
    # 単純な文
    "return 42;", "return;", "return fib(n - 1) + fib(n - 2);",
    "break;", "continue;", ";",
    "x = 1;", "sum = sum + a[i];", "f(1, 2);", "head = head->next;",
    "*p = 20;", "p->val = 10;",
    # ブロック
    "{ }", "{ ; }", "{ x = 1; }",
    "{ x = 1; y = 2; return x + y; }",
    "{ { return 1; } }",
    "{ f(); { g(); } h(); }",
    # if
    "if (x) return 1;",
    "if (a > b) return a; else return b;",
    "if (x == 0) { return 1; } else { return 2; }",
    "if (a) if (b) return 1; else return 2;",
    "if (a) { if (b) return 1; } else return 2;",
    "if (score >= 90) return 4; else if (score >= 70) return 3; else return 1;",
    "if (n <= 1) { return n; }",
    # while
    "while (i <= 10) { sum = sum + i; i = i + 1; }",
    "while (head != 0) { sum = sum + head->val; head = head->next; }",
    "while (x) break;",
    "while (i < 3) { while (j < 2) { break; } }",
    "while (n != 1) { if (n % 2 == 0) { n = n / 2; } else { n = n * 3 + 1; } }",
    # for
    "for (i = 0; i < 5; i = i + 1) sum = sum + i;",
    "for (i = 1; i <= 10; i = i + 1) { if (i % 2 == 0) { continue; } sum = sum + i; }",
    "for (;;) break;",
    "for (; i < 3;) i = i + 1;",
    "for (i = 0; ; i = i + 1) { if (i > 5) break; }",
    "for (i = 0; i < 3; i = i + 1) for (j = 0; j < 2; j = j + 1) c = c + 1;",
    # 入れ子の複合
    "{ i = 0; while (i < 10) { if (i == 5) break; i = i + 1; } return i; }",
]


def sig(n):
    """AST を line 以外のフィールドで構造比較するための署名。"""
    if n is None:
        return None
    return (n.kind, n.val, n.sval, n.name, n.is_arrow, n.ty_str,
            sig(n.lhs), sig(n.rhs), sig(n.operand),
            sig(n.cond), sig(n.then), sig(n.else_),
            sig(n.init), sig(n.step), sig(n.body), sig(n.init_expr),
            tuple(sig(a) for a in n.args),
            tuple(sig(s) for s in n.stmts),
            tuple(sig(p) for p in n.params))


def scaffold_parse_stmt(tokens):
    p = Parser(tokens)
    node = p.parse_stmt()
    assert p.cur.kind == TK_EOF, "コーパスの文が scaffold で読み切れない"
    return node


def main():
    pass_count = 0
    fail_count = 0
    for src in STATEMENTS:
        expected = sig(scaffold_parse_stmt(tokenize(src)))
        try:
            actual = sig(myparser.parse_statement(tokenize(src)))
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
    print(f"  PASS: {pass_count}  FAIL: {fail_count}  (全 {len(STATEMENTS)} 文)")
    print("=============================")
    if fail_count == 0:
        print("scaffold と完全一致。文パーサの置き換え成功!")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
