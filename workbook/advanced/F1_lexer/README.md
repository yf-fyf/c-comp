# F1: 字句解析器を作る — ブラックボックスを開ける（前編）

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F1_lexer/](https://yf-fyf.github.io/c-comp/advanced/F1_lexer/) にあります。

## 今日のゴール

`scaffold/lexer.py` を読んで構造を理解し、同じ仕様の字句解析器を自作する。
全テスト入力（約100本の `.c`）でトークン列が スキャフォールド と完全一致すれば完了。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | F0 |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（`scaffold/lexer.py` は読解の対象であって、書き換えない） |
| 編集する | `mylexer.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が全テスト入力（約100本の `.c`）でスキャフォールドとのトークン列の完全一致を報告する |
| コマ数 | 1 |
| 備考 | フロントエンド発展シリーズの第1回。F0 の `tokenize` を Core プロファイルの C の字句仕様へ拡張する |

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
