# @title 【不具合例】ra を退避していない
# @desc 「関数から戻ると壊れる」の典型
#
# call は戻り番地を ra に書き込む。だから関数の中でさらに call するなら、
# 自分の ra を先にスタックへ退避しておかなければならない。
# ここでは main が ra を退避せずに f を呼んでいる。
# f から戻ったあと main の ret は「call f の次」へ戻ってしまい、
# 同じところを回り続ける。
#
# 「すすむ」を何度か押すと、同じ行を往復しているのが見える。
# 直し方: プロローグで sd ra, N(sp)、エピローグで ld ra, N(sp)。

  .text
  .globl f
f:
  li a0, 1
  ret

  .globl main
main:
  addi sp, sp, -16
                          # ← ここに sd ra, 8(sp) が要る
  call f
  addi sp, sp, 16
  ret
