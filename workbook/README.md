# 学習者向けガイド

この教材では、Python で C 言語サブセットの簡易コンパイラを作る。
標準トラックの最終成果物は `final/mycc.py` である。

## 最初にすること

**[`docs/getting_started.md`](./docs/getting_started.md) を読む。ここが唯一の入口である。**
必要な Python バージョン・環境の用意・読む順序・各回の進め方・全16コマ一覧は、
すべてその文書にまとまっている。この README の残りは、あとから場所を確かめるための一覧である。

## この中にあるもの

| パス | 内容 |
|------|------|
| [`docs/`](./docs/README.md) | 学習者向け文書の逆引き索引（進め方・言語仕様・RV64 リファレンス・テスト・デバッグ） |
| `sessions/NN_xxx/` | 各回の作業指示・`mycc.py`・テスト（資料は[サイト](https://yf-fyf.github.io/c-comp/)） |
| `final/` | コマ15 で作る最終統合版と `fixed17` テスト |
| [`advanced/`](./advanced/README.md) | 選択制の発展課題 26 トピック（C 移植・セルフホストを含む） |
| [`ocaml/`](./ocaml/README.md) | 各回の完成形に相当する OCaml 版参考実装 |
| `scaffold/` | 提供される Lexer / Parser / AST 定義 / テストランナー |
| [`docker/rv64/`](./docker/rv64/README.md) | 推奨実行環境 |
| [`guides/`](./guides/) | 補助ツールの導入手順（任意） |

## よく使うコマンド

`workbook/` から実行する。

```bash
# 各回のテスト
python3 scaffold/test_runner.py sessions/02_arithmetic_codegen

# 最終統合版のテスト（コマ15 以降）
python3 scaffold/test_runner.py

# AST を確認する
python3 scaffold/parse_viewer.py sessions/01_interpreter/tests/add_mul.c
```

詳細は [`docs/testing.md`](./docs/testing.md) を参照。
