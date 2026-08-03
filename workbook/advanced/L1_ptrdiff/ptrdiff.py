#!/usr/bin/env python3
"""L1: ポインタ同士の引き算(スケルトン)

p - q は「アドレスの差(バイト数)」ではなく「要素いくつ分か」を返す。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)                    アセンブリを1行出力する
    cg.codegen(式ノード)            式を評価して結果を a0 に置く
    cg._push_a0() / cg._pop_into(reg)   値の退避・復元
    cg._type_of_expr(式ノード)      式の型(ty_str)を返す
    cg.size_of_ty_str(ty, cg._struct_defs)  型のバイトサイズ

実装する順番:
    Step 1: is_ptr_diff
    Step 2: gen_ptr_diff

確認:
    python3 check.py
    python3 golden.py
"""


def is_ptr(ty):
    """ty_str がポインタ型か(完成済み)。"""
    return ty.endswith('*')


def elem_size(cg, ty):
    """ポインタ ty の指す先のサイズ(完成済み)。

    'int*' なら 'int' のサイズ = 4 を返す。
    """
    return cg.size_of_ty_str(ty[:-1], cg._struct_defs)


def is_ptr_diff(cg, node):
    """Step 1: node が「ポインタ − ポインタ」の引き算かどうか。

    方針:
    - node.kind が 'Sub' でなければ False
    - 左辺・右辺の型を cg._type_of_expr() で取り、
      両方が is_ptr() なら True

    注意: p - 3(ポインタ − 整数)は対象外。
    こちらは既存のコード生成が正しく処理している。
    """
    raise NotImplementedError("Step 1: is_ptr_diff を実装する")


def gen_ptr_diff(cg, node):
    """Step 2: p - q を「要素いくつ分か」として生成する。

    方針:
    1. 左辺を codegen して cg._push_a0() で退避
    2. 右辺を codegen
    3. cg._pop_into('a1') で左辺を戻す
    4. '  sub a0, a1, a0' でアドレスの差(バイト数)を求める
    5. 要素サイズが 1 でなければ、そのサイズで割る
         '  li a1, {size}'
         '  div a0, a0, a1'
       (要素サイズは elem_size(cg, cg._type_of_expr(node.lhs)) で取れる)

    1〜3 はコマ2 以来の二項演算のパターンそのままである。
    """
    raise NotImplementedError("Step 2: gen_ptr_diff を実装する")
