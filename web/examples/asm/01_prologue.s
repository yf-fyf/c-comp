# @title プロローグとエピローグ
# @desc 関数の出入りでスタックがどう動くか
#
# int main() { int a; int b; a = 3; b = 4; return a + b; }
# ローカル変数 2 つ分（16 バイト）を確保して、使い終わったら元に戻す。
# 「すすむ」を押しながら、右の sp と s0 の位置がスタック表のどこを指すか見る。

  .text
  .globl main
main:
  addi sp, sp, -32        # フレームを確保（16 の倍数にする）
  sd ra, 24(sp)           # 戻り番地を退避
  sd s0, 16(sp)           # 呼び出し元のフレームポインタを退避
  addi s0, sp, 32         # s0 = このフレームの上端

  li a0, 3
  sd a0, -24(s0)          # a = 3
  li a0, 4
  sd a0, -32(s0)          # b = 4

  ld a0, -24(s0)          # a を読む
  ld a1, -32(s0)          # b を読む
  add a0, a0, a1          # a + b

  ld s0, 16(sp)           # 退避したものを逆順に戻す
  ld ra, 24(sp)
  addi sp, sp, 32         # フレームを解放
  ret
