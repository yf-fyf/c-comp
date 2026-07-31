# B1: 最適化入門 — 定数畳み込みとピープホール

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/B1_fold_peephole/](https://yf-fyf.github.io/c-comp/advanced/B1_fold_peephole/) にあります。

## 今日のゴール

2つの最適化パスを追加して生成命令数を減らし、`fixed17` が全通し続けることで
「意味を変えずに速くできた」ことを確認する。

前提はコマ8 まで（効果の測定には コマ16 の `final/mycc.py` を使う）。
**`mycc.py` は書き換えません。**

## 編集するファイル

- `fold.py`（Step 1: 定数畳み込みの演算部分）
- `peephole.py`（Step 2〜3: 3つの置換規則）

Step 3 の `remove_jump_to_next` は、**O7 の Step 3 と同名・同一の最適化**です。
片方を書いたら、もう片方へそのまま持ち込めます。
なお `count_insns.py` が数えるのは静的命令数（出力の命令の個数）で、
「実行された命令が何回減ったか」は別物です。それを測る物差しは O1 が作ります。

## 動かし方

```bash
python3 foldcc.py ../../final/tests/f05_for.c              # 最適化あり
python3 foldcc.py --no-fold ../../final/tests/f05_for.c    # 畳み込みなし
python3 foldcc.py ../../final/tests/f05_for.c | python3 ../count_insns.py
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 全通 + 命令数の before/after
```

`golden.py` が全テスト PASS かつ命令数削減を報告したら完了です。
