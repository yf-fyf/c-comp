# R1: libc なしで動かす — システムコールを直接呼ぶ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/R1_nolibc/](https://yf-fyf.github.io/c-comp/advanced/R1_nolibc/) にあります。

## 今日のゴール

システムコールを直接発行して、libc なしで文字を表示し終了コードを返す。
さらに自作コンパイラの出力を libc なしで実行する。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ11（`printf`）まで |
| 推奨の前提 | コマ16（`check.py` の Step 2 は `final/mycc.py` の出力をリンクするので、無いとそこが SKIP になる） |
| 改変しない | `mycc.py`、`scaffold/`、`syscall.s`（配布済み・完成品） |
| 編集する | `hello.s` |
| 完了条件 | `check.py` の全 Step が PASS になる（このトピックに `golden.py` は無い） |
| コマ数 | 1 |
| 備考 | ランタイム発展シリーズの第1回。続く R2・R3 の土台になる |

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
