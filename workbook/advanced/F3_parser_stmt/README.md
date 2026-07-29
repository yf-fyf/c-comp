# F3: 再帰下降パーサ② — 文を解析する

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

F2 の式パーサを継承して、文（return / break / continue / if / while / for /
ブロック / 式文）の解析を追加する。
37本の文コーパスで AST が scaffold の Parser と完全一致すれば完了。

前提は F2（`StmtParser` は自分の F2 `ExprParser` を importlib で継承する）。
宣言と関数定義は F4 で扱う。

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
