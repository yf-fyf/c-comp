# B2: レジスタ割り当て入門 — スタックマシンを卒業する

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/B2_regalloc/](https://yf-fyf.github.io/c-comp/advanced/B2_regalloc/) にあります。

## 今日のゴール

式の途中結果の退避先をメモリから t レジスタに変え、
`fixed17` を全通させたまま命令数を減らす。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | 着手はコマ8（関数呼び出し）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ16 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `regcc.py`（配布済み・完成品） |
| 編集する | `regstack.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `fixed17` 全通と命令数の削減を報告する |
| コマ数 | 1 |
| 備考 | 最適化入門発展シリーズの第2回。B1 とは独立している。O4（レジスタ割り当て）の前哨にあたる |

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
