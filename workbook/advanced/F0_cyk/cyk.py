#!/usr/bin/env python3
"""F0: CYK 法による数式の構文解析(スケルトン)

使い方:
    python3 cyk.py '1 + 2 * 3'
    python3 cyk.py --table '1 + 2 * 3'

実装する関数(TODO の順に進める):
    Step 1: tokenize
    Step 2: cyk_chart
    Step 3: build_tree
    Step 4: count_trees
    Step 5: eval_ast

確認:
    python3 check.py
"""

import sys

# ---------------------------------------------------------------
# トークン
#
# トークンは (kind, value) のタプルで表す。
#   kind : 'num' '+' '*' '(' ')'
#   value: 数値('num' のみ。それ以外は None)
#
# 例: "12 + 3" → [('num', 12), ('+', None), ('num', 3)]
# ---------------------------------------------------------------


def tokenize(src):
    """Step 1: 文字列をトークン列にする(字句解析)。

    方針:
    - 空白(' ', '\\t', '\\n')は読み飛ばす
    - 数字が来たら、数字が続く限り読み進めて1つの 'num' トークンにする(最長一致)
    - '+' '*' '(' ')' は1文字で1トークン
    - それ以外の文字は SyntaxError を投げる
    """
    raise NotImplementedError("Step 1: tokenize を実装する")


# ---------------------------------------------------------------
# 文法(チョムスキー標準形)
#
# terminal_rules: (記号, トークン種別)  … 記号 → 'tok'
# binary_rules:   (記号, B, C)          … 記号 → B C
#
# この2つの形しかないのが「チョムスキー標準形」。
# CYK 法はこの形の文法を前提にする(変換の方法は handout の付録を参照)。
# ---------------------------------------------------------------

# 曖昧な文法 G1: E → E + E | E * E | ( E ) | num
GRAMMAR_AMBIG = {
    "start": "E",
    "terminal_rules": [
        ("E", "num"),
        ("PLUS", "+"),
        ("MUL", "*"),
        ("OPEN", "("),
        ("CLOSE", ")"),
    ],
    "binary_rules": [
        ("E", "E", "PLUS_REST"),
        ("E", "E", "MUL_REST"),
        ("E", "OPEN", "CLOSE_REST"),
        ("PLUS_REST", "PLUS", "E"),
        ("MUL_REST", "MUL", "E"),
        ("CLOSE_REST", "E", "CLOSE"),
    ],
}

# 優先順位を組み込んだ文法 G2:
#   E → E + T | T,  T → T * F | F,  F → ( E ) | num
GRAMMAR_PREC = {
    "start": "E",
    "terminal_rules": [
        ("E", "num"),
        ("T", "num"),
        ("F", "num"),
        ("PLUS", "+"),
        ("MUL", "*"),
        ("OPEN", "("),
        ("CLOSE", ")"),
    ],
    "binary_rules": [
        ("E", "E", "PLUS_REST"),
        ("E", "T", "MUL_REST"),
        ("E", "OPEN", "CLOSE_REST"),
        ("T", "T", "MUL_REST"),
        ("T", "OPEN", "CLOSE_REST"),
        ("F", "OPEN", "CLOSE_REST"),
        ("PLUS_REST", "PLUS", "T"),
        ("MUL_REST", "MUL", "F"),
        ("CLOSE_REST", "E", "CLOSE"),
    ],
}


# ---------------------------------------------------------------
# CYK 法
# ---------------------------------------------------------------


def cyk_chart(tokens, grammar):
    """Step 2: CYK の表を作る。

    chart[(i, j)] = {記号: [作り方, ...]}
      区間 (i, j) はトークン列のスライス tokens[i:j] に対応する。
      作り方は ('tok', トークン) または (k, B, C)。
      (k, B, C) は「tokens[i:k] が B、tokens[k:j] が C」という分割を表す。

    方針:
    1. 長さ1の区間 (i, i+1) を terminal_rules で埋める
       tokens[i] の kind に一致する規則 (sym, kind) ごとに
       cell[sym] へ ('tok', tokens[i]) を追加する
    2. 長さ2以上の区間 (i, j) を、長さの短い順に埋める
       分割点 k(i < k < j)ごとに、chart[(i, k)] と chart[(k, j)] を見て、
       binary_rules の (sym, B, C) が「左に B があり、右に C がある」なら
       cell[sym] へ (k, B, C) を追加する
    """
    raise NotImplementedError("Step 2: cyk_chart を実装する")


def accepts(tokens, grammar):
    """トークン列が文法から導出できるなら True(受理判定)。完成済み。"""
    if not tokens:
        return False
    chart = cyk_chart(tokens, grammar)
    return grammar["start"] in chart[(0, len(tokens))]


def build_tree(chart, i, j, sym):
    """Step 3: 表から (i, j) 区間の sym の導出木を1つ復元する。

    節は (記号, [左の子, 右の子])、葉は (記号, トークン) のタプルにする。

    方針:
    - chart[(i, j)][sym] の最初の作り方を使う
    - ('tok', トークン) なら葉 (sym, トークン) を返す
    - (k, B, C) なら、左 (i, k) の B と右 (k, j) の C を再帰的に復元して
      (sym, [左の木, 右の木]) を返す
    """
    raise NotImplementedError("Step 3: build_tree を実装する")


def count_trees(chart, i, j, sym):
    """Step 4: (i, j) 区間で sym から作れる導出木の本数を数える。

    方針:
    - chart[(i, j)][sym] の作り方ごとに本数を求めて合計する
    - ('tok', トークン) は1本
    - (k, B, C) は「左の本数 × 右の本数」
    """
    raise NotImplementedError("Step 4: count_trees を実装する")


# ---------------------------------------------------------------
# 導出木 → AST → 評価
# ---------------------------------------------------------------


def to_ast(node):
    """CNF の導出木を AST に直す。完成済み。

    AST は ('num', 値) / ('add', 左, 右) / ('mul', 左, 右) のタプル。
    """
    sym, body = node
    if not isinstance(body, list):  # 葉
        kind, value = body
        return ("num", value)
    left, right = body
    rsym = right[0]
    if rsym == "PLUS_REST":
        return ("add", to_ast(left), to_ast(right[1][1]))
    if rsym == "MUL_REST":
        return ("mul", to_ast(left), to_ast(right[1][1]))
    if rsym == "CLOSE_REST":
        return to_ast(right[1][0])  # ( E ) → E
    raise RuntimeError(f"想定外の導出木: {node}")


def to_sexpr(ast):
    """AST を S 式の文字列にする。完成済み。"""
    if ast[0] == "num":
        return f"(num {ast[1]})"
    return f"({ast[0]} {to_sexpr(ast[1])} {to_sexpr(ast[2])})"


def eval_ast(ast):
    """Step 5: AST を評価して値を返す(コマ1 と同じ考え方)。

    方針:
    - ('num', 値) なら値を返す
    - ('add', 左, 右) / ('mul', 左, 右) なら左右を評価して足す / 掛ける
    """
    raise NotImplementedError("Step 5: eval_ast を実装する")


# ---------------------------------------------------------------
# 表示(完成済み)
# ---------------------------------------------------------------


def print_chart(chart, tokens):
    """CYK の表を、長い区間を上にして表示する。"""
    n = len(tokens)
    for length in range(n, 0, -1):
        cells = []
        for i in range(0, n - length + 1):
            syms = sorted(chart[(i, i + length)].keys())
            cells.append("{" + " ".join(syms) + "}")
        print(f"  長さ{length}: " + "  ".join(cells))


def main():
    args = sys.argv[1:]
    show_table = "--table" in args
    exprs = [a for a in args if a != "--table"]
    if not exprs:
        print("使い方: python3 cyk.py [--table] '1 + 2 * 3'")
        return

    src = exprs[0]
    tokens = tokenize(src)
    print(f"入力       : {src}")
    print(f"トークン列 : {tokens}")

    for name, grammar in [("曖昧な文法 G1", GRAMMAR_AMBIG),
                          ("優先順位つき文法 G2", GRAMMAR_PREC)]:
        print(f"--- {name} ---")
        if not tokens:
            print("受理       : No")
            continue
        chart = cyk_chart(tokens, grammar)
        if show_table:
            print_chart(chart, tokens)
        start = grammar["start"]
        if start not in chart[(0, len(tokens))]:
            print("受理       : No")
            continue
        count = count_trees(chart, 0, len(tokens), start)
        ast = to_ast(build_tree(chart, 0, len(tokens), start))
        print(f"受理       : Yes(構文木は {count} 本)")
        print(f"最初の木   : {to_sexpr(ast)}")
        print(f"評価結果   : {eval_ast(ast)}")


if __name__ == "__main__":
    main()
