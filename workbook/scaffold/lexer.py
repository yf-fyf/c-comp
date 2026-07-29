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
from typing import List, Dict

# ---- トークン種別 ----
TK_NUM   = 'TK_NUM'    # 整数リテラル
TK_CHAR  = 'TK_CHAR'   # 文字リテラル（int として扱う）
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

# 2文字演算子（長いものを先に並べる）
TWO_CHAR_PUNCTS = [
    '==', '!=', '<=', '>=', '&&', '||', '<<', '>>', '->',
]

ONE_CHAR_PUNCTS = set('+-*/%&|^~!<>=;:,.(){}[]')


@dataclass
class Token:
    kind: str
    val:  int = 0    # TK_NUM / TK_CHAR
    sval: str = ''   # TK_IDENT / TK_KW / TK_PUNCT / TK_STR
    line: int = 0


def _lex_error(msg: str, filename: str, line: int) -> None:
    print(f"{filename}:{line}: 字句解析エラー: {msg}", file=sys.stderr)
    sys.exit(1)


def _escape_char(c: str) -> int:
    """バックスラッシュエスケープ文字を文字コードに変換"""
    return {'n': 10, 't': 9, '\\': 92, "'": 39, '"': 34, '0': 0, 'r': 13}.get(c, ord(c))


# ---- 前処理器 ----

def preprocess(source: str,
               filename: str = '<input>',
               defines: Dict[str, str] = None,
               include_dirs: List[str] = None) -> str:
    """
    #include "file.h" と #define NAME value を処理する。
    関数形式マクロ・条件コンパイルは対象外（Core プロファイル外）。
    """
    if defines is None:
        defines = {}
    if include_dirs is None:
        # ファイル自身のディレクトリと scaffold/ を検索パスに含める
        file_dir = os.path.dirname(os.path.abspath(filename))
        scaffold_dir = os.path.dirname(os.path.abspath(__file__))
        include_dirs = [file_dir, scaffold_dir, '.']

    result_lines = []
    for lineno, line in enumerate(source.split('\n'), 1):
        stripped = line.strip()

        # #include "file.h"
        if stripped.startswith('#include'):
            m = re.match(r'#include\s+"([^"]+)"', stripped)
            if m:
                fname = m.group(1)
                found = False
                for d in include_dirs:
                    path = os.path.join(d, fname)
                    if os.path.exists(path):
                        with open(path, 'r', encoding='utf-8') as f:
                            included = preprocess(f.read(), path, defines, include_dirs)
                        result_lines.append(included)
                        found = True
                        break
                if not found:
                    _lex_error(f"ファイルが見つからない: {fname}", filename, lineno)
            continue

        # #define NAME value
        if stripped.startswith('#define'):
            m = re.match(r'#define\s+(\w+)\s+(.*)', stripped)
            if m:
                defines[m.group(1)] = m.group(2).strip()
            continue

        # それ以外: 定義済みマクロを置換してから追加
        for name, val in defines.items():
            line = re.sub(r'\b' + re.escape(name) + r'\b', val, line)
        result_lines.append(line)

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

        # 行コメント //
        if source[i:i+2] == '//':
            while i < n and source[i] != '\n':
                i += 1
            continue

        # ブロックコメント /* */
        if source[i:i+2] == '/*':
            i += 2
            while i < n - 1:
                if source[i] == '\n':
                    line += 1
                if source[i:i+2] == '*/':
                    i += 2
                    break
                i += 1
            continue

        # 整数リテラル
        if c.isdigit():
            j = i
            while i < n and source[i].isdigit():
                i += 1
            tokens.append(Token(TK_NUM, val=int(source[j:i]), line=line))
            continue

        # 文字リテラル 'x'
        if c == "'":
            i += 1
            if i >= n:
                _lex_error("文字リテラルが終端していない", filename, line)
            if source[i] == '\\' and i + 1 < n:
                i += 1
                ch = _escape_char(source[i])
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
                    buf.append(chr(_escape_char(source[i])))
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

        # 3文字: ...（可変長引数、lib.h の宣言でのみ出現）
        if source[i:i+3] == '...':
            tokens.append(Token(TK_PUNCT, sval='...', line=line))
            i += 3
            continue

        # 2文字演算子
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
