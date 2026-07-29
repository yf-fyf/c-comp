# R2: 自前 printf — 数を文字に変える

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/R2_printf/](https://yf-fyf.github.io/c-comp/advanced/R2_printf/) にあります。

## 今日のゴール

libc を使わずに `print_str` / `print_int` / `printf1` を自分で書き、
自作コンパイラでコンパイルして動かす。

前提は R1（`sys_write` が使える状態）。

## 編集するファイル

- `myprintf.c`（Step 1: 文字列の基本、Step 2: 10進変換、Step 3: 書式）

`syscall.s` は R1 のもの（完成品）です。

## テスト

```bash
python3 check.py
```

`tests/*.c` を自作コンパイラでコンパイルし、`myprintf.c`・`syscall.s` と
`-nostdlib` でリンクして実行します。
