#!/usr/bin/env python3
"""F1: 字句解析器の自作(スケルトン)

scaffold/lexer.py と同じ仕様の字句解析器を自作する。

使い方:
    python3 mylexer.py path/to/file.c    # トークン列を表示

実装するメソッド(TODO の順に進める):
    Step 1: skip_whitespace / skip_comment / read_number
    Step 2: read_ident_or_keyword
    Step 3: read_punct
    Step 4: read_char_literal / read_string_literal
    Step 5: (新規実装なし)行番号が正しいか check.py で総点検

確認:
    python3 check.py     # Step ごとの単体テスト
    python3 golden.py    # 全テスト入力で scaffold と突き合わせ
"""

import sys
from dataclasses import dataclass

# ---- トークン種別(scaffold と同じ文字列にする) ----
TK_NUM   = 'TK_NUM'    # 整数リテラル
TK_CHAR  = 'TK_CHAR'   # 文字リテラル(int として扱う)
TK_STR   = 'TK_STR'    # 文字列リテラル
TK_IDENT = 'TK_IDENT'  # 識別子
TK_KW    = 'TK_KW'     # キーワード
TK_PUNCT = 'TK_PUNCT'  # 演算子・区切り文字
TK_EOF   = 'TK_EOF'    # 入力終端

KEYWORDS = {
    'int', 'char', 'void', 'struct', 'typedef',
    'if', 'else', 'while', 'for',
    'return', 'break', 'continue',
    'sizeof',
}

# 2文字演算子(長いものから先に試す)
TWO_CHAR_PUNCTS = [
    '==', '!=', '<=', '>=', '&&', '||', '<<', '>>', '->',
]

ONE_CHAR_PUNCTS = set('+-*/%&|^~!<>=;:,.(){}[]')

# エスケープ文字 → 文字コード
ESCAPES = {'n': 10, 't': 9, '\\': 92, "'": 39, '"': 34, '0': 0, 'r': 13}


@dataclass
class Token:
    kind: str
    val:  int = 0    # TK_NUM / TK_CHAR
    sval: str = ''   # TK_IDENT / TK_KW / TK_PUNCT / TK_STR
    line: int = 0


def escape_char(c):
    """バックスラッシュエスケープ文字を文字コードに変換する(完成済み)。"""
    return ESCAPES.get(c, ord(c))


class Lexer:
    def __init__(self, source, filename='<input>'):
        self.src = source          # 入力文字列
        self.filename = filename
        self.i = 0                 # 現在位置
        self.line = 1              # 現在の行番号
        self.tokens = []

    # ---- 共通部品(完成済み) ----

    def error(self, msg):
        raise SyntaxError(f"{self.filename}:{self.line}: 字句解析エラー: {msg}")

    def startswith(self, s):
        """現在位置が文字列 s で始まっているか。"""
        return self.src.startswith(s, self.i)

    def add(self, kind, val=0, sval=''):
        """現在の行番号でトークンを1つ追加する。"""
        self.tokens.append(Token(kind, val=val, sval=sval, line=self.line))

    # ---- メインループ(完成済みディスパッチ) ----
    #
    # 次の1文字を見て、どの読み取りに進むかを決める。
    # 上から順に試すので、判定の順序に意味がある
    # (コメントの判定は、割り算の '/' より先に来なければならない)。

    def tokenize(self):
        n = len(self.src)
        while self.i < n:
            c = self.src[self.i]
            if c in ' \t\r\n':
                self.skip_whitespace()                 # Step 1
            elif self.startswith('//') or self.startswith('/*'):
                self.skip_comment()                    # Step 1
            elif c.isdigit():
                self.read_number()                     # Step 1
            elif c.isalpha() or c == '_':
                self.read_ident_or_keyword()           # Step 2
            elif c == "'":
                self.read_char_literal()               # Step 4
            elif c == '"':
                self.read_string_literal()             # Step 4
            else:
                self.read_punct()                      # Step 3
        self.add(TK_EOF)
        return self.tokens

    # ---- Step 1: 空白・コメント・数 ----

    def skip_whitespace(self):
        """空白1文字を読み飛ばす。

        方針:
        - 改行なら self.line を1増やす
        - self.i を1進める
        """
        raise NotImplementedError("Step 1: skip_whitespace を実装する")

    def skip_comment(self):
        """// 行コメント、または /* */ ブロックコメントを読み飛ばす。

        方針:
        - '//' なら、行末(または入力終端)まで読み飛ばす。改行自体は消費しない
          (次のループの skip_whitespace が行番号を数える)
        - '/*' なら、'*/' が見つかるまで読み飛ばす。途中の改行で self.line を
          1増やす。終端せずに入力が尽きたら self.error(...) を呼ぶ
        """
        raise NotImplementedError("Step 1: skip_comment を実装する")

    def read_number(self):
        """数字が続く限り読み(最長一致)、TK_NUM を作る。

        方針:
        - 開始位置を覚えておき、数字が続く限り self.i を進める
        - 読んだ範囲を int にして self.add(TK_NUM, val=...) する
        """
        raise NotImplementedError("Step 1: read_number を実装する")

    # ---- Step 2: 識別子・キーワード ----

    def read_ident_or_keyword(self):
        """英数字と _ が続く限り読み、キーワード表と照合する。

        方針:
        - 英数字か '_' が続く限り self.i を進める(最長一致)
        - 読んだ単語が KEYWORDS にあれば TK_KW、なければ TK_IDENT
        - どちらも sval に単語を入れる
        """
        raise NotImplementedError("Step 2: read_ident_or_keyword を実装する")

    # ---- Step 3: 記号 ----

    def read_punct(self):
        """記号を読む。長い候補から順に試す(最長一致)。

        方針:
        1. '...' で始まるなら3文字のトークンにする
        2. TWO_CHAR_PUNCTS の各演算子を順に試す
        3. ONE_CHAR_PUNCTS にある1文字ならそのトークンにする
        4. どれでもなければ self.error(f"予期しない文字: {c!r}")
        """
        raise NotImplementedError("Step 3: read_punct を実装する")

    # ---- Step 4: 文字・文字列リテラル ----

    def read_char_literal(self):
        """'a' や '\\n' を読み、文字コードを値とする TK_CHAR を作る。

        方針:
        - 開きの ' を読み飛ばす
        - '\\' なら次の1文字を escape_char() で文字コードにする。
          そうでなければ ord() で文字コードにする
        - 閉じの ' がなければ self.error("文字リテラルが終端していない")
        """
        raise NotImplementedError("Step 4: read_char_literal を実装する")

    def read_string_literal(self):
        """"..." を読み、エスケープを解決した実体を sval に持つ TK_STR を作る。

        方針:
        - 開きの " を読み飛ばし、閉じの " まで1文字ずつバッファに集める
        - '\\' なら次の1文字を escape_char() で変換して chr() で文字に戻す
        - 文字列の中に改行があったら self.line を1増やす
        - 閉じずに入力が尽きたら self.error("文字列リテラルが終端していない")
        """
        raise NotImplementedError("Step 4: read_string_literal を実装する")


def tokenize(source, filename='<input>'):
    """scaffold の tokenize と同じインターフェース(完成済み)。"""
    return Lexer(source, filename).tokenize()


def main():
    if len(sys.argv) < 2:
        print("使い方: python3 mylexer.py file.c")
        return
    with open(sys.argv[1], encoding='utf-8') as f:
        source = f.read()
    for t in tokenize(source, sys.argv[1]):
        print(f"{t.line:4}: {t.kind:8} val={t.val:<6} sval={t.sval!r}")


if __name__ == "__main__":
    main()
