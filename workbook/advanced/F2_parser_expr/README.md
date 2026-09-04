# F2: 再帰下降パーサ① — 式を解析する

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F2_parser_expr/](https://yf-fyf.github.io/c-comp/advanced/F2_parser_expr/) にあります。

## 今日のゴール

EBNF の式の階層をそのまま関数の階層に写して、Core プロファイルの式パーサを自作します。
85本の式コーパスで AST が スキャフォールド の Parser と完全一致すれば完了です。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | F1 |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（`Node` と `ND_*` 定数は `ast_def.py` から借りる） |
| 編集する | `myparser.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が85本の式コーパスで AST の完全一致を報告する |
| コマ数 | 1 |
| 備考 | フロントエンド発展シリーズの第2回。`sizeof` は型のパースが要るので F4 で扱う |

`Node` と定数は スキャフォールド の `ast_def.py` から借ります
（AST の形は決まっている。作るのは「組み立てる側」）。

## 編集するファイル

- `myparser.py`（Step 1〜6 を上から順に。各レベルは最初「素通し」になっている）

## 動かし方

```bash
python3 myparser.py '1 + 2 * 3'    # parse_viewer と同じ S 式で表示
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(期待値は S 式)
python3 golden.py    # 85本の式コーパスで scaffold と突き合わせ
```

`golden.py` の全式 PASS がこの回の完了条件です。
