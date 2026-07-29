# @title 配列の添字とアドレス計算
# @desc a[i] が「先頭 + i * 要素サイズ」になること
#
# int a[4]; a[0..3] = 10,20,30,40; return a[2] + a[3];
# int は 4 バイトなので、a[i] のアドレスは a + i*4 になる。
# この *4 を忘れると隣の要素や別の変数を読んでしまう（「配列の添字がずれる」）。
#
# スタック表で、a[0]〜a[3] が 4 バイトずつ並んでいるのを確かめる。

  .text
  .globl main
main:
  addi sp, sp, -32
  sd ra, 24(sp)
  sd s0, 16(sp)
  addi s0, sp, 32

  addi a1, s0, -32        # a の先頭アドレス（int 4 個 = 16 バイト）

  li a0, 10
  sw a0, 0(a1)            # a[0] = 10   ← 先頭 + 0*4
  li a0, 20
  sw a0, 4(a1)            # a[1] = 20   ← 先頭 + 1*4
  li a0, 30
  sw a0, 8(a1)            # a[2] = 30   ← 先頭 + 2*4
  li a0, 40
  sw a0, 12(a1)           # a[3] = 40   ← 先頭 + 3*4

  lw a0, 8(a1)            # a[2]
  lw a2, 12(a1)           # a[3]
  add a0, a0, a2          # 30 + 40 = 70

  ld s0, 16(sp)
  ld ra, 24(sp)
  addi sp, sp, 32
  ret
