#!/usr/bin/env python3
"""L3: 可変長引数の定義(スケルトン)

int sum(int n, ...) を「定義」できるようにする。

定義側の '...' を構文で受理し直すのは varcc.py の parser shim の担当。
このファイルはコード生成側だけを担当する。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)                  アセンブリを1行出力する
    cg.codegen(式ノード)          式を評価して結果を a0 に置く
    cg.alloc_local(名前, 型)      ローカル変数の場所を確保する
    cg._locals[名前][0]           確保した場所の s0 からのオフセット

実装する順番:
    Step 1: reserve_save_area
    Step 2: gen_save_registers
    Step 3: is_arg_builtin / gen_arg_access

確認:
    python3 check.py
    python3 golden.py
"""

NUM_ARG_REGS = 8
SLOT_NAMES = [f'__va{i}' for i in range(NUM_ARG_REGS)]


def reserve_save_area(cg):
    """Step 1: save area 用のスロットを8個ぶん確保する。

    引数レジスタ a0〜a7 の中身を置くための場所を、
    フレームの中に8個(各8バイト)取る。

    方針: SLOT_NAMES の各名前について cg.alloc_local(名前, 'int*') を呼ぶ。
    ('int*' は8バイトの型として使っているだけで、意味は「8バイト確保」)

    alloc_local を続けて呼ぶと、場所は8バイトずつ下がっていく。
    つまり連続した領域になるので、あとから添字で読める。
    """
    raise NotImplementedError("Step 1: reserve_save_area を実装する")


def save_area_base(cg):
    """save area の先頭(= a0 を置く場所)のオフセット(完成済み)。"""
    return cg._locals[SLOT_NAMES[0]][0]


def gen_save_registers(cg):
    """Step 2: 関数の先頭で、引数レジスタ8本を save area へ書き出す。

    a0〜a7 は、関数に入った直後にしか正しい値が入っていない
    (すぐ次の計算や呼び出しで上書きされる)。
    だから「まだ何もしていない」この時点で、8本まとめて保存しておく。

    方針: base = save_area_base(cg) として、i = 0..7 について
        '  sd a{i}, {base - i * 8}(s0)'
    を出す。スロットは下へ向かって並んでいるので、引き算になる。
    """
    raise NotImplementedError("Step 2: gen_save_registers を実装する")


def is_arg_builtin(cg, node):
    """Step 3: node が組み込み関数 __arg(i) の呼び出しかどうか。

    方針: node.kind が 'Call' で、node.name が '__arg'、
    引数がちょうど1個なら True。
    """
    raise NotImplementedError("Step 3: is_arg_builtin を実装する")


def gen_arg_access(cg, node):
    """Step 3: __arg(i) — i 番目の引数を a0 に読み出す。

    添字 i は実行時に決まってよい(ループで回せる)ので、
    アドレスを計算してから ld する。

    方針:
    1. cg.codegen(node.args[0]) で a0 = i
    2. '  li a1, 8' と '  mul a0, a0, a1' で a0 = i * 8
    3. base = save_area_base(cg) として
         '  li a1, {base}'
         '  add a1, s0, a1'      → a1 = save area の先頭アドレス
    4. '  sub a0, a1, a0'        → a0 = 先頭 - i*8(下へ i 個ぶん)
    5. '  ld a0, 0(a0)'          → その場所の値を読む
    """
    raise NotImplementedError("Step 3: gen_arg_access を実装する")
