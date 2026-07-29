#!/usr/bin/env python3
"""L1: 構造体の代入(スケルトン)

q = p; のように構造体をまるごとコピーできるようにする。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)                     アセンブリを1行出力する
    cg.codegen_lval(式ノード)        式のアドレスを a0 に置く
    cg._push_a0() / cg._pop_into(reg)    値の退避・復元
    cg._type_of_lval(式ノード)       代入先の型(ty_str)
    cg._struct_defs                 構造体名 → {'size': N, 'fields': {...}}

実装する順番:
    Step 1: is_struct_assign
    Step 2: gen_struct_copy

確認:
    python3 check.py
    python3 golden.py
"""


def struct_size(cg, ty):
    """構造体型ならサイズ、そうでなければ None(完成済み)。"""
    info = cg._struct_defs.get(ty)
    return info['size'] if info else None


def is_struct_assign(cg, node):
    """Step 1: node が「構造体同士の代入」かどうか。

    方針:
    - node.kind が 'Assign' でなければ False
    - 左辺の型を cg._type_of_lval(node.lhs) で取り、
      struct_size() が None でなければ True

    int や ポインタの代入(いままで動いていたもの)は False になる。
    """
    raise NotImplementedError("Step 1: is_struct_assign を実装する")


def gen_struct_copy(cg, node):
    """Step 2: 構造体をまるごとコピーする。

    ふつうの代入は「右辺の値」を a0 に載せるが、構造体は
    レジスタ1本に載らない。そこで、両辺の **アドレス** を用意して
    メモリからメモリへ写す。

    方針:
    1. size = struct_size(cg, cg._type_of_lval(node.lhs)) を求める
    2. cg.codegen_lval(node.lhs) で書き込み先のアドレス → cg._push_a0()
    3. cg.codegen_lval(node.rhs) で読み出し元のアドレス(値ではない)
    4. cg._pop_into('a1') で書き込み先を a1 に戻す
       → a0 = 読み出し元、a1 = 書き込み先
    5. オフセット 0 から size バイトぶん、8 → 4 → 1 バイトの順に写す
         '  ld a2, {off}(a0)' / '  sd a2, {off}(a1)'      (8バイト)
         '  lw a2, {off}(a0)' / '  sw a2, {off}(a1)'      (4バイト)
         '  lb a2, {off}(a0)' / '  sb a2, {off}(a1)'      (1バイト)
       大きい単位から使うと命令数が少なくて済む
    6. 最後に '  mv a0, a1' として、代入式の値を左辺のアドレスにしておく
    """
    raise NotImplementedError("Step 2: gen_struct_copy を実装する")
