# @title 再帰とスタックの伸縮
# @desc 呼び出しのたびにフレームが積まれる様子
#
# int fact(int n) { if (n < 2) return 1; return n * fact(n - 1); }
# fact(5) = 120。
# 「すすむ」で追うと、call のたびに sp が下がってフレームが増え、
# ret のたびに戻っていくのが見える。
# 引数 n は自分のフレームへ退避してから再帰している。これをやめると
# 戻ってきたときに n が壊れる（a0-a7 は呼び出し先が壊してよいレジスタ）。

  .text
  .globl fact
fact:
  addi sp, sp, -32
  sd ra, 24(sp)
  sd s0, 16(sp)
  addi s0, sp, 32

  li a1, 2
  slt a1, a0, a1          # n < 2 か
  beqz a1, .Lrec
  li a0, 1                # 基底: 1 を返す
  j .Lend

.Lrec:
  sd a0, -24(s0)          # n を自分のフレームへ退避
  addi a0, a0, -1
  call fact               # fact(n - 1)
  ld a1, -24(s0)          # 退避した n を読み戻す
  mul a0, a0, a1          # n * fact(n-1)

.Lend:
  ld s0, 16(sp)
  ld ra, 24(sp)
  addi sp, sp, 32
  ret

  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
  li a0, 5
  call fact
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
