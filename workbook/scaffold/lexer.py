"""
字句解析器 + 簡易前処理器 — 教員提供スキャフォールド

使い方:
    source = preprocess(raw_source, filename)
    tokens = tokenize(source, filename)
"""

import re
import os
import sys
from dataclasses import dataclass
from typing import List, Dict, Set

# ---- トークン種別 ----
TK_NUM   = 'TK_NUM'    # 整数リテラル
TK_CHAR  = 'TK_CHAR'   # 文字リテラル（int として扱う）
TK_STR   = 'TK_STR'    # 文字列リテラル
TK_IDENT = 'TK_IDENT'  # 識別子
TK_KW    = 'TK_KW'     # キーワード
TK_PUNCT = 'TK_PUNCT'  # 演算子・区切り文字
TK_EOF   = 'TK_EOF'    # 入力終端

# 予約語は使用する 12 語のみ（言語仕様「字句」参照）
KEYWORDS = {
    'int', 'char', 'void', 'struct',
    'if', 'else', 'while', 'for',
    'break', 'continue', 'return',
    'sizeof',
}

# 2文字演算子（長いものを先に並べる）
TWO_CHAR_PUNCTS = [
    '==', '!=', '<=', '>=', '&&', '||', '->', '++', '--',
]

ONE_CHAR_PUNCTS = set('+-*/%&!<>=;:,.?(){}[]')

INT_MAX = 2147483647

# エスケープは 6 種のみ（言語仕様「リテラル」参照）
ESCAPES = {'n': 10, 't': 9, '\\': 92, "'": 39, '"': 34, '0': 0}


@dataclass
class Token:
    kind: str
    val:  int = 0    # TK_NUM / TK_CHAR
    sval: str = ''   # TK_IDENT / TK_KW / TK_PUNCT / TK_STR
    line: int = 0


def _lex_error(msg: str, filename: str, line: int) -> None:
    print(f"{filename}:{line}: 字句解析エラー: {msg}", file=sys.stderr)
    sys.exit(1)


def _pp_error(msg: str, filename: str, line: int) -> None:
    print(f"{filename}:{line}: 前処理エラー: {msg}", file=sys.stderr)
    sys.exit(1)


def _escape_char(c: str, filename: str, line: int) -> int:
    """バックスラッシュエスケープ文字を文字コードに変換（6 種のみ）"""
    if c not in ESCAPES:
        _lex_error(f"不正なエスケープ: \\{c}", filename, line)
    return ESCAPES[c]


# ---- 前処理器 ----

def _code_spans(line: str) -> List[tuple]:
    """1 行を走査して「コード」区間 (start, end) の並びを返す。

    文字列リテラル "..."、文字リテラル '...'、行コメント // ... の内側は
    コードではないので除外する。マクロ置換をコード区間だけに限るために使う。

    リテラルの終端判定（バックスラッシュが次の 1 文字を打ち消す）と、
    行コメントが // のみ（ブロックコメントは言語仕様外）である点は
    tokenize() と同じ規則である。tokenize() 側は文字コードへの変換や
    エラー報告まで行うため、走査そのものを 1 つの関数に統合すると
    かえって読みにくくなる。そこでここでは「区間を切り出すだけ」の
    軽量な状態機械を別に置き、規則が対応することをこのコメントで示す。
    エスケープの種類の妥当性（ESCAPES の 6 種か）は検査しない。
    それは tokenize() の役目で、ここでは終端を誤認しなければ十分である。

    終端しないリテラルが行末まで続く場合は、その残りをコード外として扱う。
    不正な入力そのものは後段の tokenize() が字句解析エラーとして報告する。
    """
    spans = []
    i = 0
    n = len(line)
    start = 0
    while i < n:
        c = line[i]
        if c == '/' and line[i:i+2] == '//':
            break                      # 以降は行コメント
        if c == '"' or c == "'":
            if start < i:
                spans.append((start, i))
            quote = c
            i += 1
            while i < n and line[i] != quote:
                if line[i] == '\\':    # 次の 1 文字は終端記号にならない
                    i += 1
                i += 1
            i += 1                     # 閉じ引用符（無ければ行末を越えるだけ）
            start = i
            continue
        i += 1
    if start < n:
        spans.append((start, min(i, n)))
    return spans


def _sub_in_code(line: str, pattern, defines: Dict[str, str]) -> str:
    """コード区間だけにマクロ置換を適用した行を返す。"""
    out = []
    pos = 0
    for s, e in _code_spans(line):
        out.append(line[pos:s])                                   # リテラル等はそのまま
        out.append(pattern.sub(lambda m: defines[m.group(1)], line[s:e]))
        pos = e
    out.append(line[pos:])
    return ''.join(out)


def _search_in_code(line: str, pattern):
    """コード区間だけを対象に pattern を探す。見つかれば Match を返す。"""
    for s, e in _code_spans(line):
        m = pattern.search(line, s, e)
        if m:
            return m
    return None


def _apply_defines(line: str, defines: Dict[str, str],
                   filename: str, lineno: int) -> str:
    """オブジェクト形式マクロを 1 段だけ置換する。

    置換対象は文字列リテラル・文字リテラル・行コメントの外側にある
    識別子トークンだけである（"N" や 'N' や // N の中身は変えない）。
    置換結果のコード部分にマクロ名が残る場合はエラー（多段参照は言語仕様外）。
    """
    if not defines:
        return line
    pattern = re.compile(r'\b(' + '|'.join(re.escape(n) for n in defines) + r')\b')
    if not _search_in_code(line, pattern):
        return line
    replaced = _sub_in_code(line, pattern, defines)
    m = _search_in_code(replaced, pattern)
    if m:
        _pp_error(f"マクロの多段参照は使えない: {m.group(1)}", filename, lineno)
    return replaced


def preprocess(source: str,
               filename: str = '<input>',
               defines: Dict[str, str] = None,
               include_dirs: List[str] = None,
               _active: Set[str] = None) -> str:
    """
    #include "file.h" と #define NAME value を処理する。
    指令はこの 2 種のみ。循環取込みと、置換結果にマクロ名が残る #define はエラー。
    """
    if defines is None:
        defines = {}
    if include_dirs is None:
        # ファイル自身のディレクトリと scaffold/ を検索パスに含める
        file_dir = os.path.dirname(os.path.abspath(filename))
        scaffold_dir = os.path.dirname(os.path.abspath(__file__))
        include_dirs = [file_dir, scaffold_dir, '.']
    if _active is None:
        _active = set()
        if os.path.exists(filename):
            _active.add(os.path.realpath(filename))

    result_lines = []
    for lineno, line in enumerate(source.split('\n'), 1):
        stripped = line.strip()

        if stripped.startswith('#'):
            # #include "file.h"
            if stripped.startswith('#include'):
                m = re.match(r'#include\s+"([^"]+)"\s*$', stripped)
                if not m:
                    _pp_error('#include は #include "file" 形式のみ使える', filename, lineno)
                fname = m.group(1)
                for d in include_dirs:
                    path = os.path.join(d, fname)
                    if os.path.exists(path):
                        real = os.path.realpath(path)
                        if real in _active:
                            _pp_error(f"循環取込み: {fname}", filename, lineno)
                        with open(path, 'r', encoding='utf-8') as f:
                            included = preprocess(f.read(), path, defines,
                                                  include_dirs, _active | {real})
                        result_lines.append(included)
                        break
                else:
                    _pp_error(f"ファイルが見つからない: {fname}", filename, lineno)
                continue

            # #define NAME [value]
            if stripped.startswith('#define'):
                m = re.match(r'#define\s+([A-Za-z_]\w*)(?:\s+(.*))?$', stripped)
                if not m:
                    _pp_error('#define はオブジェクト形式 #define NAME value のみ使える',
                              filename, lineno)
                name = m.group(1)
                if name in KEYWORDS:
                    _pp_error(f"キーワードはマクロ名にできない: {name}", filename, lineno)
                body = (m.group(2) or '').strip()
                if name in defines and defines[name] != body:
                    _pp_error(f"マクロの再定義（本体が異なる）: {name}", filename, lineno)
                defines[name] = body
                continue

            _pp_error(f"対応しない前処理指令: {stripped.split()[0]}", filename, lineno)

        # それ以外: 定義済みマクロを置換してから追加
        result_lines.append(_apply_defines(line, defines, filename, lineno))

    return '\n'.join(result_lines)


# ---- 字句解析器 ----

def tokenize(source: str, filename: str = '<input>') -> List[Token]:
    """前処理済みソーステキストをトークン列に変換する"""
    tokens: List[Token] = []
    i = 0
    line = 1
    n = len(source)

    while i < n:
        c = source[i]

        # 空白
        if c in ' \t\r':
            i += 1
            continue
        if c == '\n':
            line += 1
            i += 1
            continue

        # 行コメント //（ブロックコメント /* */ は言語仕様外）
        if source[i:i+2] == '//':
            while i < n and source[i] != '\n':
                i += 1
            continue

        # 整数リテラル（10 進のみ。先頭 0 は '0' 単独のみ）
        if c.isdigit():
            j = i
            while i < n and source[i].isdigit():
                i += 1
            text = source[j:i]
            if len(text) > 1 and text[0] == '0':
                _lex_error(f"整数リテラルの先頭を 0 にはできない（8進表記はない）: {text}",
                           filename, line)
            val = int(text)
            if val > INT_MAX:
                _lex_error(f"整数リテラルが上限 {INT_MAX} を超えている: {text}",
                           filename, line)
            tokens.append(Token(TK_NUM, val=val, line=line))
            continue

        # 文字リテラル 'x'
        if c == "'":
            i += 1
            if i >= n:
                _lex_error("文字リテラルが終端していない", filename, line)
            if source[i] == '\\' and i + 1 < n:
                i += 1
                ch = _escape_char(source[i], filename, line)
            else:
                ch = ord(source[i])
            i += 1
            if i >= n or source[i] != "'":
                _lex_error("文字リテラルが終端していない", filename, line)
            i += 1
            tokens.append(Token(TK_CHAR, val=ch, line=line))
            continue

        # 文字列リテラル "..."
        if c == '"':
            i += 1
            buf = []
            while i < n and source[i] != '"':
                if source[i] == '\\' and i + 1 < n:
                    i += 1
                    buf.append(chr(_escape_char(source[i], filename, line)))
                else:
                    if source[i] == '\n':
                        line += 1
                    buf.append(source[i])
                i += 1
            if i >= n:
                _lex_error("文字列リテラルが終端していない", filename, line)
            i += 1  # closing "
            tokens.append(Token(TK_STR, sval=''.join(buf), line=line))
            continue

        # 識別子・キーワード
        if c.isalpha() or c == '_':
            j = i
            while i < n and (source[i].isalnum() or source[i] == '_'):
                i += 1
            word = source[j:i]
            kind = TK_KW if word in KEYWORDS else TK_IDENT
            tokens.append(Token(kind, sval=word, line=line))
            continue

        # 3文字: ...（可変長引数、プロトタイプ宣言でのみ出現）
        if source[i:i+3] == '...':
            tokens.append(Token(TK_PUNCT, sval='...', line=line))
            i += 3
            continue

        # 2文字演算子（最長一致）
        matched = False
        for op in TWO_CHAR_PUNCTS:
            if source[i:i+len(op)] == op:
                tokens.append(Token(TK_PUNCT, sval=op, line=line))
                i += len(op)
                matched = True
                break
        if matched:
            continue

        # 1文字演算子・区切り記号
        if c in ONE_CHAR_PUNCTS:
            tokens.append(Token(TK_PUNCT, sval=c, line=line))
            i += 1
            continue

        _lex_error(f"予期しない文字: {c!r}", filename, line)

    tokens.append(Token(TK_EOF, line=line))
    return tokens
