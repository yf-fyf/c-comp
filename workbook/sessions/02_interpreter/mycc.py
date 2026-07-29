"""
コマ 2: AST インタープリター（学生用スケルトン）

目標: AST を受け取り、式を評価して整数値を返す eval_ast() を実装する。
      コード生成をせず、Python の整数演算で直接計算する。

実行方法:
    python3 sessions/02_interpreter/mycc.py input.c
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scaffold'))

from ast_def import Node
from lexer import preprocess, tokenize
from parser import parse


# ---- C の除算・剰余のヘルパー ----
# C では / はゼロ方向に切り捨て、% の符号は被除数と同じ。

def c_div(a: int, b: int) -> int:
    """C と同じく、ゼロ方向に切り捨てた商を返す。"""
    if b == 0:
        raise ZeroDivisionError()
    quotient = abs(a) // abs(b)
    return -quotient if (a < 0) != (b < 0) else quotient


def c_mod(a: int, b: int) -> int:
    """C と同じく、被除数と同符号の剰余を返す。"""
    return a - b * c_div(a, b)


# ---- TODO: eval_ast を実装してください ----
#
# 各 AST ノードを再帰的に評価し、整数値を返す関数です。
# match 文で node.kind を分岐させてください。
#
# 各ノードの処理:
#
#   'Num'       → node.val をそのまま返す（例として実装済み）
#
#   'Neg'       → 単項マイナス
#     1. eval_ast(node.operand)  … オペランドを評価
#     2. 符号反転して返す
#
#   二項演算子 ('Add','Sub','Mul','Div','Mod') — 共通パターン:
#     Add: eval_ast(node.lhs) + eval_ast(node.rhs)
#     Sub: eval_ast(node.lhs) - eval_ast(node.rhs)
#     Mul: eval_ast(node.lhs) * eval_ast(node.rhs)
#     Div: c_div(eval_ast(node.lhs), eval_ast(node.rhs))    ← 除算は c_div を使う
#     Mod: c_mod(eval_ast(node.lhs), eval_ast(node.rhs))    ← 剰余は c_mod を使う
#
#   未対応ノードは RuntimeError を上げてください。

def eval_ast(node: Node) -> int:
    match node.kind:
        case 'Num':
            return node.val
        case 'Neg':
            # ---- TODO: Neg の実装 ----
            # ヒント: return -eval_ast(node.operand)
            raise NotImplementedError("eval_ast: Neg を実装してください")
        case 'Add':
            # ---- TODO: Add の実装 ----
            raise NotImplementedError("eval_ast: Add を実装してください")
        case 'Sub':
            # ---- TODO: Sub の実装 ----
            raise NotImplementedError("eval_ast: Sub を実装してください")
        case 'Mul':
            # ---- TODO: Mul の実装 ----
            raise NotImplementedError("eval_ast: Mul を実装してください")
        case 'Div':
            # ---- TODO: Div の実装 ----
            # ヒント: return c_div(eval_ast(node.lhs), eval_ast(node.rhs))
            raise NotImplementedError("eval_ast: Div を実装してください")
        case 'Mod':
            # ---- TODO: Mod の実装 ----
            # ヒント: return c_mod(eval_ast(node.lhs), eval_ast(node.rhs))
            raise NotImplementedError("eval_ast: Mod を実装してください")
        case _:
            raise RuntimeError(f"eval_ast: コマ2で未対応の式です (kind={node.kind!r})")


def run_main(prog: list[Node]) -> int:
    """コマ2の対象である main の return 式を eval_ast に渡す。"""
    for node in prog:
        if node.kind == 'FuncDef' and node.name == 'main':
            for stmt in node.body.stmts:
                if stmt.kind == 'Return' and stmt.operand is not None:
                    return eval_ast(stmt.operand)
    raise RuntimeError("main 関数または return 文が見つかりません")


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/02_interpreter/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()

    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    result = run_main(prog)

    print(f"評価結果: {result}")


if __name__ == '__main__':
    main()
