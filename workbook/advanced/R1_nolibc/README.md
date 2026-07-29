# R1: libc なしで動かす — システムコールを直接呼ぶ

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

システムコールを直接発行して、libc なしで文字を表示し終了コードを返す。
さらに自作コンパイラの出力を libc なしで実行する。

前提はコマ11 まで。

## 編集するファイル

- `hello.s`（Step 1: write と exit の ecall）

`syscall.s`（C から呼べる `sys_write` / `sys_exit` と `_start`）は完成品です。

## 動かし方

```bash
riscv64-linux-gnu-gcc -nostdlib -static hello.s -o hello
qemu-riscv64 ./hello; echo $?      # → Hello, no libc! / 42
```

## テスト

```bash
python3 check.py
```
