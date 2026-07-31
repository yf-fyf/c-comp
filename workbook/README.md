# 学習者向けガイド

この教材では、Python で C 言語サブセットの簡易コンパイラを作る。
標準トラックの最終成果物は `final/mycc.py` である。Python は 3.10 以降を使う。

**まず [`docs/getting_started.md`](./docs/getting_started.md) を読む。**
環境の用意から各回の進め方まで、始めるのに必要なことがまとまっている。

## この中にあるもの

| パス | 内容 |
|------|------|
| [`docs/`](./docs/README.md) | 進め方・言語仕様・RV64 リファレンス・テスト・デバッグ |
| `sessions/NN_xxx/` | 各回の作業指示・`mycc.py`・テスト（資料は[サイト](https://yf-fyf.github.io/c-comp/)） |
| `final/` | コマ16 で作る最終統合版と `fixed17` テスト |
| [`advanced/`](./advanced/README.md) | 選択制の発展課題 25 トピック |
| [`porting/`](./porting/README.md) | C 移植・セルフホストトラック |
| [`ocaml/`](./ocaml/README.md) | 各回の完成形に相当する OCaml 版参考実装 |
| `scaffold/` | 提供される Lexer / Parser / AST 定義 / テストランナー |
| [`docker/rv64/`](./docker/rv64/README.md) | 推奨実行環境 |
| [`guides/`](./guides/) | 補助ツールの導入手順（任意） |

## よく使うコマンド

```bash
# 各回のテスト
python3 scaffold/test_runner.py sessions/03_arithmetic_codegen

# 最終統合版のテスト（コマ16 以降）
python3 scaffold/test_runner.py

# AST を確認する
python3 scaffold/parse_viewer.py sessions/02_interpreter/tests/add_mul.c
```

詳細は [`docs/testing.md`](./docs/testing.md) を参照。
