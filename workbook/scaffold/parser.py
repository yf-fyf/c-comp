"""
構文解析器 — 教員提供スキャフォールド

Core プロファイル言語仕様の EBNF に基づく再帰下降パーサ。
トークン列を受け取り、トップレベル宣言の Node リストを返す。
"""

import sys
from typing import List, Optional, Set

from ast_def import *
from lexer import Token, TK_NUM, TK_CHAR, TK_STR, TK_IDENT, TK_KW, TK_PUNCT, TK_EOF


def _parse_error(msg: str, line: int = 0) -> None:
    prefix = f"[line {line}] " if line else ""
    print(f"構文解析エラー: {prefix}{msg}", file=sys.stderr)
    sys.exit(1)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        # typedef で定義された型名を追跡（is_type_start で利用）
        self.typedef_names: Set[str] = set()

    # ---- トークン操作 ----

    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        p = self.pos + offset
        return self.tokens[min(p, len(self.tokens) - 1)]

    def advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def consume_if(self, s: str) -> bool:
        if self.cur.sval == s:
            self.pos += 1
            return True
        return False

    def expect(self, s: str) -> None:
        if self.cur.sval != s:
            _parse_error(f"'{s}' が期待されましたが '{self.cur.sval}' がありました", self.cur.line)
        self.pos += 1

    def expect_ident(self) -> str:
        if self.cur.kind not in (TK_IDENT, TK_KW):
            _parse_error(f"識別子が期待されましたが '{self.cur.sval}' がありました", self.cur.line)
        name = self.cur.sval
        self.pos += 1
        return name

    # ---- 型判定 ----

    def is_type_start(self) -> bool:
        """現在のトークンが型宣言の開始か判定する"""
        if self.cur.kind == TK_KW and self.cur.sval in ('int', 'char', 'void', 'struct'):
            return True
        if self.cur.kind == TK_IDENT and self.cur.sval in self.typedef_names:
            return True
        return False

    # ---- 型のパース ----

    def parse_type(self) -> str:
        """
        型を文字列として返す（例: 'int', 'char*', 'struct Node*', 'void'）
        ポインタの * は型文字列に含める。
        """
        if self.cur.kind == TK_KW and self.cur.sval in ('int', 'char', 'void'):
            base = self.cur.sval
            self.pos += 1
        elif self.cur.sval == 'struct':
            self.pos += 1
            tag = ''
            if self.cur.kind == TK_IDENT:
                tag = self.cur.sval
                self.pos += 1
            base = f'struct {tag}' if tag else 'struct'
            # インライン struct 定義 { ... } はスキップ
            if self.cur.sval == '{':
                self._skip_braces()
        elif self.cur.kind == TK_IDENT and self.cur.sval in self.typedef_names:
            base = self.cur.sval
            self.pos += 1
        else:
            _parse_error(f"型が期待されましたが '{self.cur.sval}' がありました", self.cur.line)
            base = ''  # unreachable

        # ポインタ *
        stars = ''
        while self.cur.sval == '*':
            stars += '*'
            self.pos += 1

        return base + stars

    def _skip_braces(self) -> None:
        """{ ... } ブロックを読み飛ばす（ネスト対応）"""
        self.expect('{')
        depth = 1
        while depth > 0:
            if self.cur.kind == TK_EOF:
                _parse_error("'}' が見つかりません")
            if self.cur.sval == '{':
                depth += 1
            elif self.cur.sval == '}':
                depth -= 1
            self.pos += 1

    # ---- トップレベル ----

    def parse_program(self) -> List[Node]:
        nodes: List[Node] = []
        while self.cur.kind != TK_EOF:
            # typedef
            if self.cur.sval == 'typedef':
                self.pos += 1
                self._parse_typedef()
                continue

            ty_str = self.parse_type()

            # 宣言子を伴わない struct 定義（`struct S { ... };` と前方宣言 `struct S;`）。
            # AST には出さない。フィールドの配置はコード生成側が原稿から読むので、
            # ここでは読み捨てるだけでよい。
            if self.cur.sval == ';' and ty_str.startswith('struct'):
                self.pos += 1
                continue

            name = self.expect_ident()

            if self.cur.sval == '(':
                # 関数宣言 or 定義
                nodes.append(self._parse_func(ty_str, name))
            else:
                # グローバル変数宣言
                arr = self._parse_array_suffix()
                init_expr = None
                if self.consume_if('='):
                    init_expr = self.parse_expr()
                self.expect(';')
                nodes.append(Node(ND_DECL, name=name, ty_str=ty_str + arr, init_expr=init_expr))

        return nodes

    def _parse_typedef(self) -> None:
        """typedef を処理して型名を typedef_names に登録する"""
        if self.cur.sval == 'struct':
            self.pos += 1
            if self.cur.kind == TK_IDENT:
                self.pos += 1  # struct タグ名
            if self.cur.sval == '{':
                self._skip_braces()
        elif self.cur.kind in (TK_KW, TK_IDENT):
            self.pos += 1
        # ポインタ
        while self.cur.sval == '*':
            self.pos += 1
        # 新しい typedef 名
        if self.cur.kind == TK_IDENT:
            self.typedef_names.add(self.cur.sval)
            self.pos += 1
        self.expect(';')

    def _parse_func(self, ty_str: str, name: str) -> Node:
        self.expect('(')
        params: List[Node] = []

        if not self.consume_if(')'):
            # void のみの場合: int f(void)
            if self.cur.sval == 'void' and self.peek().sval == ')':
                self.pos += 2
            else:
                while True:
                    # '...' は可変長引数マーカー（lib.h の宣言でのみ使用）
                    if self.cur.sval == '...':
                        self.pos += 1
                        break
                    p_ty = self.parse_type()
                    p_name = ''
                    if self.cur.kind == TK_IDENT:
                        p_name = self.cur.sval
                        self.pos += 1
                    params.append(Node(ND_DECL, name=p_name, ty_str=p_ty))
                    if not self.consume_if(','):
                        break
                self.expect(')')

        # 関数宣言（; で終わり）
        if self.consume_if(';'):
            return Node(ND_FUNCPROTO, name=name, ty_str=ty_str, params=params)

        # 関数定義
        body = self.parse_block()
        return Node(ND_FUNCDEF, name=name, ty_str=ty_str, params=params, body=body)

    def _parse_array_suffix(self) -> str:
        """'[' INT_LITERAL ']' があれば '[N]' を返す。なければ空文字列"""
        if self.cur.sval != '[':
            return ''
        self.pos += 1
        if self.cur.kind != TK_NUM:
            _parse_error("配列サイズに整数定数が必要です", self.cur.line)
        size = self.cur.val
        self.pos += 1
        self.expect(']')
        return f'[{size}]'

    # ---- ブロックと文 ----

    def parse_block(self) -> Node:
        line = self.cur.line
        self.expect('{')
        stmts: List[Node] = []
        # C89 スタイル: 宣言を先頭に
        while self.is_type_start():
            stmts.append(self._parse_local_decl())
        while not self.consume_if('}'):
            if self.cur.kind == TK_EOF:
                _parse_error("'}' が見つかりません", line)
            stmts.append(self.parse_stmt())
        return Node(ND_BLOCK, stmts=stmts, line=line)

    def _parse_local_decl(self) -> Node:
        line = self.cur.line
        ty_str = self.parse_type()
        name = self.expect_ident()
        arr = self._parse_array_suffix()
        init_expr = None
        if self.consume_if('='):
            init_expr = self.parse_expr()
        self.expect(';')
        return Node(ND_DECL, name=name, ty_str=ty_str + arr, init_expr=init_expr, line=line)

    def parse_stmt(self) -> Node:
        tok = self.cur

        if tok.sval == 'return':
            self.pos += 1
            if self.consume_if(';'):
                return Node(ND_RETURN, line=tok.line)
            expr = self.parse_expr()
            self.expect(';')
            return Node(ND_RETURN, operand=expr, line=tok.line)

        if tok.sval == 'break':
            self.pos += 1
            self.expect(';')
            return Node(ND_BREAK, line=tok.line)

        if tok.sval == 'continue':
            self.pos += 1
            self.expect(';')
            return Node(ND_CONTINUE, line=tok.line)

        if tok.sval == 'if':
            return self._parse_if()

        if tok.sval == 'while':
            return self._parse_while()

        if tok.sval == 'for':
            return self._parse_for()

        if tok.sval == '{':
            return self.parse_block()

        # 空文
        if self.consume_if(';'):
            return Node(ND_EXPRSTMT, line=tok.line)

        # 式文
        expr = self.parse_expr()
        self.expect(';')
        return Node(ND_EXPRSTMT, operand=expr, line=tok.line)

    def _parse_if(self) -> Node:
        line = self.cur.line
        self.pos += 1  # 'if'
        self.expect('(')
        cond = self.parse_expr()
        self.expect(')')
        then = self.parse_stmt()
        else_ = None
        if self.cur.sval == 'else':
            self.pos += 1
            else_ = self.parse_stmt()
        return Node(ND_IF, cond=cond, then=then, else_=else_, line=line)

    def _parse_while(self) -> Node:
        line = self.cur.line
        self.pos += 1  # 'while'
        self.expect('(')
        cond = self.parse_expr()
        self.expect(')')
        body = self.parse_stmt()
        return Node(ND_WHILE, cond=cond, body=body, line=line)

    def _parse_for(self) -> Node:
        line = self.cur.line
        self.pos += 1  # 'for'
        self.expect('(')
        init = None if self.cur.sval == ';' else self.parse_expr()
        self.expect(';')
        cond = None if self.cur.sval == ';' else self.parse_expr()
        self.expect(';')
        step = None if self.cur.sval == ')' else self.parse_expr()
        self.expect(')')
        body = self.parse_stmt()
        return Node(ND_FOR, init=init, cond=cond, step=step, body=body, line=line)

    # ---- 式（優先順位: 低い順に定義）----

    def parse_expr(self) -> Node:
        return self._parse_assign()

    def _parse_assign(self) -> Node:
        # assign_expr ::= unary_expr '=' assign_expr | lor_expr
        # lor_expr まで読んでから '=' を確認する（lor_expr も unary_expr を含む）
        node = self._parse_lor()
        if self.consume_if('='):
            rhs = self._parse_assign()  # 右結合
            return Node(ND_ASSIGN, lhs=node, rhs=rhs, line=node.line)
        return node

    def _parse_binary(self, op_map: dict, next_fn) -> Node:
        """左結合の二項演算を汎用的にパースする"""
        node = next_fn()
        while self.cur.sval in op_map:
            kind = op_map[self.cur.sval]
            line = self.cur.line
            self.pos += 1
            node = Node(kind, lhs=node, rhs=next_fn(), line=line)
        return node

    def _parse_lor(self)    -> Node: return self._parse_binary({'||': ND_OR},     self._parse_land)
    def _parse_land(self)   -> Node: return self._parse_binary({'&&': ND_AND},    self._parse_bitor)
    def _parse_bitor(self)  -> Node: return self._parse_binary({'|':  ND_BITOR},  self._parse_bitxor)
    def _parse_bitxor(self) -> Node: return self._parse_binary({'^':  ND_BITXOR}, self._parse_bitand)
    def _parse_bitand(self) -> Node: return self._parse_binary({'&':  ND_BITAND}, self._parse_eq)
    def _parse_eq(self)     -> Node: return self._parse_binary({'==': ND_EQ, '!=': ND_NE}, self._parse_rel)

    def _parse_rel(self) -> Node:
        """比較演算子。> / >= は lhs・rhs を swap して LT / LE に正規化する"""
        node = self._parse_shift()
        while self.cur.sval in ('<', '>', '<=', '>='):
            op   = self.cur.sval
            line = self.cur.line
            self.pos += 1
            rhs  = self._parse_shift()
            if op == '<':
                node = Node(ND_LT, lhs=node, rhs=rhs, line=line)
            elif op == '>':
                node = Node(ND_LT, lhs=rhs,  rhs=node, line=line)  # swap
            elif op == '<=':
                node = Node(ND_LE, lhs=node, rhs=rhs, line=line)
            else:  # >=
                node = Node(ND_LE, lhs=rhs,  rhs=node, line=line)  # swap
        return node

    def _parse_shift(self) -> Node: return self._parse_binary({'<<': ND_SHL, '>>': ND_SHR}, self._parse_add)
    def _parse_add(self)   -> Node: return self._parse_binary({'+': ND_ADD, '-': ND_SUB},   self._parse_mul)
    def _parse_mul(self)   -> Node: return self._parse_binary({'*': ND_MUL, '/': ND_DIV, '%': ND_MOD}, self._parse_unary)

    def _parse_unary(self) -> Node:
        tok = self.cur
        if self.consume_if('-'):
            return Node(ND_NEG,    operand=self._parse_unary(), line=tok.line)
        if self.consume_if('!'):
            return Node(ND_NOT,    operand=self._parse_unary(), line=tok.line)
        if self.consume_if('~'):
            return Node(ND_BITNOT, operand=self._parse_unary(), line=tok.line)
        if self.consume_if('*'):
            return Node(ND_DEREF,  operand=self._parse_unary(), line=tok.line)
        if self.consume_if('&'):
            return Node(ND_ADDR,   operand=self._parse_unary(), line=tok.line)
        if self.cur.sval == 'sizeof':
            return self._parse_sizeof()
        return self._parse_postfix()

    def _parse_sizeof(self) -> Node:
        line = self.cur.line
        self.pos += 1  # 'sizeof'
        # sizeof '(' type ')' か sizeof expr か
        if self.cur.sval == '(' and self._peek_is_type():
            self.expect('(')
            ty = self.parse_type()
            self.expect(')')
            return Node(ND_SIZEOF_TYPE, ty_str=ty, line=line)
        return Node(ND_SIZEOF_EXPR, operand=self._parse_unary(), line=line)

    def _peek_is_type(self) -> bool:
        """'(' の次のトークンが型の開始か"""
        tok = self.peek(1)
        if tok.kind == TK_KW and tok.sval in ('int', 'char', 'void', 'struct'):
            return True
        if tok.kind == TK_IDENT and tok.sval in self.typedef_names:
            return True
        return False

    def _parse_postfix(self) -> Node:
        node = self._parse_primary()
        while True:
            if self.consume_if('['):
                idx = self.parse_expr()
                self.expect(']')
                node = Node(ND_INDEX, lhs=node, rhs=idx, line=node.line)
            elif self.consume_if('->'):
                name = self.expect_ident()
                node = Node(ND_MEMBER, operand=node, name=name, is_arrow=True, line=node.line)
            elif self.cur.sval == '.' and self.peek().kind in (TK_IDENT, TK_KW):
                self.pos += 1
                name = self.expect_ident()
                node = Node(ND_MEMBER, operand=node, name=name, is_arrow=False, line=node.line)
            else:
                break
        return node

    def _parse_primary(self) -> Node:
        tok = self.cur

        # 整数リテラル・文字リテラル
        if tok.kind in (TK_NUM, TK_CHAR):
            self.pos += 1
            return Node(ND_NUM, val=tok.val, line=tok.line)

        # 文字列リテラル
        if tok.kind == TK_STR:
            self.pos += 1
            return Node(ND_STR, sval=tok.sval, line=tok.line)

        # グループ化
        if self.consume_if('('):
            node = self.parse_expr()
            self.expect(')')
            return node

        # 識別子（変数参照 or 関数呼び出し）
        if tok.kind == TK_IDENT:
            self.pos += 1
            if self.consume_if('('):
                args: List[Node] = []
                if not self.consume_if(')'):
                    args.append(self.parse_expr())
                    while self.consume_if(','):
                        args.append(self.parse_expr())
                    self.expect(')')
                return Node(ND_CALL, name=tok.sval, args=args, line=tok.line)
            return Node(ND_VAR, name=tok.sval, line=tok.line)

        _parse_error(f"式が期待されましたが '{tok.sval}' がありました", tok.line)


# ---- エントリポイント ----

def parse(tokens: List[Token]) -> List[Node]:
    """
    トークン列を受け取り、トップレベル宣言の Node リストを返す。
    """
    return Parser(tokens).parse_program()
