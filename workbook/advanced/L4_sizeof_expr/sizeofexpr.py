#!/usr/bin/env python3
"""L4: sizeof 単項式(スケルトン)

sizeof x / sizeof *p / sizeof (a + 1) を実装する。

字句は変更しない('sizeof' は標準トラックでもキーワードとして読めている)。
構文(SizeofExpr ノードを作るところ)も langcc.py が済ませてある。
この回で書くのは「オペランドの型を求める」「その大きさを置く」
「大きさの決まらない型を弾く」の3つだけである。

要点は **オペランドを評価しないこと**。sizeof の答えはオペランドの
*静的な型* だけで決まる。cg.codegen(オペランド) を呼んでしまうと、
値としては同じ数が出るのに sizeof bump() で bump() が呼ばれてしまい、
「sizeof はオペランドを評価しない」という規定に違反する。
L2 の「複合代入の左辺は1回だけ評価される」と同型の罠である。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)              アセンブリを1行出力する
    cg.type_size(型)         型文字列のバイト数('int'→4、'char'→1、ポインタ→8)
    cg.is_ptr(型)            ポインタ型なら True
    cg.elem_ty(型)           ポインタの指す先の型('int*'→'int')
    cg.lval_type(左辺ノード)  Var / Deref / Index / Member の型文字列
    cg.var_type(名前, 行)     変数名から型文字列を引く
    cg.struct_tags()         本体まで定義されている構造体型の名前の一覧

    cg.codegen は **呼ばない**。ここに codegen が現れたら設計を間違えている。

langcc.py がこの3つを次の順に呼ぶ。
    ty = static_type_of(cg, node.operand)
    reject_incomplete(cg, ty, node.line)
    gen_sizeof_expr(cg, ty)

実装する順番:
    Step 1: static_type_of
    Step 2: gen_sizeof_expr
    Step 3: reject_incomplete

確認:
    python3 check.py
    python3 golden.py
"""


def static_type_of(cg, node):
    """Step 1: オペランドの静的な型を、コードを1行も出さずに求める。

    土台の mycc.py が持つ _type_of_expr と同じ規則を辿る。違うのは
    「型を知るためだけに辿る」ことで、値を作る命令は一切出さない点である。

    方針(node.kind で場合分けし、型を表す文字列を返す):
    - 'Var' / 'Deref' / 'Index' / 'Member' — 左辺値になれる節。
      型は既存の部品が知っているので cg.lval_type(node) に任せる
    - 'Str' — 文字列リテラルは 'char*'
    - 'Addr' — &e の型は「e の型 + '*'」
    - 'Assign' — 代入式の型は左辺の型
    - 'PreInc' / 'PreDec' — ++e / --e の型も左辺の型
    - 'Cond' — 条件演算子は then 側の型(土台の _type_of_expr と同じ扱い)
    - 'Add' — ポインタ + int / int + ポインタ はそのポインタ型。
      どちらもポインタでなければ 'int'(cg.is_ptr で判定する)
    - 'Sub' — 左辺がポインタなら そのポインタ型。
      そうでなければ 'int'(ポインタ同士の引き算は Core 仕様の外。L1 参照)
    - それ以外 — 'Num' / 'Neg' / 'Not' / 'Mul' / 'Div' / 'Mod' /
      比較 / '&&' / '||' / 'Call' / 'SizeofType' / 'SizeofExpr' は 'int'

    再帰するのは型を知るためだけである。cg.codegen は決して呼ばない。
    """
    raise NotImplementedError("Step 1: static_type_of を実装する")


def gen_sizeof_expr(cg, ty):
    """Step 2: 型のバイト数を a0 に置く。命令は1つだけ。

    方針:
        cg.emit(f'  li a0, {cg.type_size(ty)}')

    たった1行だが、ここに cg.codegen(オペランド) を足さないこと自体が
    「評価しない」という意味論の実装である。
    """
    raise NotImplementedError("Step 2: gen_sizeof_expr を実装する")


def reject_incomplete(cg, ty, line):
    """Step 3: 不完全型・void への sizeof をコンパイルエラーにする。

    サイズが決まらない型は2種類ある。
      - void            大きさを持たない
      - struct S        前方宣言だけで本体が無い(lib.h の struct FILE など)
    ポインタは指す先が不完全でもサイズ8で決まるので、通してよい。

    土台の size_of_ty_str は知らない型に既定値を返してしまうので、
    黙って嘘の数を出す前にここで止める。

    方針:
        cg.is_ptr(ty) なら何もせず返る
        ty == 'void' なら RuntimeError
        ty が 'struct ' で始まり、cg.struct_tags() に無ければ RuntimeError
      メッセージは "[line {line}] ..." で始める(土台のエラー表示に合わせる)。
    """
    raise NotImplementedError("Step 3: reject_incomplete を実装する")
