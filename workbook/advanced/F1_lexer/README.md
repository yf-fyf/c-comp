# F1: 字句解析器を作る — 黒箱を開ける（前編）

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

`scaffold/lexer.py` を読んで構造を理解し、同じ仕様の字句解析器を自作する。
全テスト入力（約100本の `.c`）でトークン列が scaffold と完全一致すれば完了。

前提は F0。編集するのは `mylexer.py` だけ（scaffold 本体は変更しない）。

## 編集するファイル

- `mylexer.py`（Step 1〜4 の TODO メソッドを上から順に実装する）

## 動かし方

```bash
python3 mylexer.py ../../sessions/03_arithmetic_codegen/tests/add.c
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 全テスト入力で scaffold と突き合わせ
```

`golden.py` の全ファイル PASS がこの回の完了条件です。
