"""
構文解析器 — 教員提供スキャフォールド

Core プロファイル言語仕様の EBNF に基づく再帰下降パーサ。
トークン列を受け取り、トップレベル宣言の Node リストを返す。

注意: 標準トラックの受理範囲は仕様の全機能である。
複合代入 += -= *= /= %= は仕様の外側の機能で、発展トピック L2 が追加する。
"""

import sys
from typing import List, Tuple

from ast_def import *
from lexer import Token, TK_NUM, TK_CHAR, TK_STR, TK_IDENT, TK_KW, TK_PUNCT, TK_EOF

TYPE_KEYWORDS = ('int', 'char', 'void', 'struct')


def _parse_error(msg: str, line: int = 0) -> None:
    prefix = f"[line {line}] " if line else ""
    print(f"構文解析エラー: {prefix}{msg}", file=sys.stderr)
    sys.exit(1)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

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
        if self.cur.kind != TK_IDENT:
            _parse_error(f"識別子が期待されましたが '{self.cur.sval}' がありました", self.cur.line)
        name = self.cur.sval
        self.pos += 1
        return name

    # ---- 型判定 ----

    def is_type_start(self) -> bool:
        """現在のトークンが型の開始か判定する"""
        return self.cur.kind == TK_KW and self.cur.sval in TYPE_KEYWORDS

    # ---- 型のパース ----
    #
    # 言語仕様の型文法は、型を書ける位置ごとに 4 つに分かれる:
    #   scalar_type … 引数・struct フィールド（void 単独・struct 値は不可）
    #   obj_type    … 変数宣言・sizeof の型名（void 単独は不可）
    #   ret_type    … 関数の戻り値型（struct 値は不可。void 単独は可）
    # ここでは base と '*' の並びを読んでから位置ごとに検証する。

    def _parse_base_and_stars(self) -> Tuple[str, str]:
        """型の基底と '*' の並びを読み、('int', '**') のような組で返す"""
        if self.cur.kind == TK_KW and self.cur.sval in ('int', 'char', 'void'):
            base = self.cur.sval
            self.pos += 1
        elif self.cur.kind == TK_KW and self.cur.sval == 'struct':
            self.pos += 1
            tag = self.expect_ident()
            base = f'struct {tag}'
        else:
            _parse_error(f"型が期待されましたが '{self.cur.sval}' がありました", self.cur.line)

        stars = ''
        while self.cur.sval == '*':
            stars += '*'
            self.pos += 1
        return base, stars

    def parse_obj_type(self) -> str:
        """変数宣言・sizeof で使える型（obj_type）"""
        line = self.cur.line
        base, stars = self._parse_base_and_stars()
        if base == 'void' and not stars:
            _parse_error("void 型の変数は宣言できません", line)
        return base + stars

    def parse_scalar_type(self) -> str:
        """引数・struct フィールドで使える型（scalar_type）"""
        line = self.cur.line
        base, stars = self._parse_base_and_stars()
        if base == 'void' and not stars:
            _parse_error("void 型は使えません（void * は可）", line)
        if base.startswith('struct') and not stars:
            _parse_error("struct 値はここでは使えません（ポインタにする）", line)
        return base + stars

    # ---- トップレベル ----

    def parse_program(self) -> List[Node]:
        nodes: List[Node] = []
        if self.cur.kind == TK_EOF:
            _parse_error("プログラムには 1 個以上の外部宣言が必要です")
        while self.cur.kind != TK_EOF:
            # struct 定義・前方宣言（AST には出さない。scaffold はレイアウトを扱わない）
            if self.cur.sval == 'struct' and self.peek(2).sval in ('{', ';'):
                self._parse_struct_decl()
                continue

            line = self.cur.line
            base, stars = self._parse_base_and_stars()
            name = self.expect_ident()

            if self.cur.sval == '(':
                # 関数宣言 or 定義（ret_type: struct 値の戻り値は不可）
                if base.startswith('struct') and not stars:
                    _parse_error("struct 値の戻り値は使えません（ポインタにする）", line)
                nodes.append(self._parse_func(base + stars, name))
            else:
                # グローバル変数宣言（obj_type・初期化子なし）
                if base == 'void' and not stars:
                    _parse_error("void 型の変数は宣言できません", line)
                self.expect(';')
                nodes.append(Node(ND_DECL, name=name, ty_str=base + stars))

        return nodes

    def _parse_struct_decl(self) -> None:
        """`struct S { fields };`（定義）と `struct S;`（前方宣言）を処理する"""
        self.expect('struct')
        self.expect_ident()  # タグ名
        if self.consume_if(';'):
            return  # 前方宣言
        self.expect('{')
        self._parse_field()  # フィールドは 1 個以上
        while not self.consume_if('}'):
            if self.cur.kind == TK_EOF:
                _parse_error("'}' が見つかりません")
            self._parse_field()
        self.expect(';')

    def _parse_field(self) -> None:
        """field_decl ::= scalar_type IDENT ';'"""
        self.parse_scalar_type()
        self.expect_ident()
        self.expect(';')

    def _parse_func(self, ty_str: str, name: str) -> Node:
        self.expect('(')
        params: List[Node] = []
        variadic = False

        if not self.consume_if(')'):
            while True:
                if self.cur.sval == '...':
                    if not params:
                        _parse_error("可変長 '...' は 1 個以上の固定引数の後にのみ書けます",
                                     self.cur.line)
                    self.pos += 1
                    variadic = True
                    break
                p_ty = self.parse_scalar_type()
                p_name = self.expect_ident()  # 仮引数は名前必須
                params.append(Node(ND_DECL, name=p_name, ty_str=p_ty))
                if not self.consume_if(','):
                    break
            self.expect(')')

        # 関数宣言（; で終わり）
        if self.consume_if(';'):
            return Node(ND_FUNCPROTO, name=name, ty_str=ty_str, params=params)

        # 関数定義
        if variadic:
            _parse_error("可変長 '...' はプロトタイプ宣言でのみ使えます", self.cur.line)
        body = self.parse_func_body()
        return Node(ND_FUNCDEF, name=name, ty_str=ty_str, params=params, body=body)

    # ---- ブロックと文 ----

    def parse_func_body(self) -> Node:
        """関数本体。局所宣言は先頭にのみ置ける"""
        line = self.cur.line
        self.expect('{')
        stmts: List[Node] = []
        while self.is_type_start():
            stmts.append(self._parse_local_decl())
        while not self.consume_if('}'):
            if self.cur.kind == TK_EOF:
                _parse_error("'}' が見つかりません", line)
            stmts.append(self.parse_stmt())
        return Node(ND_BLOCK, stmts=stmts, line=line)

    def parse_block(self) -> Node:
        """入れ子ブロック。文のみを含む（宣言は関数本体の先頭のみ）"""
        line = self.cur.line
        self.expect('{')
        stmts: List[Node] = []
        while not self.consume_if('}'):
            if self.cur.kind == TK_EOF:
                _parse_error("'}' が見つかりません", line)
            stmts.append(self.parse_stmt())
        return Node(ND_BLOCK, stmts=stmts, line=line)

    def _parse_local_decl(self) -> Node:
        line = self.cur.line
        ty_str = self.parse_obj_type()
        name = self.expect_ident()
        self.expect(';')
        return Node(ND_DECL, name=name, ty_str=ty_str, line=line)

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
        # assign_expr ::= unary_expr '=' assign_expr | cond_expr
        # cond_expr まで読んでから '=' を確認する（cond_expr も unary_expr を含む）
        node = self._parse_cond()
        if self.consume_if('='):
            rhs = self._parse_assign()  # 右結合
            return Node(ND_ASSIGN, lhs=node, rhs=rhs, line=node.line)
        return node

    def _parse_cond(self) -> Node:
        # cond_expr ::= lor_expr [ '?' expr ':' cond_expr ]（右結合）
        node = self._parse_lor()
        if self.consume_if('?'):
            then = self.parse_expr()
            self.expect(':')
            else_ = self._parse_cond()
            return Node(ND_COND, cond=node, then=then, else_=else_, line=node.line)
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

    def _parse_lor(self)  -> Node: return self._parse_binary({'||': ND_OR},  self._parse_land)
    def _parse_land(self) -> Node: return self._parse_binary({'&&': ND_AND}, self._parse_eq)
    def _parse_eq(self)   -> Node: return self._parse_binary({'==': ND_EQ, '!=': ND_NE}, self._parse_rel)

    def _parse_rel(self) -> Node:
        """比較演算子。> / >= は lhs・rhs を swap して LT / LE に正規化する"""
        node = self._parse_add()
        while self.cur.sval in ('<', '>', '<=', '>='):
            op   = self.cur.sval
            line = self.cur.line
            self.pos += 1
            rhs  = self._parse_add()
            if op == '<':
                node = Node(ND_LT, lhs=node, rhs=rhs, line=line)
            elif op == '>':
                node = Node(ND_LT, lhs=rhs,  rhs=node, line=line)  # swap
            elif op == '<=':
                node = Node(ND_LE, lhs=node, rhs=rhs, line=line)
            else:  # >=
                node = Node(ND_LE, lhs=rhs,  rhs=node, line=line)  # swap
        return node

    def _parse_add(self) -> Node: return self._parse_binary({'+': ND_ADD, '-': ND_SUB}, self._parse_mul)
    def _parse_mul(self) -> Node: return self._parse_binary({'*': ND_MUL, '/': ND_DIV, '%': ND_MOD}, self._parse_unary)

    def _parse_unary(self) -> Node:
        tok = self.cur
        if self.consume_if('-'):
            return Node(ND_NEG,    operand=self._parse_unary(), line=tok.line)
        if self.consume_if('!'):
            return Node(ND_NOT,    operand=self._parse_unary(), line=tok.line)
        if self.consume_if('*'):
            return Node(ND_DEREF,  operand=self._parse_unary(), line=tok.line)
        if self.consume_if('&'):
            return Node(ND_ADDR,   operand=self._parse_unary(), line=tok.line)
        if self.consume_if('++'):
            return Node(ND_PREINC, operand=self._parse_unary(), line=tok.line)
        if self.consume_if('--'):
            return Node(ND_PREDEC, operand=self._parse_unary(), line=tok.line)
        if self.cur.sval == 'sizeof':
            return self._parse_sizeof()
        return self._parse_postfix()

    def _parse_sizeof(self) -> Node:
        line = self.cur.line
        self.pos += 1  # 'sizeof'
        # sizeof は型名形式のみ（sizeof 式 は言語仕様外）
        if not (self.cur.sval == '(' and self._peek_is_type()):
            _parse_error("sizeof は sizeof(型名) 形式のみ使えます", line)
        self.expect('(')
        ty = self.parse_obj_type()
        self.expect(')')
        return Node(ND_SIZEOF_TYPE, ty_str=ty, line=line)

    def _peek_is_type(self) -> bool:
        """'(' の次のトークンが型の開始か"""
        tok = self.peek(1)
        return tok.kind == TK_KW and tok.sval in TYPE_KEYWORDS

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
            elif self.cur.sval == '.':
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
