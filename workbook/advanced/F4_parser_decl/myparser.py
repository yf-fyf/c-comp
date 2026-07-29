#!/usr/bin/env python3
"""F4: 再帰下降パーサ③(宣言・型・プログラム全体)— スケルトン

F3 の StmtParser を importlib で継承し、宣言・型・関数・typedef を追加して
parse_program を完成させる。この回で scaffold/parser.py の完全な置き換えになる。

使い方:
    python3 myparser.py path/to/file.c    # プログラム全体を S 式で表示

実装する順番:
    Step 1: is_type_start / parse_type
    Step 2: parse_array_suffix / parse_local_decl / parse_block(上書き)
    Step 3: peek_is_type / parse_sizeof
    Step 4: parse_func
    Step 5: parse_typedef / parse_program

確認:
    python3 check.py     # Step ごとの単体テスト
    python3 golden.py    # 全テスト入力(約100本の .c)で scaffold と突き合わせ
"""

import importlib.util
import sys
from pathlib import Path


def _load_f3():
    """隣の F3_parser_stmt/myparser.py(自分の F3)を読み込む(完成済み)。"""
    f3_path = Path(__file__).resolve().parent.parent / "F3_parser_stmt" / "myparser.py"
    if not f3_path.is_file():
        raise FileNotFoundError(f"F3 のパーサが見つからない: {f3_path}")
    spec = importlib.util.spec_from_file_location("f3_myparser", f3_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


f3 = _load_f3()

# f3 の読み込みで scaffold/ が sys.path に入っている
from ast_def import *      # noqa: E402,F403
from lexer import (        # noqa: E402
    preprocess, tokenize, TK_NUM, TK_IDENT, TK_KW, TK_EOF,
)


class ProgramParser(f3.StmtParser):
    """F3 の文パーサに、宣言・型・関数・typedef を追加した完全なパーサ。"""

    def __init__(self, tokens):
        super().__init__(tokens)
        # typedef で定義された型名の集合(is_type_start で参照する)
        self.typedef_names = set()

    # ---- 共通部品(完成済み) ----

    def expect_ident(self):
        """識別子を要求して名前を返す。"""
        if self.cur.kind not in (TK_IDENT, TK_KW):
            self.error(f"識別子が期待されましたが '{self.cur.sval}' がありました")
        name = self.cur.sval
        self.pos += 1
        return name

    def skip_braces(self):
        """'{' ... '}' をネスト対応で読み飛ばす(完成済み)。"""
        self.expect('{')
        depth = 1
        while depth > 0:
            if self.cur.kind == TK_EOF:
                self.error("'}' が見つかりません")
            if self.cur.sval == '{':
                depth += 1
            elif self.cur.sval == '}':
                depth -= 1
            self.pos += 1

    # ---- Step 1: 型 ----

    def is_type_start(self):
        """現在のトークンが型(=宣言)の開始かどうか。

        方針:
        - TK_KW で 'int' 'char' 'void' 'struct' のどれかなら True
        - TK_IDENT で typedef_names に登録済みの名前なら True
        - それ以外は False(→ 文・式として読む)
        """
        raise NotImplementedError("Step 1: is_type_start を実装する")

    def parse_type(self):
        """type ::= base_type { '*' }   結果は ty_str 文字列で返す。

        方針:
        - 'int' / 'char' / 'void' はそのまま base にする
        - 'struct' は、続く TK_IDENT(タグ名)があれば 'struct タグ' に。
          さらに '{' が続いていたら skip_braces() で中身を読み飛ばす
          (フィールドは AST に残さない — コマ12 がソースを走査していた理由)
        - typedef_names にある TK_IDENT はその名前を base にする
        - どれでもなければ self.error("型が期待されましたが ...")
        - 最後に '*' が続く限り base に '*' を足す(例: 'int**')
        """
        raise NotImplementedError("Step 1: parse_type を実装する")

    # ---- Step 2: 宣言とブロック ----

    def parse_array_suffix(self):
        """'[' INT ']' があれば '[N]' を返す。なければ空文字列。

        方針:
        - 現在が '[' でなければ '' を返す
        - '[' を読み進め、TK_NUM でなければエラー
          ("配列サイズに整数定数が必要です")
        - サイズを読み、']' を expect して f'[{size}]' を返す
        """
        raise NotImplementedError("Step 2: parse_array_suffix を実装する")

    def parse_local_decl(self):
        """local_decl ::= type declarator [ '=' expr ] ';'

        方針:
        - parse_type() → expect_ident() → parse_array_suffix()
        - '=' があれば初期化子を parse_expr() する
        - ';' を expect し、
          Node(ND_DECL, name=名前, ty_str=型+配列, init_expr=初期化子)
        """
        raise NotImplementedError("Step 2: parse_local_decl を実装する")

    def parse_block(self):
        """block ::= '{' { local_decl } { stmt } '}'   (C89: 宣言が先頭)

        方針: F3 の parse_block との違いは1点だけ。
        '{' の直後、is_type_start() の間 parse_local_decl() を繰り返してから、
        文のループに入る。
        """
        raise NotImplementedError("Step 2: parse_block を実装する(F3 版を上書き)")

    # ---- Step 3: sizeof ----

    def parse_unary(self):
        """F2 の parse_unary に sizeof を追加する(完成済みの上書き)。"""
        if self.cur.sval == 'sizeof':
            return self.parse_sizeof()
        return super().parse_unary()

    def peek_is_type(self):
        """'(' の次のトークンが型の開始かどうか。

        方針: is_type_start と同じ判定を self.peek(1) に対して行う。
        """
        raise NotImplementedError("Step 3: peek_is_type を実装する")

    def parse_sizeof(self):
        """'sizeof' '(' type ')' | 'sizeof' unary_expr

        方針:
        - 'sizeof' を読み進める
        - 現在が '(' かつ peek_is_type() なら sizeof(型):
          '(' type ')' を読んで Node(ND_SIZEOF_TYPE, ty_str=型)
        - そうでなければ sizeof 式:
          parse_unary() を読んで Node(ND_SIZEOF_EXPR, operand=式)
          (sizeof(x) はこちら — カッコつきの式として読まれる)
        """
        raise NotImplementedError("Step 3: parse_sizeof を実装する")

    # ---- Step 4: 関数 ----

    def parse_func(self, ty_str, name):
        """'(' [params] ')' の後、';' なら宣言、block なら定義。

        方針:
        1. '(' を expect する
        2. すぐ ')' なら引数なし
           'void' の直後が ')' なら引数なし(int f(void) の形。peek を使う)
           それ以外は ',' 区切りで繰り返す:
           - '...' が来たらそこで打ち切る(可変長宣言。lib.h で使う)
           - parse_type() し、TK_IDENT があれば引数名として読む
           - Node(ND_DECL, name=引数名, ty_str=型) を params に追加
           最後に ')' を expect
        3. ';' を consume できたら Node(ND_FUNCPROTO, ...) を返す(宣言)
           そうでなければ parse_block() を読んで Node(ND_FUNCDEF, ...) を返す
        どちらも name / ty_str / params を持たせる
        """
        raise NotImplementedError("Step 4: parse_func を実装する")

    # ---- Step 5: typedef とトップレベル ----

    def parse_typedef(self):
        """typedef を処理し、新しい型名を typedef_names に登録する。

        ('typedef' 自体は呼び出し側が読み終えている)

        方針:
        - 'struct' なら: タグ名(TK_IDENT)があれば読み飛ばし、
          '{' があれば skip_braces() で中身を読み飛ばす
        - そうでなければ既存の型名を1トークン読み飛ばす
        - '*' が続く限り読み飛ばす
        - 残った TK_IDENT が新しい型名。typedef_names に追加して読み進める
        - ';' を expect する
        AST ノードは作らない(型名の登録だけが仕事)。
        """
        raise NotImplementedError("Step 5: parse_typedef を実装する")

    def parse_program(self):
        """program ::= { typedef | グローバル変数宣言 | 関数宣言/定義 }

        方針: TK_EOF まで繰り返す。
        - 'typedef' なら読み進めて parse_typedef()(リストには何も足さない)
        - それ以外は parse_type() → expect_ident() し、
          - 次が '(' なら parse_func(型, 名前) を追加
          - そうでなければグローバル変数:
            parse_array_suffix()、'=' があれば初期化子、';' を expect し、
            Node(ND_DECL, name=..., ty_str=型+配列, init_expr=...) を追加
        """
        raise NotImplementedError("Step 5: parse_program を実装する")


def parse(tokens):
    """scaffold の parse() と同じインターフェース(完成済み)。"""
    return ProgramParser(tokens).parse_program()


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 myparser.py file.c")
        return
    from parse_viewer import program_to_sexp, render_sexp
    path = sys.argv[1]
    with open(path, encoding='utf-8') as f:
        source = preprocess(f.read(), path)
    program = parse(tokenize(source, path))
    print(render_sexp(program_to_sexp(program)))


if __name__ == "__main__":
    main()
