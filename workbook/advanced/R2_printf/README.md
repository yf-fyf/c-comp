# R2: 自前 printf — 数を文字に変える

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/R2_printf/](https://yf-fyf.github.io/c-comp/advanced/R2_printf/) にあります。

## 今日のゴール

libc を使わずに `print_str` / `print_int` / `printf1` を自分で書き、
自作コンパイラでコンパイルして動かす。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | R1（`sys_write` が使える状態） |
| 推奨の前提 | コマ16（実質必須に近い。`check.py` が `final/mycc.py` で `tests/*.c` をコンパイルするので、無いと実行できない） |
| 改変しない | `mycc.py`、`scaffold/`、`syscall.s`（R1 のもの。配布済み・完成品） |
| 編集する | `myprintf.c` |
| 完了条件 | `check.py` の全 Step が PASS になる（このトピックに `golden.py` は無い） |
| コマ数 | 1 |
| 備考 | ランタイム発展シリーズの第2回。書くのはすべて Core プロファイルの C で、自分のコンパイラでコンパイルする |

## 編集するファイル

- `myprintf.c`（Step 1: 文字列の基本、Step 2: 10進変換、Step 3: 書式）

`syscall.s` は R1 のもの（完成品）です。

## テスト

```bash
python3 check.py
```

`tests/*.c` を自作コンパイラでコンパイルし、`myprintf.c`・`syscall.s` と
`-nostdlib` でリンクして実行します。
