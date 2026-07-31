# B2: レジスタ割り当て入門 — スタックマシンを卒業する

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/B2_regalloc/](https://yf-fyf.github.io/c-comp/advanced/B2_regalloc/) にあります。

## 今日のゴール

式の途中結果の退避先をメモリから t レジスタに変え、
`fixed17` を全通させたまま命令数を減らす。

前提はコマ8 まで。**`mycc.py` は書き換えません**（`regcc.py` が差し替えます）。

## 編集するファイル

- `regstack.py`（Step 1: push_a0 / pop_into、Step 2: spill / reload）

この回がレジスタに載せるのは**式の途中結果**（`t0`〜`t6`）です。
**局所変数**を `s1`〜`s11` に載せるのは O4 で、別の無駄を消しています
（この回の発展課題3 が、そのまま O4 の主題です）。

## 動かし方

```bash
python3 regcc.py ../../final/tests/f09_recur.c
python3 regcc.py ../../final/tests/f09_recur.c | python3 ../count_insns.py
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 全通 + 命令数の before/after
```
