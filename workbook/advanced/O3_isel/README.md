# O3: 命令選択 — 複数の命令を1つに畳む

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O3_isel/](https://yf-fyf.github.io/c-comp/advanced/O3_isel/) にあります。

## 今日のゴール

「アドレス計算 + ロード」を、RV64 の `offset(base)` 形式のロード1命令に畳む。
`fixed17` を通したまま、静的・動的の両方で命令数を減らす。

前提は O1（測定基盤）。**`mycc.py` は書き換えません**。

## 編集するファイル

- `isel.py`（Step 1: fold_load、Step 2: is_dead_after、
  Step 3: fold_store / fold_mul_to_shift、Step 4: run）

## 動かし方

```bash
python3 ../optcc.py --passes isel ../O1_measure/bench/matmul.c
python3 ../optcc.py --passes '' ../O1_measure/bench/matmul.c   # 最適化なし
```

## テスト

```bash
python3 check.py     # 各置き換えの単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 + ベンチマーク + 静的/動的の削減
```
