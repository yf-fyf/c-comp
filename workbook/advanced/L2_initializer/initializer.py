#!/usr/bin/env python3
"""L2: 初期化子リスト(スケルトン)

int a[3] = {1, 2, 3};  や  char s[6] = "hello";  を実装する。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)                アセンブリを1行出力する
    cg.array_len(ty)           'int[3]' → 3(配列でなければ None)
    cg.elem_size(ty)           要素1個のバイト数('int[3]' → 4)
    cg.const_value(式ノード)    定数式の値
    cg.local_offset(名前)       ローカル変数の s0 からのオフセット
    cg.store_insn(サイズ)       1→'sb'、4→'sw'、8→'sd'

初期化子ノードの形:
    {1, 2, 3}  → kind='InitList'、args=[Num(1), Num(2), Num(3)]
    "hello"    → kind='Str'、sval='hello'

実装する順番:
    Step 1: init_values
    Step 2: gen_local_init
    Step 3: global_init_data

確認:
    python3 check.py
    python3 golden.py
"""


def init_values(cg, ty, init_node):
    """Step 1: 初期化子から「各要素に入れる値」のリストを返す。

    例:
        {1,2,3} で int[3]   → [1, 2, 3]
        "hi"    で char[4]  → [104, 105, 0, 0]   (NUL 終端 + 0 埋め)
        {7}     で int[5]   → [7, 0, 0, 0, 0]

    方針:
    1. init_node.kind が 'Str' なら、各文字の文字コード + 終端の 0
       (ord(c) で文字コードが取れる)
    2. 'InitList' なら、args の各要素を cg.const_value() で値にする
    3. それ以外(単独の式)なら、その値1つだけのリスト
    4. 配列の長さ n = cg.array_len(ty) が分かるなら、
       足りない分を 0 で埋め、多い分は捨てて長さを n に揃える
       (C では、書かなかった要素は 0 になると決まっている)
    """
    raise NotImplementedError("Step 1: init_values を実装する")


def gen_local_init(cg, node):
    """Step 2: ローカルの配列初期化を生成する。

    node は Decl ノード(node.name, node.ty_str, node.init_expr)。

    方針:
    - init_values() で値のリストを作る
    - 要素サイズ esz = cg.elem_size(node.ty_str)
    - 配列の先頭オフセット base = cg.local_offset(node.name)
    - i 番目の値 v について、次の3行を出す
        '  li a0, {v}'
        '  addi a1, s0, {base + i * esz}'
        '  {cg.store_insn(esz)} a0, 0(a1)'

    コマ4 の「変数のアドレスは s0 + オフセット」と、
    コマ10 の「配列の i 番目は base + i * 要素サイズ」の組み合わせである。
    """
    raise NotImplementedError("Step 2: gen_local_init を実装する")


def global_init_data(cg, ty, init_node):
    """Step 3: グローバルの配列初期化を .data の行のリストとして返す。

    グローバル変数は実行前にデータとして置かれるので、命令ではなく
    アセンブラのディレクティブで値を並べる。

    方針:
    - init_values() で値のリストを作る
    - 要素サイズに応じてディレクティブを選ぶ
        1 → '.byte'、4 → '.word'、8 → '.dword'
    - 各値について f'  {directive} {v}' の行を作って返す

    例: int g[4] = {10,20,30,40} なら
        ['  .word 10', '  .word 20', '  .word 30', '  .word 40']
    """
    raise NotImplementedError("Step 3: global_init_data を実装する")
