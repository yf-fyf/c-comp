#!/usr/bin/env python3
"""F2: 再帰下降パーサ①(式)— スケルトン

scaffold/parser.py の式パーサ部分と同じものを自作する(sizeof は F4 で扱う)。
Node と定数は scaffold の ast_def から借り、「組み立てる側」だけを作る。

使い方:
    python3 myparser.py '1 + 2 * 3'    # S 式で表示

実装する順番:
    Step 1: parse_primary(リテラル・変数・カッコ)
    Step 2: parse_mul / parse_add(左結合ループを手で2回書く)
    Step 3: parse_binary 共通化 + 残りの二項レベル + parse_rel(swap)
    Step 4: parse_unary / parse_postfix / 関数呼び出し
    Step 5: parse_cond(三項演算子、右結合)
    Step 6: parse_assign(右結合、cond_expr を呼ぶ)

確認:
    python3 check.py     # Step ごとの単体テスト
    python3 golden.py    # 式コーパスで scaffold と突き合わせ

各レベルは最初「素通し」になっている(1段下を呼ぶだけ)。
そのため、まだ実装していない演算子を含む式は
「式の後にトークンが余っています」というエラーになる。上から順に埋めていく。
"""

import sys
from pathlib import Path


def _find_scaffold():
    """このファイルの位置から scaffold/ ディレクトリを探す(完成済み)。"""
    d = Path(__file__).resolve().parent
    while d != d.parent:
        for cand in (d / "scaffold", d / "workbook" / "scaffold"):
            if (cand / "ast_def.py").is_file():
                return cand
        d = d.parent
    raise FileNotFoundError("scaffold/ が見つからない")


sys.path.insert(0, str(_find_scaffold()))

from ast_def import *          # noqa: E402,F403  Node と ND_* 定数
from lexer import (            # noqa: E402
    tokenize, TK_NUM, TK_CHAR, TK_STR, TK_IDENT, TK_KW, TK_PUNCT, TK_EOF,
)


class ExprParser:
    """式だけを解析する再帰下降パーサ。"""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ---- トークン操作(完成済み) ----

    @property
    def cur(self):
        """現在のトークン。"""
        return self.tokens[self.pos]

    def peek(self, offset=1):
        """offset 個先のトークン(読み進めない)。"""
        p = self.pos + offset
        return self.tokens[min(p, len(self.tokens) - 1)]

    def advance(self):
        """現在のトークンを返して1つ読み進める。"""
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def consume_if(self, s):
        """現在のトークンが記号 s ならば読み進めて True。"""
        if self.cur.sval == s:
            self.pos += 1
            return True
        return False

    def expect(self, s):
        """記号 s を要求する。なければエラー。"""
        if self.cur.sval != s:
            self.error(f"'{s}' が期待されましたが '{self.cur.sval}' がありました")
        self.pos += 1

    def error(self, msg):
        line = self.cur.line
        raise SyntaxError(f"[line {line}] 構文解析エラー: {msg}")

    # ---- 式(優先順位: 低い順に定義) ----
    #
    # EBNF の階層(language_spec.md)がそのまま関数の呼び出し階層になる。
    # 各関数は「自分のレベルの演算子」だけを処理し、
    # それより優先順位の高い部分は1段下の関数に任せる。

    def parse_expr(self):
        """expr ::= assign_expr(完成済みの入口)。"""
        return self.parse_assign()

    def parse_assign(self):
        """assign_expr ::= unary_expr '=' assign_expr | cond_expr   ※右結合

        cond_expr は unary_expr を含むので、先に cond_expr まで読んでしまい
        '=' があればそれを代入とみなす(仕様の unary_expr 限定は意味解析で検査)。
        Core の scaffold トークンには複合代入(+= など)がないので '=' のみでよい
        (複合代入は発展 L2 で扱う)。

        TODO(Step 6): parse_cond() を読んだ後、'=' があれば
        parse_assign() を再帰して ND_ASSIGN を作る(右結合)。
        """
        return self.parse_cond()  # TODO: '=' の処理を足す

    def parse_cond(self):
        """cond_expr ::= lor_expr [ '?' expr ':' cond_expr ]   ※右結合

        TODO(Step 5): lor_expr を読んだ後、'?' があれば
        - then = parse_expr()(then 側は expr 全体。assign を含められる)
        - ':' を expect
        - else_ = parse_cond()(else 側だけ再帰、a?b:c?d:e の連鎖に対応)
        で Node(ND_COND, cond=lor の木, then=then, else_=else_) を作る。
        '?' がなければ lor_expr の結果をそのまま返す。
        """
        return self.parse_lor()  # TODO: '?' ':' の処理を足す

    def parse_binary(self, op_map, next_fn):
        """左結合の二項演算を汎用的にパースする共通部品。

        op_map: {演算子文字列: ノード種別} 例 {'+': ND_ADD, '-': ND_SUB}
        next_fn: 1段階優先順位の高いレベルの関数

        TODO(Step 3): parse_add / parse_mul と同じループをここに一般化する。
        """
        raise NotImplementedError("Step 3: parse_binary を実装する")

    def parse_lor(self):
        """lor_expr ::= land_expr { '||' land_expr }
        TODO(Step 3): parse_binary を使って実装する。"""
        return self.parse_land()  # TODO

    def parse_land(self):
        """land_expr ::= eq_expr { '&&' eq_expr }
        TODO(Step 3): parse_binary を使って実装する。"""
        return self.parse_eq()  # TODO

    def parse_eq(self):
        """eq_expr ::= rel_expr { ('==' | '!=') rel_expr }
        TODO(Step 3)"""
        return self.parse_rel()  # TODO

    def parse_rel(self):
        """rel_expr ::= add_expr { ('<' | '>' | '<=' | '>=') add_expr }

        TODO(Step 3): これは parse_binary では書けない。
        '>' と '>=' は lhs・rhs を入れ替えて ND_LT / ND_LE に正規化する
        (AST に ND_GT / ND_GE は存在しない — コマ5 資料の種明かし)。
        例: a > b は Node(ND_LT, lhs=b の木, rhs=a の木)
        """
        return self.parse_add()  # TODO

    def parse_add(self):
        """add_expr ::= mul_expr { ('+' | '-') mul_expr }

        TODO(Step 2): 左結合のループを手で書く。
        1. node = self.parse_mul()
        2. 現在のトークンが '+' か '-' の間、繰り返し:
           読み進めて rhs = self.parse_mul() を取り、
           node = Node(ND_ADD または ND_SUB, lhs=node, rhs=rhs)
           (いままでの結果を lhs に入れるので左結合になる)
        """
        return self.parse_mul()  # TODO: ループを足す

    def parse_mul(self):
        """mul_expr ::= unary_expr { ('*' | '/' | '%') unary_expr }
        TODO(Step 2): parse_add と同じ形のループ。"""
        return self.parse_unary()  # TODO: ループを足す

    def parse_unary(self):
        """unary_expr ::= ('-'|'!'|'*'|'&'|'++'|'--') unary_expr | postfix_expr

        TODO(Step 4): 前置演算子があれば読み進めて、
        自分自身を再帰した結果を operand に持つノードを作る。
        - '-' → ND_NEG    '!' → ND_NOT
        - '*' → ND_DEREF  '&' → ND_ADDR
        - '++' → ND_PREINC(前置インクリメント)
        - '--' → ND_PREDEC(前置デクリメント。後置形はこの言語にはない)
        どれでもなければ parse_postfix() へ。
        """
        return self.parse_postfix()  # TODO: 前置演算子を足す

    def parse_postfix(self):
        """postfix_expr ::= primary_expr { '[' expr ']' | '->' IDENT | '.' IDENT }

        TODO(Step 4): primary を読んだ後、後置がある限りループ:
        - '[' expr ']'  → Node(ND_INDEX, lhs=いままでの結果, rhs=添字)
        - '->' IDENT    → Node(ND_MEMBER, operand=結果, name=名前, is_arrow=True)
        - '.'  IDENT    → Node(ND_MEMBER, operand=結果, name=名前, is_arrow=False)
        """
        return self.parse_primary()  # TODO: 後置のループを足す

    def parse_primary(self):
        """primary_expr ::= INT | CHAR | STRING | IDENT ['(' args ')'] | '(' expr ')'

        TODO(Step 1):
        - TK_NUM / TK_CHAR → Node(ND_NUM, val=トークンの val)
        - TK_STR           → Node(ND_STR, sval=トークンの sval)
        - '('              → parse_expr() を読み、')' を expect する
        - TK_IDENT         → Node(ND_VAR, name=名前)
        - どれでもなければ self.error(f"式が期待されましたが ...")

        TODO(Step 4): TK_IDENT の直後に '(' があれば関数呼び出し。
        引数を ',' 区切りで parse_expr() し、
        Node(ND_CALL, name=名前, args=引数リスト) を作る。
        """
        raise NotImplementedError("Step 1: parse_primary を実装する")


def parse_expression(tokens):
    """トークン列を式1つとして解析する(完成済み)。

    式の後にトークンが余っていたらエラーにする。
    """
    p = ExprParser(tokens)
    node = p.parse_expr()
    if p.cur.kind != TK_EOF:
        p.error(f"式の後にトークンが余っています: '{p.cur.sval}'")
    return node


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 myparser.py '1 + 2 * 3'")
        return
    from parse_viewer import node_to_sexp, render_sexp
    node = parse_expression(tokenize(sys.argv[1]))
    print(render_sexp(node_to_sexp(node)))


if __name__ == "__main__":
    main()
