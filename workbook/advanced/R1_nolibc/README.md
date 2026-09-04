# R1: libc なしで動かす — システムコールを直接呼ぶ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/R1_nolibc/](https://yf-fyf.github.io/c-comp/advanced/R1_nolibc/) にあります。

## 今日のゴール

システムコールを直接発行して、libc なしで文字を表示し終了コードを返します。
さらに自作コンパイラの出力を libc なしで実行します。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | 着手はコマ10（`printf`）まで。完了条件の `check.py` は Step 2 で完成した `final/mycc.py` の出力をリンクする（無い間はそこが SKIP になる）ので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
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

未実装のうちは SKIP になります。この回の編集対象はアセンブリなので、
未実装は `hello.s` の `TODO(...)` コメントで表してあります。
`check.py` は TODO が残っている間その Step を `[SKIP] 未実装: …` と報告し、
実装したところから PASS / FAIL に変わります（SKIP は未達なので、完了条件は満たしていません）。

`check.py` が Step 2 で使う土台のコンパイラは、環境変数 `R1_COMPILER` で差し替えられます
（R 系列はラッパーが無いので、回 ID を接頭辞にする例外規則。詳しくは
[`../README.md`](../README.md) の「環境変数の名前」を参照）。
