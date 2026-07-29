# B1: 最適化入門 — 定数畳み込みとピープホール

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

2つの最適化パスを追加して生成命令数を減らし、`fixed15` が全通し続けることで
「意味を変えずに速くできた」ことを確認する。

前提はコマ8 まで（効果の測定には コマ16 の `final/mycc.py` を使う）。
**`mycc.py` は書き換えません。**

## 編集するファイル

- `fold.py`（Step 1: 定数畳み込みの演算部分）
- `peephole.py`（Step 2〜3: 3つの置換規則）

## 動かし方

```bash
python3 foldcc.py ../../final/tests/f05_for.c              # 最適化あり
python3 foldcc.py --no-fold ../../final/tests/f05_for.c    # 畳み込みなし
python3 foldcc.py ../../final/tests/f05_for.c | python3 ../count_insns.py
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # fixed15 全通 + 命令数の before/after
```

`golden.py` が全テスト PASS かつ命令数削減を報告したら完了です。
