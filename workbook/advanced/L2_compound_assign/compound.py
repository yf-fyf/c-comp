#!/usr/bin/env python3
"""L2: 複合代入(スケルトン)

x += 3;  p -= 1;  x %= 5;  を実装する。

標準トラックの字句には '+=' などのトークンが無いので、字句の拡張から始める。
構文(CompoundAssign ノードを作るところ)は langcc.py が済ませてある。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)                 アセンブリを1行出力する
    cg.codegen(式ノード)         式の値を a0 に作る
    cg.codegen_lval(左辺ノード)   左辺値の「アドレス」を a0 に作る
    cg.push_a0()                a0 をスタックに積む
    cg.pop_into(レジスタ)        スタックの一番上を取り出す
    cg.load_ty(型)              a0 のアドレスから値を読んで a0 に入れる
    cg.store_ty(型)             a1 のアドレスへ a0 の値を書く
    cg.lval_type(左辺ノード)      左辺の型文字列('int'、'char'、'int*' など)
    cg.ptr_elem_size(型)        ポインタなら要素1個のバイト数、でなければ 0

複合代入ノードの形:
    x += 3   → kind='CompoundAssign'、sval='+='、lhs=Var(x)、rhs=Num(3)

実装する順番:
    Step 1: extend_puncts
    Step 2: gen_compound_assign
    Step 3: scale_rhs_for_ptr

確認:
    python3 check.py
    python3 golden.py
"""

# 演算子 → RISC-V の命令名
OP_INSN = {'+=': 'add', '-=': 'sub', '*=': 'mul', '/=': 'div', '%=': 'rem'}


def extend_puncts(puncts):
    """Step 1: 2文字演算子の表に複合代入を加えたリストを返す。

    puncts は scaffold の lexer.TWO_CHAR_PUNCTS の複製
    (['==', '!=', '<=', '>=', '&&', '||', '->', '++', '--'])。

    方針:
    - '+=' '-=' '*=' '/=' '%=' を追加した新しいリストを返す
    - 2文字演算子どうしに「片方がもう片方の先頭」という関係は無いので、
      並べる順番は気にしなくてよい('++' と '+=' は2文字目で分かれる)
    - 1文字演算子より先に2文字を試すのは lexer 側の仕事なので、
      ここではリストを返すだけでよい
    """
    raise NotImplementedError("Step 1: extend_puncts を実装する")


def gen_compound_assign(cg, node):
    """Step 2: 複合代入のコードを生成する。

    node は CompoundAssign(node.sval が演算子、node.lhs / node.rhs)。

    要点は「左辺のアドレスを1度だけ計算する」こと。
    x = x + e に書き換えてしまうと、*f() += 1 で f() が2回呼ばれてしまい、
    仕様の「複合代入の左辺は1回だけ評価される」に違反する。

    方針(a0 を作業レジスタにする):
        ty = cg.lval_type(node.lhs)
        cg.codegen_lval(node.lhs)   # a0 = 左辺のアドレス
        cg.push_a0()                # アドレスを退避
        cg.load_ty(ty)              # a0 = いまの値
        cg.push_a0()                # いまの値も退避
        cg.codegen(node.rhs)        # a0 = 右辺の値
        scale_rhs_for_ptr(cg, ty)   # Step 3(ポインタなら要素サイズ倍)
        cg.pop_into('a1')           # a1 = いまの値
        cg.emit(f'  {OP_INSN[node.sval]} a0, a1, a0')
        cg.pop_into('a1')           # a1 = 左辺のアドレス
        cg.store_ty(ty)             # 書き戻す。a0 には結果が残る

    a0 に結果が残るので、y = (x += 1) のように式としても使える。
    '%=' や '/=' の右辺が 0 のときは未定義動作(仕様「未定義動作」)。
    ここで特別扱いはしない。

    Step 2 の間は scale_rhs_for_ptr の呼び出しを省いて int だけ動かし、
    Step 3 で足してもよい。
    """
    raise NotImplementedError("Step 2: gen_compound_assign を実装する")


def scale_rhs_for_ptr(cg, ty):
    """Step 3: 左辺がポインタなら、a0 の右辺値を要素サイズ倍する。

    p += 2 は「2要素ぶん進める」であって「2バイト進める」ではない。
    コマ10 の p + 2 と同じスケーリングを、複合代入でも行う。

    方針:
        sz = cg.ptr_elem_size(ty)      # ポインタでなければ 0
        sz が 2 以上なら
            cg.emit(f'  li a1, {sz}')
            cg.emit('  mul a0, a0, a1')
      (このとき a1 は空いている。いまの値はスタックに積んである)

    ポインタに使えるのは '+=' と '-=' だけである(仕様「ポインタ演算」)。
    """
    raise NotImplementedError("Step 3: scale_rhs_for_ptr を実装する")
