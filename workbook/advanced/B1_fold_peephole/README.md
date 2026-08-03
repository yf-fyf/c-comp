# B1: 最適化入門 — 定数畳み込みとピープホール

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/B1_fold_peephole/](https://yf-fyf.github.io/c-comp/advanced/B1_fold_peephole/) にあります。

## 今日のゴール

2つの最適化パスを追加して生成命令数を減らし、`fixed17` が全通し続けることで
「意味を変えずに速くできた」ことを確認する。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | 着手はコマ6（関数呼び出し）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `foldcc.py`（配布済み・完成品） |
| 編集する | `fold.py`、`peephole.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `fixed17` 全通と命令数の削減を報告する |
| コマ数 | 1 |
| 備考 | 最適化入門発展シリーズの第1回。O 系列（O1〜O7）の前哨で、測定基盤を作らずに始められるよう軽装にしてある |

## 編集するファイル

- `fold.py`（Step 1: `fold_binary` / `fold_unary`）
- `peephole.py`（Step 2: `fuse_push_const_pop`、Step 3: `remove_jump_to_next` / `remove_branch_to_next`）

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

土台のコンパイラを差し替えたいときは環境変数 `FOLDCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
