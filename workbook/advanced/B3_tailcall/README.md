# B3: 末尾呼び出し最適化 — 再帰をループに変える

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/B3_tailcall/](https://yf-fyf.github.io/c-comp/advanced/B3_tailcall/) にあります。

## 今日のゴール

`return f(...);` の形の自己再帰をジャンプに変換し、
100万回の末尾再帰でもスタックがあふれないようにする。

前提はコマ8 まで。**`mycc.py` は書き換えません**（`tccc.py` が差し替えます）。

## 編集するファイル

- `tailcall.py`（Step 1: is_self_tail_call、Step 2: gen_tail_call）

## 動かし方

```bash
python3 tccc.py tests/deep_sum.c
python3 tccc.py tests/deep_sum.c | grep -c call    # call が減る
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 深い末尾再帰が通る + fixed15 が壊れない
```
