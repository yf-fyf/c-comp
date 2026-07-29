# F2: 再帰下降パーサ① — 式を解析する

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F2_parser_expr/](https://yf-fyf.github.io/c-comp/advanced/F2_parser_expr/) にあります。

## 今日のゴール

EBNF の式の階層をそのまま関数の階層に写して、Core プロファイルの式パーサを自作する。
86本の式コーパスで AST が scaffold の Parser と完全一致すれば完了。

前提は F1。`Node` と定数は scaffold の `ast_def.py` から借りる
（AST の形は決まっている。作るのは「組み立てる側」）。
`sizeof` は F4 で扱う。

## 編集するファイル

- `myparser.py`（Step 1〜5 を上から順に。各レベルは最初「素通し」になっている）

## 動かし方

```bash
python3 myparser.py '1 + 2 * 3'    # parse_viewer と同じ S 式で表示
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(期待値は S 式)
python3 golden.py    # 86本の式コーパスで scaffold と突き合わせ
```

`golden.py` の全式 PASS がこの回の完了条件です。
