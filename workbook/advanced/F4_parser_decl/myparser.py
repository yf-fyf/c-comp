#!/usr/bin/env python3
"""F4: 再帰下降パーサ③(宣言・型・プログラム全体)— スケルトン

F3 の StmtParser を importlib で継承し、型・宣言・struct 定義・関数・
プログラム全体の解析を追加して parse_program を完成させる。
この回で scaffold/parser.py の完全な置き換えになる。

使い方:
    python3 myparser.py path/to/file.c    # プログラム全体を S 式で表示

実装する順番:
    Step 1: is_type_start / parse_base_and_stars / parse_obj_type / parse_scalar_type
    Step 2: parse_local_decl / parse_func_body
    Step 3: peek_is_type / parse_sizeof
    Step 4: parse_func
    Step 5: parse_field / parse_struct_decl / parse_program

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
    preprocess, tokenize, TK_IDENT, TK_KW, TK_EOF,
)

# 型を書き始められるキーワードはこの 4 語だけ(typedef がないので表は増えない)
TYPE_KEYWORDS = ('int', 'char', 'void', 'struct')


class ProgramParser(f3.StmtParser):
    """F3 の文パーサに、型・宣言・関数・プログラム全体を追加した完全なパーサ。"""

    # ---- 共通部品(完成済み) ----

    def expect_ident(self):
        """識別子を要求して名前を返す。"""
        if self.cur.kind != TK_IDENT:
            self.error(f"識別子が期待されましたが '{self.cur.sval}' がありました")
        name = self.cur.sval
        self.pos += 1
        return name

    # ---- Step 1: 型 — 位置ごとに許される型が違う ----

    def is_type_start(self):
        """現在のトークンが型(=宣言)の開始かどうか。

        方針: TK_KW で TYPE_KEYWORDS のどれかなら True、それ以外は False
        (→ 文・式として読む)。表を引く必要はない。
        """
        raise NotImplementedError("Step 1: is_type_start を実装する")

    def parse_base_and_stars(self):
        """型の基底と '*' の並びを読み、('int', '**') の組で返す。

        方針:
        - 'int' / 'char' / 'void' はそのまま base にする
        - 'struct' なら読み進めて expect_ident() でタグ名を読み、
          base を 'struct タグ名' にする(タグ記法は必須)
        - どれでもなければ self.error("型が期待されましたが ...")
        - 最後に '*' が続く限り stars に '*' を足す
        基底と '*' を分けて返すのは、位置ごとの検証が
        「base が void か / struct か」と「'*' が付いているか」で決まるからである。
        """
        raise NotImplementedError("Step 1: parse_base_and_stars を実装する")

    def parse_obj_type(self):
        """変数宣言・sizeof で使える型(obj_type)。

        方針: parse_base_and_stars() を呼び、
        base が 'void' で stars が空なら self.error("void 型の変数は宣言できません")。
        通れば base + stars を返す。
        """
        raise NotImplementedError("Step 1: parse_obj_type を実装する")

    def parse_scalar_type(self):
        """引数・struct フィールドで使える型(scalar_type)。

        方針: parse_base_and_stars() を呼び、obj_type の検査に加えて
        base が 'struct ...' で stars が空なら
        self.error("struct 値はここでは使えません(ポインタにする)")。
        (void 単独のメッセージは "void 型は使えません(void * は可)")
        """
        raise NotImplementedError("Step 1: parse_scalar_type を実装する")

    # ---- Step 2: 局所宣言と関数本体 ----

    def parse_local_decl(self):
        """local_decl ::= obj_type IDENT ';'   (初期化子はこの言語にはない)

        方針: parse_obj_type() → expect_ident() → expect(';') し、
        Node(ND_DECL, name=名前, ty_str=型)。
        """
        raise NotImplementedError("Step 2: parse_local_decl を実装する")

    def parse_func_body(self):
        """func_body ::= '{' { local_decl } { stmt } '}'   (宣言は先頭のみ)

        方針: F3 の parse_block との違いは 1 点だけ。
        '{' の直後、is_type_start() が真の間 parse_local_decl() を繰り返してから、
        文のループに入る(入力が尽きたら self.error("'}' が見つかりません"))。
        Node(ND_BLOCK, stmts=リスト) を返す。

        F3 の parse_block(文だけを含む入れ子ブロック)は上書きしない。
        宣言を置けるのは関数本体の先頭だけなので、両者は別の関数である。
        """
        raise NotImplementedError("Step 2: parse_func_body を実装する")

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
        """'sizeof' '(' obj_type ')'   (型名形式のみ)

        方針:
        - 'sizeof' を読み進める
        - '(' でない、または peek_is_type() が偽なら
          self.error("sizeof は sizeof(型名) 形式のみ使えます")
          (この言語に sizeof 式 はない。先読みは曖昧さの解消ではなく
           エラーメッセージを良くするために使う)
        - '(' obj_type ')' を読んで Node(ND_SIZEOF_TYPE, ty_str=型)
        """
        raise NotImplementedError("Step 3: parse_sizeof を実装する")

    # ---- Step 4: 関数 ----

    def parse_func(self, ty_str, name):
        """'(' [params] ')' の後、';' なら宣言、本体があれば定義。

        方針:
        1. '(' を expect する
        2. すぐ ')' なら引数なし。それ以外は ',' 区切りで繰り返す:
           - '...' が来たら: params が空なら
             self.error("可変長 '...' は 1 個以上の固定引数の後にのみ書けます")。
             読み進めて variadic を立て、ループを抜ける
           - parse_scalar_type() → expect_ident()(仮引数は名前必須)
           - Node(ND_DECL, name=引数名, ty_str=型) を params に追加
           最後に ')' を expect
        3. ';' を consume できたら Node(ND_FUNCPROTO, name, ty_str, params)(宣言)
        4. そうでなければ定義。variadic なら
           self.error("可変長 '...' はプロトタイプ宣言でのみ使えます")。
           parse_func_body() を読んで Node(ND_FUNCDEF, ..., body=本体)
        引数リストを読み終えるまで宣言か定義かを決めなくてよい点に注目する。
        """
        raise NotImplementedError("Step 4: parse_func を実装する")

    # ---- Step 5: struct 定義とトップレベル ----

    def parse_field(self):
        """field_decl ::= scalar_type IDENT ';'

        方針: parse_scalar_type() → expect_ident() → expect(';')。
        **戻り値はない**(フィールドは検証するだけで AST に残さない)。
        """
        raise NotImplementedError("Step 5: parse_field を実装する")

    def parse_struct_decl(self):
        """'struct' IDENT '{' field+ '}' ';' | 'struct' IDENT ';'(前方宣言)

        方針:
        - 'struct' を expect、expect_ident() でタグ名
        - すぐ ';' を consume できたら前方宣言なので、そこで戻る
        - '{' を expect し、parse_field() を 1 回(フィールドは 1 個以上)、
          その後 '}' を consume するまで parse_field() を繰り返す
          (入力が尽きたら self.error("'}' が見つかりません"))
        - 最後に ';' を expect する
        AST ノードは作らない(検証だけが仕事)。
        """
        raise NotImplementedError("Step 5: parse_struct_decl を実装する")

    def parse_program(self):
        """program ::= { struct 定義 | グローバル変数宣言 | 関数宣言/定義 }+

        方針: 空入力なら self.error("プログラムには 1 個以上の外部宣言が必要です")。
        TK_EOF まで繰り返す。
        - 'struct' で始まり、self.peek(2).sval が '{' か ';' なら struct 定義:
          parse_struct_decl()(リストには何も足さない)
          ※ 2 トークン先まで見るのは 'struct S x;' と区別するため
        - それ以外は parse_base_and_stars() → expect_ident() し、
          - 次が '(' なら関数。戻り値型の検証(struct 値は不可)をしてから
            parse_func(base + stars, 名前) を追加
          - そうでなければグローバル変数。obj_type の検証(void 単独は不可)を
            してから ';' を expect し、Node(ND_DECL, name=..., ty_str=...) を追加
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
