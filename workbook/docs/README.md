# 学習者向けドキュメント

「読むもの」と「引くもの」に分かれている。

## 読むもの

| 文書 | 内容 | いつ |
|------|------|------|
| [`getting_started.md`](./getting_started.md) | 進め方・環境の用意・全17コマ一覧・コマ16 のあと | **最初に** |
| [`conventions.md`](./conventions.md) | 実装の約束ごと（`codegen` / `codegen_lval` の分離など） | コマ3 の前に一度 |
| [`debugging.md`](./debugging.md) | 動かないときの確認手順 | 詰まったとき |
| [`migration.md`](./migration.md) | 2026-08-01 の教材更新と、古いファイルとの非互換の一覧 | それより前に取得したファイルで作業しているとき |

## 引くもの

| 文書 | 内容 |
|------|------|
| [`language_spec.md`](./language_spec.md) | Core プロファイルの言語仕様（型・演算子・EBNF・除外機能・標準/発展の到達範囲） |
| [`rv64_reference.md`](./rv64_reference.md) | 呼び出し規約・スタックフレーム・よく使う命令 |
| [`testing.md`](./testing.md) | `test_runner` の使い方・テストケースの形式 |
| [`code_example.md`](./code_example.md) | 各コマ終了時点でコンパイルできるプログラム（コマ1〜16） |

## この外にあるもの

| 場所 | 内容 |
|------|------|
| [`../advanced/README.md`](../advanced/README.md) | 発展課題 26 トピックの一覧と依存関係(C 移植・セルフホスト P1 を含む) |
| [`../docker/rv64/README.md`](../docker/rv64/README.md) | Docker 環境の詳細設定とトラブルシュート |
| `design/curriculum.md`（開発リポジトリ） | 教材の設計思想（なぜこの順序・なぜ RV64 なのか） |
