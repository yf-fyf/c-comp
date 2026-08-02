# 学習者向けドキュメント — 索引

**始めるときは [`getting_started.md`](./getting_started.md) から。** ここは入口ではなく、
どの文書に何があるか・知りたいことがどこにあるかを引くための索引である。

## 文書の一覧

上の3つが「読むもの」、下の3つが「引くもの」である。

| 文書 | 内容 | 読みどき |
|------|------|---------|
| [`getting_started.md`](./getting_started.md) | 進め方・環境の用意・読む順序・全17コマ（01〜17）一覧・コマ16 のあと | **最初に**（入口） |
| [`conventions.md`](./conventions.md) | 実装の約束ごと（編集するファイル・`emit()`・命名） | コマ3 の前に一度。`codegen` / `codegen_lval` の分離はコマ4 で最小形を導入しコマ8 で拡張するので、両方の回に読み直す |
| [`testing.md`](./testing.md) | `test_runner` の使い方・テストケースの形式と、動かないときの確認手順・症状表 | テストはコマ3 から毎回。デバッグの後半は詰まったとき |
| [`language_spec.md`](./language_spec.md) | Core プロファイルの言語仕様（型・演算子・EBNF・除外機能・標準/発展の到達範囲） | 引くもの。冒頭に目次がある |
| [`rv64_reference.md`](./rv64_reference.md) | 呼び出し規約・スタックフレーム・よく使う命令 | 引くもの |
| [`code_example.md`](./code_example.md) | 各コマ終了時点でコンパイルできるプログラム（コマ1〜16） | 引くもの。冒頭に目次がある |

## 知りたいことから引く

| 知りたいこと・キーワード | 行き先 |
|------------------------|--------|
| 環境を作りたい / Docker / Python のバージョン | [`getting_started.md` の「環境を用意する」](./getting_started.md#環境を用意する) |
| この機能は書けるのか（`switch`・`+=`・後置 `++`・ビット演算 など） | [`language_spec.md` の除外機能の一覧](./language_spec.md#excluded) |
| 使える型・演算子・優先順位 | [`language_spec.md` の型](./language_spec.md#types)・[演算子](./language_spec.md#operators) |
| 構文が通らない / EBNF を確かめたい | [`language_spec.md` の形式文法](./language_spec.md#grammar) |
| この機能はどのコマで導入されるか | [`language_spec.md` の対応表](./language_spec.md#feature-map) |
| 除算の丸め方向・評価順序・未定義動作 | [`language_spec.md` の実行時の意味](./language_spec.md#semantics) |
| gcc で通る C との違い | [`language_spec.md` の ISO C との関係](./language_spec.md#isoc) |
| `printf` / `malloc` の宣言 | [`language_spec.md` の標準ライブラリ](./language_spec.md#stdlib) |
| どこまで書けるコンパイラになったか / 具体例が見たい | [`code_example.md` の目次](./code_example.md) |
| `codegen` と `codegen_lval` の分け方 | [`conventions.md` の「守ってほしい設計」](./conventions.md#守ってほしい設計) |
| 関数名・変数名をどう付けるか / 名前を変えてよいか | [`conventions.md` の「命名の目安」](./conventions.md#命名の目安) |
| テストの走らせ方・テストケースの書き方 | [`testing.md`](./testing.md) |
| 呼び出し規約・スタックフレーム・命令の意味 | [`rv64_reference.md`](./rv64_reference.md) |
| テストが落ちる / 終了コードが変 / 実行時に壊れる | [`testing.md` の症状表](./testing.md#症状から当たりをつける) |
| `AttributeError` が出る / 昔取得したファイルがある | [`testing.md` の症状表](./testing.md#症状から当たりをつける) |
| コマ16 のあと何をするか | 次は[コマ17（発表・振り返り）](https://yf-fyf.github.io/c-comp/sessions/17_demo_review/)。[`getting_started.md` の「コマ16 のあと」](./getting_started.md#コマ16-のあと) |
| 発表で何を話すか / 自分の実装をどう説明するか | [コマ17 の資料](https://yf-fyf.github.io/c-comp/sessions/17_demo_review/) |
| 発展課題26トピックからどれを選ぶか | [コマ17 の資料](https://yf-fyf.github.io/c-comp/sessions/17_demo_review/)（選び方）・[`../advanced/README.md`](../advanced/README.md)（一覧と前提の出典） |

## この外にあるもの

| 場所 | 内容 |
|------|------|
| [`../advanced/README.md`](../advanced/README.md) | 発展課題 26 トピックの一覧と依存関係(C 移植・セルフホスト P1 を含む) |
| [`../ocaml/README.md`](../ocaml/README.md) | 各回の完成形に相当する OCaml 版参考実装(完成相当なので、自分の方針を考えたあとの確認に) |
| [`../docker/rv64/README.md`](../docker/rv64/README.md) | Docker 環境の詳細設定とトラブルシュート |
| `design/curriculum.md`（開発リポジトリ） | 教材の設計思想（なぜこの順序・なぜ RV64 なのか） |
