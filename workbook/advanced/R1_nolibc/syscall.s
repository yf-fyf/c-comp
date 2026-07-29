# R1: C から呼べるシステムコール窓口(教員用参照実装)
#
# mycc がコンパイルした C コードとリンクして使う。
#   int sys_write(int fd, char *buf, int len);
#   void sys_exit(int code);
# さらに、libc なしで動かすための _start(main を呼んで exit する)も置く。

    .text
    .globl sys_write
sys_write:
    li   a7, 64         # write
    ecall
    ret                 # 戻り値(書けたバイト数)は a0 に入っている

    .globl sys_exit
sys_exit:
    li   a7, 93         # exit
    ecall

    .globl _start
_start:
    call main           # main の戻り値が a0 に入る
    li   a7, 93         # exit(main の戻り値)
    ecall
