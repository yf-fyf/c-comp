# R1: libc なしの Hello World(スケルトン)
#
# 目標: この1ファイルだけで、文字列を表示して終了コード 42 を返す。
# libc は使わない。printf も exit も使わず、システムコールを直接発行する。
#
#   riscv64-linux-gnu-gcc -nostdlib -static hello.s -o hello
#   qemu-riscv64 ./hello; echo $?     → Hello, no libc! と表示され 42
#
# 使うシステムコール(Linux RV64):
#   write(fd, buf, count)   a0=fd, a1=buf, a2=count, a7=64
#   exit(code)              a0=code,                 a7=93
# 引数を a0.. に、番号を a7 に入れて ecall する。

    .data
msg:
    .ascii "Hello, no libc!\n"
    .set msglen, 16          # msg のバイト数(改行を含む)

    .text
    .globl _start
_start:
    # TODO(Step 1): write(1, msg, msglen) を発行する
    #   a0 に 1、a1 に msg のアドレス(la を使う)、a2 に msglen、
    #   a7 に 64 を入れて ecall

    # TODO(Step 2): exit(42) を発行する
    #   a0 に 42、a7 に 93 を入れて ecall
    #   (ret ではない。戻る先がないのでプログラムはここで終わる)
