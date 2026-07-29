# @title 【不具合例】sp が 16 の倍数でないまま call
# @desc Illegal instruction / Bus error の原因
#
# RV64 の呼び出し規約は、call の時点で sp が 16 バイト境界にあることを要求する。
# ここでは 8 バイトだけ引いてから call しているので条件を満たさない。
# 実機や qemu では Illegal instruction や Bus error になる。
# シミュレータは止めずに「気づいたこと」へ警告を出す。
#
# 直し方: 確保する量を align_to(n, 16) で 16 の倍数に切り上げる。

  .text
  .globl f
f:
  li a0, 42
  ret

  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)

  addi sp, sp, -8         # ← 8 しか引いていない。ここが原因
  call f                  # この時点で sp % 16 == 8
  addi sp, sp, 8

  ld ra, 8(sp)
  addi sp, sp, 16
  ret
