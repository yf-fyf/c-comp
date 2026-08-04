#!/usr/bin/env python3
"""L5: 構造体の値渡し・値返し(スケルトン)

`struct Point add(struct Point a, struct Point b) { ... }` のように、
構造体を **値** で受け取り、**値** で返せるようにする。

この回で決めた呼び出し規約(この教材独自の単純化。gcc の RV64 ABI とは非互換。
理由と非互換点は資料の「呼び出し規約」節を読むこと):

  実引数(値渡し)
      呼び出し側は構造体をコピーしない。渡す式の **アドレス** を
      引数スロット 1 個に載せて渡す(`&` と同じ機構)。
      呼ばれ側だけが、入口でそのアドレスの中身を自分のフレームへ写す。
      → コピーは 1 回だけ。仮引数は入口を過ぎれば他の局所変数と全く同じ扱いになる。

  戻り値(値返し)
      呼び出し側が戻り値を受け取る領域を自分のフレームに確保し、その
      **アドレスを末尾の追加引数** として渡す(隠しポインタ = sret)。
      呼ばれ側は `return 式;` で a0 に値を積む代わりに、そのポインタの
      指す先へ構造体を写す。
      → 隠しポインタが引数を 1 個使うので、struct 値を返す関数の
        ユーザ引数は 7 個までになる。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)                アセンブリを1行出力する
    cg.codegen(式ノード)        式の値を a0 に置く
    cg.codegen_lval(式ノード)   式のアドレスを a0 に置く
    cg._push_a0() / cg._pop_into(reg)   値の退避・復元
    cg.expr_type(式ノード)      式の型(文字列)
    cg.struct_size(型)          構造体型ならバイト数、それ以外は None
    cg.current_params()         いま生成中の関数の仮引数
                                [(引数レジスタ番号, 名前, 型), ...]
    cg.current_ret_type()       いま生成中の関数の戻り値型
    cg.frame_offset(名前)       局所変数(仮引数を含む)の s0 からのオフセット
    cg.sret_param()             struct 値を返す関数なら
                                (隠しポインタの引数レジスタ番号, 置き場のオフセット)、
                                そうでなければ None
    cg.sret_slot_addr(呼び出しノード)
                                その呼び出しの戻り値受け取り領域のアドレスを a0 に置く
    cg.emit_call(関数名, 引数の個数)
                                スタックに積んだ引数を a0〜 に配って呼ぶ(完成済み)

実装する順番:
    Step 1: copy_struct           — S3 のコピーの再掲。以降すべての土台
    Step 2: gen_arg               — 呼び出し側:struct 値の実引数はアドレスを渡す
    Step 3: gen_param_prologue    — 呼ばれ側:入口でフレーム内へ複製する
    Step 4: gen_sret_call         — 呼び出し側:戻り先を確保して隠しポインタを渡す
    Step 5: gen_struct_return     — 呼ばれ側:return で隠しポインタの先へ写す

Step 1〜3 まで書けば「値渡し」が、Step 4〜5 まで書けば「値返し」が動く。

確認:
    python3 check.py
    python3 golden.py
"""


def copy_struct(cg, size):
    """Step 1: a0 が指す size バイトを a1 が指す先へ写す。

    S3 の gen_struct_copy の内側と同じロジック(あちらは両辺のアドレスを
    自分で用意していたが、ここでは呼ぶ側が a0・a1 を用意して渡す)。

    方針:
    - オフセット 0 から size バイトぶん、8 → 4 → 1 バイトの順に写す
        '  ld a2, {off}(a0)' / '  sd a2, {off}(a1)'      (8バイト)
        '  lw a2, {off}(a0)' / '  sw a2, {off}(a1)'      (4バイト)
        '  lb a2, {off}(a0)' / '  sb a2, {off}(a1)'      (1バイト)
    - 大きい単位から使うと命令数が少なくて済む
    - 作業レジスタは a2 だけを使う(a0・a1 は壊さない)
    """
    raise NotImplementedError("Step 1: copy_struct を実装する")


def gen_arg(cg, arg):
    """Step 2: 実引数を 1 個ぶん生成し、引数スロットに載せる値を a0 に置く。

    方針:
    - cg.expr_type(arg) の型が構造体(cg.struct_size(...) が None でない)なら
      **値ではなくアドレス** を渡す → cg.codegen_lval(arg)
    - それ以外はこれまでどおり cg.codegen(arg)

    なぜ codegen_lval でよいのか: この言語で構造体の値になれる式は
    変数・`*p`・`p->f` / `x.f`・関数呼び出しの結果だけで、
    どれもアドレスを持っている。だから「アドレスを取る」で困らない。
    """
    raise NotImplementedError("Step 2: gen_arg を実装する")


def gen_param_prologue(cg):
    """Step 3: 呼ばれ側の入口で、渡された struct をフレーム内へ複製する。

    関数プロローグは仮引数レジスタ a{i} を、その仮引数のフレーム内スロットへ
    そのまま書き出している。struct 値の仮引数では、そこに入っているのは
    **呼び出し側の構造体のアドレス** なので、これを読んで、同じスロットへ
    中身を写し直す(写し終えるとスロットは本物の構造体になる)。

    方針:
    1. cg.sret_param() が None でなければ、先に
       '  sd a{reg}, {off}(s0)' で隠しポインタを退避する。
       **必ず先に**。copy_struct は a0・a1・a2 を壊すので、
       あとに回すと隠しポインタが載っているレジスタを失うことがある
    2. cg.current_params() を順に見て、cg.struct_size(型) が None のものは飛ばす
    3. 構造体の仮引数は off = cg.frame_offset(名前) として
         '  ld a0, {off}(s0)'      呼び出し側が渡したアドレス
         '  addi a1, s0, {off}'    自分のフレーム内のスロット
       としてから copy_struct(cg, size) を呼ぶ
       (アドレスは先にレジスタへ読んであるので、同じスロットへ上書きしてよい)
    """
    raise NotImplementedError("Step 3: gen_param_prologue を実装する")


def gen_sret_call(cg, node):
    """Step 4: struct 値を返す関数を呼ぶ(呼び出し側)。

    戻り値を受け取る一時領域は、ラッパーがこの呼び出し 1 箇所につき 1 個、
    呼び出し側のフレーム内に確保済み。cg.sret_slot_addr(node) でそのアドレスが
    a0 に載る。再帰しても各呼び出しは自分のフレームの領域を指すので混ざらない。

    方針:
    1. node.args を順に gen_arg(cg, arg) → cg._push_a0() で積む
    2. 続けて cg.sret_slot_addr(node) → cg._push_a0() で隠しポインタを **末尾** に積む
    3. cg.emit_call(node.name, len(node.args) + 1) で呼ぶ
    4. 呼び出しから戻ると a0 は壊れている。この呼び出し式の値は
       「戻り先のアドレス」なので、cg.sret_slot_addr(node) をもう一度呼んで
       a0 に載せ直す
    """
    raise NotImplementedError("Step 4: gen_sret_call を実装する")


def gen_struct_return(cg, node):
    """Step 5: struct 値の `return 式;`(呼ばれ側)。

    node は Return 文のノードで、node.operand が返す式。
    a0 に値を積むのではなく、Step 3 で退避した隠しポインタの指す先へ写す。
    (このあとの `j` で関数の出口へ飛ぶ処理はラッパーがやる)

    方針:
    1. size = cg.struct_size(cg.current_ret_type())
    2. cg.codegen(node.operand) → a0 = 返す構造体のアドレス
       (構造体の式は値ではなくアドレスが a0 に載る)
    3. cg.sret_param() の offset から '  ld a1, {off}(s0)' で隠しポインタを読む
       ※ 2 の式が関数呼び出しかもしれないので、**読むのは 2 のあと**
    4. copy_struct(cg, size)
    5. '  mv a0, a1' として、戻り値としてもアドレスを残しておく
    """
    raise NotImplementedError("Step 5: gen_struct_return を実装する")
