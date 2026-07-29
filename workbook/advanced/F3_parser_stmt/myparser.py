#!/usr/bin/env python3
"""F3: 再帰下降パーサ②(文)— スケルトン

F2 で自作した ExprParser を importlib で継承し、文の解析を追加する
(本編の CodegenNN と同じ「前回の自分を継承する」方式)。
F2 が未完成だとこの回のテストは動かない。先に F2 を完成させること。

宣言(int x; など)は F4 で扱う。

使い方:
    python3 myparser.py 'if (a > b) return a; else return b;'

実装する順番:
    Step 1: parse_return / parse_break / parse_continue / parse_exprstmt
    Step 2: parse_block
    Step 3: parse_if(dangling else)
    Step 4: parse_while / parse_for

確認:
    python3 check.py     # Step ごとの単体テスト
    python3 golden.py    # 文コーパスで scaffold と突き合わせ
"""

import importlib.util
import sys
from pathlib import Path


def _load_f2():
    """隣の F2_parser_expr/myparser.py(自分の F2)を読み込む(完成済み)。"""
    f2_path = Path(__file__).resolve().parent.parent / "F2_parser_expr" / "myparser.py"
    if not f2_path.is_file():
        raise FileNotFoundError(f"F2 のパーサが見つからない: {f2_path}")
    spec = importlib.util.spec_from_file_location("f2_myparser", f2_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


f2 = _load_f2()

# f2 の読み込みで scaffold/ が sys.path に入っている
from ast_def import *      # noqa: E402,F403
from lexer import tokenize, TK_EOF  # noqa: E402


class StmtParser(f2.ExprParser):
    """F2 の式パーサに、文の解析を追加したパーサ。

    式のメソッド(parse_expr など)とトークン操作は F2 から継承している。
    """

    # ---- 文のディスパッチ(完成済み) ----
    #
    # 文は「先頭のトークン」を見るだけで種類が決まる。
    # キーワードで始まらないものは式文(または空文)。

    def parse_stmt(self):
        """stmt ::= return文 | break文 | continue文 | if文 | while文
                  | for文 | block | 式文(空文含む)"""
        sval = self.cur.sval
        if sval == 'return':
            return self.parse_return()
        if sval == 'break':
            return self.parse_break()
        if sval == 'continue':
            return self.parse_continue()
        if sval == 'if':
            return self.parse_if()
        if sval == 'while':
            return self.parse_while()
        if sval == 'for':
            return self.parse_for()
        if sval == '{':
            return self.parse_block()
        return self.parse_exprstmt()

    # ---- Step 1: 単純な文 ----

    def parse_return(self):
        """'return' [ expr ] ';'

        方針:
        - 'return' を読み進める
        - すぐ ';' なら Node(ND_RETURN)(戻り値なし)
        - そうでなければ式を parse_expr() し、';' を expect して
          Node(ND_RETURN, operand=式)
        """
        raise NotImplementedError("Step 1: parse_return を実装する")

    def parse_break(self):
        """'break' ';'  → Node(ND_BREAK)"""
        raise NotImplementedError("Step 1: parse_break を実装する")

    def parse_continue(self):
        """'continue' ';'  → Node(ND_CONTINUE)"""
        raise NotImplementedError("Step 1: parse_continue を実装する")

    def parse_exprstmt(self):
        """式文 expr ';'、または空文 ';'

        方針:
        - すぐ ';' なら Node(ND_EXPRSTMT)(空文)
        - そうでなければ式を読み、';' を expect して
          Node(ND_EXPRSTMT, operand=式)
        """
        raise NotImplementedError("Step 1: parse_exprstmt を実装する")

    # ---- Step 2: ブロック ----

    def parse_block(self):
        """block ::= '{' { stmt } '}'   ※宣言は F4 で扱う

        方針:
        - '{' を expect する
        - '}' が来るまで parse_stmt() を繰り返してリストに集める
          (途中で入力が尽きたら self.error("'}' が見つかりません"))
        - Node(ND_BLOCK, stmts=リスト)
        """
        raise NotImplementedError("Step 2: parse_block を実装する")

    # ---- Step 3: if ----

    def parse_if(self):
        """if_stmt ::= 'if' '(' expr ')' stmt [ 'else' stmt ]

        方針:
        - 'if' を読み進め、'(' expr ')' を読む
        - then 側を parse_stmt() で読む(ブロックとは限らない)
        - 次のトークンが 'else' なら読み進めて else 側も parse_stmt()
        - Node(ND_IF, cond=..., then=..., else_=...)(else がなければ None)

        「else があれば取る」だけで、else は最も内側の if に結合する
        (dangling else)。
        """
        raise NotImplementedError("Step 3: parse_if を実装する")

    # ---- Step 4: while / for ----

    def parse_while(self):
        """while_stmt ::= 'while' '(' expr ')' stmt
        → Node(ND_WHILE, cond=..., body=...)"""
        raise NotImplementedError("Step 4: parse_while を実装する")

    def parse_for(self):
        """for_stmt ::= 'for' '(' [expr] ';' [expr] ';' [expr] ')' stmt

        方針:
        - init: 次が ';' なら None、そうでなければ parse_expr()。';' を expect
        - cond: 次が ';' なら None、そうでなければ parse_expr()。';' を expect
        - step: 次が ')' なら None、そうでなければ parse_expr()。')' を expect
        - body を parse_stmt() で読む
        - Node(ND_FOR, init=..., cond=..., step=..., body=...)
        """
        raise NotImplementedError("Step 4: parse_for を実装する")


def parse_statement(tokens):
    """トークン列を文1つとして解析する(完成済み)。"""
    p = StmtParser(tokens)
    node = p.parse_stmt()
    if p.cur.kind != TK_EOF:
        p.error(f"文の後にトークンが余っています: '{p.cur.sval}'")
    return node


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 myparser.py 'if (a > b) return a; else return b;'")
        return
    from parse_viewer import node_to_sexp, render_sexp
    node = parse_statement(tokenize(sys.argv[1]))
    print(render_sexp(node_to_sexp(node)))


if __name__ == "__main__":
    main()
