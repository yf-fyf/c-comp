#!/usr/bin/env python3
"""S1: 短絡評価(スケルトン)

&& と || を、両辺を評価する形から「必要なときだけ右辺を評価する」形に変える。

引数の cg はコード生成器のインスタンスで、次を使う。
    cg.emit(行)          アセンブリを1行出力する
    cg.codegen(式ノード)  式を評価して結果を a0 に置く
    cg.new_label()       一意なラベル名(.L1 など)を返す

node.lhs が左辺、node.rhs が右辺。

実装する順番:
    Step 1: gen_and
    Step 2: gen_or

確認:
    python3 check.py
    python3 golden.py
"""


def gen_and(cg, node):
    """Step 1: lhs && rhs

    生成したい流れ:

        lhs を評価         → a0
        a0 が 0 なら Lfalse へ    ← ここで右辺を飛ばすのが短絡
        rhs を評価         → a0
        a0 が 0 なら Lfalse へ
        li a0, 1
        j Lend
      Lfalse:
        li a0, 0
      Lend:

    使う命令: beqz(0 なら飛ぶ)、j(無条件に飛ぶ)、li
    ラベルは cg.new_label() で2つ作る。
    """
    raise NotImplementedError("Step 1: gen_and を実装する")


def gen_or(cg, node):
    """Step 2: lhs || rhs

    && の裏返し。左辺が 0 以外なら、右辺を見ずに 1 で終わる。

        lhs を評価         → a0
        a0 が 0 以外なら Ltrue へ   ← 短絡
        rhs を評価         → a0
        a0 が 0 以外なら Ltrue へ
        li a0, 0
        j Lend
      Ltrue:
        li a0, 1
      Lend:

    使う命令: bnez(0 以外なら飛ぶ)、j、li
    """
    raise NotImplementedError("Step 2: gen_or を実装する")
