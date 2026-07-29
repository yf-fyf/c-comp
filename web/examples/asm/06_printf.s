# @title 文字列と printf
# @desc .data に置いた文字列を printf に渡す
#
# printf("%d and %s\n", 42, "hi");
# 文字列リテラルは .data に .byte の並びとして置かれ、la でアドレスを取る。
# 引数は a0 から順に渡す（a0 = 書式文字列、a1 以降が可変長引数）。
#
# 右の「データ領域」に文字列が見える。実行すると標準出力へ出る。

  .data
.LC0:                     # "%d and %s\n"
  .byte 37
  .byte 100
  .byte 32
  .byte 97
  .byte 110
  .byte 100
  .byte 32
  .byte 37
  .byte 115
  .byte 10
  .byte 0
.LC1:                     # "hi"
  .byte 104
  .byte 105
  .byte 0

  .text
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)

  la a0, .LC0             # 書式文字列
  li a1, 42               # %d に対応
  la a2, .LC1             # %s に対応
  call printf

  li a0, 0                # main は 0 を返す
  ld ra, 8(sp)
  addi sp, sp, 16
  ret
