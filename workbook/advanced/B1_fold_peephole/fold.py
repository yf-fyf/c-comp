#!/usr/bin/env python3
"""B1: 定数畳み込みパス(スケルトン)

AST を受け取り、コンパイル時に値が決まる部分式を ND_NUM に置き換えて返す。
木の走査(fold_node / fold_program)と置き換えの判定(fold_expr)は完成済み。
実装するのは「演算の意味」の2つ:

    Step 1: fold_binary / fold_unary

確認:
    python3 check.py
"""

import sys
from pathlib import Path


def _find_scaffold():
    d = Path(__file__).resolve().parent
    while d != d.parent:
        for cand in (d / "scaffold", d / "workbook" / "scaffold"):
            if (cand / "ast_def.py").is_file():
                return cand
        d = d.parent
    raise FileNotFoundError("scaffold/ が見つからない")


sys.path.insert(0, str(_find_scaffold()))

from ast_def import *  # noqa: E402,F403

# 畳み込み対象の二項・単項ノード
BINARY_KINDS = {
    ND_ADD, ND_SUB, ND_MUL, ND_DIV, ND_MOD,
    ND_SHL, ND_SHR, ND_BITAND, ND_BITOR, ND_BITXOR,
    ND_EQ, ND_NE, ND_LT, ND_LE, ND_AND, ND_OR,
}
UNARY_KINDS = {ND_NEG, ND_NOT, ND_BITNOT}

# 子ノードを持つフィールド
CHILD_FIELDS = ['lhs', 'rhs', 'operand', 'cond', 'then', 'else_',
                'init', 'step', 'body', 'init_expr']
LIST_FIELDS = ['stmts', 'args', 'params']

MASK64 = (1 << 64) - 1


def to_i64(x):
    """Python の整数を 64bit 符号付きの値に丸める(完成済み)。

    実行時のレジスタは 64bit で桁あふれするので、
    コンパイル時に畳み込んだ値も同じように丸めておく。
    """
    x &= MASK64
    if x >= 1 << 63:
        x -= 1 << 64
    return x


def fold_binary(kind, a, b):
    """Step 1: 二項演算 kind を定数 a, b に適用した値を返す。

    畳み込めない(畳み込んではいけない)場合は None を返す。

    方針:
    - ND_ADD / ND_SUB / ND_MUL / ビット演算 / シフト: 計算して to_i64() で丸める
    - ND_DIV / ND_MOD: b == 0 なら None(実行時エラーはそのまま残す)。
      C の除算は 0 方向へ切り捨てで、Python の // (床関数) と負数で挙動が違う。
      例: C では -7 / 2 == -3 だが、Python では -7 // 2 == -4。
      ヒント: q = abs(a) // abs(b) を計算してから符号を付ける。
      剰余は a - q * b(a == q*b + r が成り立つように)
    - ND_SHL / ND_SHR: b が 0..63 の範囲外なら None。
      Python の >> は算術シフトなので sra と同じ挙動になる
    - 比較(Eq/Ne/Lt/Le)と論理(And/Or)は 1 か 0 を返す
    - 対応しない kind は None
    """
    raise NotImplementedError("Step 1: fold_binary を実装する")


def fold_unary(kind, a):
    """Step 1: 単項演算 kind を定数 a に適用した値を返す。

    方針:
    - ND_NEG: -a を to_i64() で丸める
    - ND_NOT: a == 0 なら 1、それ以外は 0
    - ND_BITNOT: ~a を to_i64() で丸める
    - 対応しない kind は None
    """
    raise NotImplementedError("Step 1: fold_unary を実装する")


def fold_expr(node):
    """子がすでに畳み込み済みのノード1つを、可能なら ND_NUM に置き換える(完成済み)。"""
    if (node.kind in BINARY_KINDS
            and node.lhs is not None and node.lhs.kind == ND_NUM
            and node.rhs is not None and node.rhs.kind == ND_NUM):
        v = fold_binary(node.kind, node.lhs.val, node.rhs.val)
        if v is not None:
            return Node(ND_NUM, val=v, line=node.line)
    if (node.kind in UNARY_KINDS
            and node.operand is not None and node.operand.kind == ND_NUM):
        v = fold_unary(node.kind, node.operand.val)
        if v is not None:
            return Node(ND_NUM, val=v, line=node.line)
    return node


def fold_node(node):
    """木全体を後行順(子が先)で畳み込む(完成済み)。

    子を先に畳み込むので、(1 + 2) * 3 は
    まず (1 + 2) が 3 になり、次に 3 * 3 が 9 になる。
    """
    if node is None:
        return None
    for f in CHILD_FIELDS:
        setattr(node, f, fold_node(getattr(node, f)))
    for f in LIST_FIELDS:
        setattr(node, f, [fold_node(c) for c in getattr(node, f)])
    return fold_expr(node)


def fold_program(prog):
    """トップレベル宣言のリスト全体を畳み込む(完成済み)。"""
    return [fold_node(n) for n in prog]
