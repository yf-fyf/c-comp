# F3: 再帰下降パーサ② — 文を解析する

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F3_parser_stmt/](https://yf-fyf.github.io/c-comp/advanced/F3_parser_stmt/) にあります。

## 今日のゴール

F2 の式パーサを継承して、文（return / break / continue / if / while / for /
ブロック / 式文）の解析を追加する。
37本の文コーパスで AST が スキャフォールド の Parser と完全一致すれば完了。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | F2 |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/` |
| 編集する | `myparser.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が37本の文コーパスで AST の完全一致を報告する |
| コマ数 | 1 |
| 備考 | フロントエンド発展シリーズの第3回。F2 が未完成だとこの回のテストは動かない。宣言（`int x;` など）と関数定義は F4 で扱う |

`StmtParser` は、自分が F2 で作った `ExprParser` を importlib で継承します。

## 編集するファイル

- `myparser.py`（Step 1〜4。ディスパッチ `parse_stmt` は完成済み）

## 動かし方

```bash
python3 myparser.py 'if (a > b) return a; else return b;'
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 37本の文コーパスで scaffold と突き合わせ
```

`golden.py` の全文 PASS がこの回の完了条件です。
