# B3: 末尾呼び出し最適化 — 再帰をループに変える

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/B3_tailcall/](https://yf-fyf.github.io/c-comp/advanced/B3_tailcall/) にあります。

## 今日のゴール

`return f(...);` の形の自己再帰をジャンプに変換し、
100万回の末尾再帰でもスタックがあふれないようにする。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | 着手はコマ8（関数呼び出し）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ16 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `tccc.py`（配布済み・完成品） |
| 編集する | `tailcall.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が深い末尾再帰の通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 備考 | 最適化入門発展シリーズの第3回。B1・B2 とは独立している。O 系列に対応する回は無い |

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
python3 golden.py    # 深い末尾再帰が通る + fixed17 が壊れない
```

土台のコンパイラを差し替えたいときは環境変数 `TCCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
