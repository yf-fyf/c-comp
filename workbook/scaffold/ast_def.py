"""
AST ノード定義 — 教員提供スキャフォールド

Phase 0–1 全体を通じて使用する。学生はこのファイルを変更しない。
"""

from dataclasses import dataclass, field
from typing import Optional, List

# ---- ノード種別定数 ----

# リテラル
ND_NUM    = 'Num'       # 整数リテラル・文字リテラル  val: int
ND_STR    = 'Str'       # 文字列リテラル              sval: str

# 変数・代入
ND_VAR    = 'Var'       # 変数参照（lvalue / rvalue）  name: str
ND_ASSIGN = 'Assign'    # =                            lhs, rhs

# 二項算術
ND_ADD = 'Add'          # +
ND_SUB = 'Sub'          # -
ND_MUL = 'Mul'          # *
ND_DIV = 'Div'          # /
ND_MOD = 'Mod'          # %

# 単項
ND_NEG    = 'Neg'       # 単項 -         operand
ND_NOT    = 'Not'       # !              operand
ND_ADDR   = 'Addr'      # & アドレス取得  operand
ND_DEREF  = 'Deref'     # * 間接参照      operand
ND_PREINC = 'PreInc'    # 前置 ++        operand
ND_PREDEC = 'PreDec'    # 前置 --        operand

# 比較（> / >= は lhs・rhs を swap して LT / LE に正規化）
ND_EQ = 'Eq'            # ==
ND_NE = 'Ne'            # !=
ND_LT = 'Lt'            # <   （a > b は Node(LT, lhs=b, rhs=a) で表現）
ND_LE = 'Le'            # <=  （a >= b は Node(LE, lhs=b, rhs=a) で表現）

# 論理
ND_AND = 'And'          # &&
ND_OR  = 'Or'           # ||

# 条件（三項）
ND_COND = 'Cond'        # a ? b : c      cond, then, else_

# ポインタ・複合
ND_INDEX  = 'Index'     # p[i]           lhs=ポインタ, rhs=添字
ND_MEMBER = 'Member'    # x.f / p->f     operand, name, is_arrow: bool

# sizeof（型名形式のみ）
ND_SIZEOF_TYPE = 'SizeofType'   # sizeof(type)  ty_str

# 関数呼び出し
ND_CALL = 'Call'        # f(args)        name, args: List[Node]

# 文
ND_BLOCK    = 'Block'       # { stmts }           stmts: List[Node]
ND_EXPRSTMT = 'ExprStmt'    # expr;               operand (None = 空文)
ND_RETURN   = 'Return'      # return [expr];      operand (None = void)
ND_BREAK    = 'Break'       # break;
ND_CONTINUE = 'Continue'    # continue;
ND_IF       = 'If'          # if/else             cond, then, else_
ND_WHILE    = 'While'       # while               cond, body
ND_FOR      = 'For'         # for                 init, cond, step, body
ND_DECL     = 'Decl'        # 変数宣言（初期化子なし）  name, ty_str

# トップレベル
ND_FUNCDEF   = 'FuncDef'    # 関数定義  name, ty_str, params, body
ND_FUNCPROTO = 'FuncProto'  # 関数宣言  name, ty_str, params


@dataclass
class Node:
    kind: str

    # 二項演算 / if・三項の各枝
    lhs:   Optional['Node'] = None
    rhs:   Optional['Node'] = None
    cond:  Optional['Node'] = None
    then:  Optional['Node'] = None
    else_: Optional['Node'] = None

    # ループ
    init: Optional['Node'] = None
    step: Optional['Node'] = None
    body: Optional['Node'] = None

    # 単項演算・return のオペランド
    operand: Optional['Node'] = None

    # リスト形フィールド
    stmts:  List['Node'] = field(default_factory=list)   # Block の本体
    args:   List['Node'] = field(default_factory=list)   # 関数呼び出し引数
    params: List['Node'] = field(default_factory=list)   # 関数パラメータ (Decl)

    # 値・名前
    val:  int = 0    # ND_NUM
    sval: str = ''   # ND_STR（文字列内容）
    name: str = ''   # ND_VAR / ND_CALL / ND_MEMBER / ND_FUNCDEF / ND_DECL

    # 型情報（文字列表現: 'int', 'char', 'int*', 'struct Node*', ...）
    # コード生成器が付与してもよいし、Parser が付与してもよい
    ty_str: str = ''

    # Member: -> か . か
    is_arrow: bool = False

    # デバッグ用（字句トークンの行番号）
    line: int = 0

    def __repr__(self):
        return f"Node({self.kind!r}, name={self.name!r}, val={self.val})"
