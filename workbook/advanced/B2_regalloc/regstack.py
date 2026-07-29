#!/usr/bin/env python3
"""B2: レジスタスタック(スケルトン)

式の途中結果の退避先を、メモリ(スタック)から t レジスタに変える。

引数の cg はコード生成器のインスタンスで、次の2つを使う。
    cg.emit(行)   アセンブリを1行出力する
    cg.depth      いま何段退避しているか(0 なら何も退避していない)

実装する順番:
    Step 1: push_a0 / pop_into
    Step 2: spill_before_call / reload_after_call

確認:
    python3 check.py
    python3 golden.py
"""

# 退避に使うレジスタ(RV64 の一時レジスタ)
REGS = ['t0', 't1', 't2', 't3', 't4', 't5', 't6']


def push_a0(cg):
    """Step 1: a0 の値を退避する。深さ cg.depth の場所へ。

    方針:
    - cg.depth が REGS の個数より小さければ、対応するレジスタへ mv する
      例: depth が 0 なら '  mv t0, a0'
    - レジスタが尽きていたら、これまで通りメモリへ退避する。
      ただし sp の 16 バイト境界を保つため、8 ではなく 16 バイト単位で確保する
        '  addi sp, sp, -16' / '  sd a0, 0(sp)'
    - 最後に cg.depth を 1 増やす
    """
    raise NotImplementedError("Step 1: push_a0 を実装する")


def pop_into(cg, reg):
    """Step 1: 最後に退避した値を reg に戻す。

    方針: push_a0 の逆をたどる。
    - まず cg.depth を 1 減らす(減らした後の値が「取り出す場所」)
    - それが REGS の範囲内なら '  mv {reg}, {REGS[cg.depth]}'
    - 範囲外ならメモリから戻す
        '  ld {reg}, 0(sp)' / '  addi sp, sp, 16'
    """
    raise NotImplementedError("Step 1: pop_into を実装する")


def live_regs(cg):
    """いま値が入っている t レジスタの一覧(完成済み)。"""
    return REGS[:min(cg.depth, len(REGS))]


def spill_before_call(cg):
    """Step 2: call の直前に、生きている t レジスタをメモリへ退避する。

    t0〜t6 は caller-saved(呼び出し側が守る)なので、
    呼ばれた関数に壊されてもよい約束になっている。
    呼び出しをまたいで値を保つには、呼び出す側が自分で退避するしかない。

    方針:
    - live_regs(cg) が空なら何もしない
    - 必要なバイト数を求める。1本 8 バイトだが、call の時点で sp を
      16 バイト境界に保つ必要があるので、16 の倍数に切り上げる
      例: 3 本なら 32 バイト
    - sp を下げてから、各レジスタを '  sd {r}, {i*8}(sp)' で保存する
    """
    raise NotImplementedError("Step 2: spill_before_call を実装する")


def reload_after_call(cg):
    """Step 2: call の直後に、退避した t レジスタを復元する。

    spill_before_call と同じ順序・同じサイズで ld してから sp を戻す。
    """
    raise NotImplementedError("Step 2: reload_after_call を実装する")
