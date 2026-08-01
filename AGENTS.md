# AGENTS.md

C サブセットコンパイラを段階的に作る教材リポジトリ。
「Python で理解 → C に移植」の方針で、RISC-V RV64 をターゲットとする。

---

## 運用ルール

- **git commit はメンテナ（ユーザー）の明示的な許可を得てから行う。** 自動的に add / commit しない。
- **コミットメッセージは基本的に英語で書く。** 過去のコミットログ（日本語のものを含む）は書き換えない。
- 図の生成物（`materials/figures/**/*.svg`）はコミット対象。TikZ ソースを変更したら `make figures` で作り直す。
  資料の HTML は公開時に生成するのでコミットしない。
- **学習者・学生の個人情報（授業ログ・進捗記録・氏名等）をこのリポジトリに置かない。** 授業ログは親リポジトリ側（`../logs/`）だけで管理する。
- 完成解答・品質記録・隠しテストは、兄弟の Private リポジトリ `../c-comp-design/` だけで管理する。公開リポジトリへ置かず、学習者向けの `workbook/` に混入させない。
- 通常の調査では `node_modules/`、`_build/`、`.site/`、`.pages/`、`dist/`、`__pycache__/` を探索しない。生成 SVG は表示や生成差分を調べる場合を除き本文を読まず、TikZ ソースと生成手順を確認する。

---

## ドキュメント一覧

| ファイル | 内容 |
|----------|------|
| `README.md` | プロジェクト入口 |
| `site/nav.yaml` | 資料サイトの章立てとページの並び。教材を追加したらここに1行足す |
| `design/curriculum.md` | カリキュラム設計書（方針・フェーズ構成・設計原則） |
| `design/maintaining.md` | メンテナ用実装ガイド（ディレクトリ構成・ビルド手順） |
| `design/quality_guide.md` | 教材品質管理（制作・AIレビュー・改善ワークフロー） |
| `design/ai_usage.md` | AIモデルの使い分け・セッション分離・調査範囲の基本方針 |
| `design/webapps.md` | 補助ウェブアプリの企画書（アプリ案カタログ・実装方針。企画段階） |
| `workbook/docs/README.md` | 学習者向けドキュメントの逆引き索引（知りたいこと → 該当節） |
| `workbook/docs/getting_started.md` | 進め方ガイド（環境の用意・全コマ一覧・到達目標） |
| `workbook/docs/language_spec.md` | Core プロファイル（言語仕様・型システム・演算子） |
| `workbook/docs/conventions.md` | Python 実装の約束ごと（`codegen` / `codegen_lval` の分離など） |
| `workbook/docs/rv64_reference.md` | 呼び出し規約・スタックフレーム・よく使う命令 |
| `workbook/docs/testing.md` | `test_runner` の使い方・テストケースの形式 |
| `workbook/docs/code_example.md` | 各コマのコンパイル到達目標コード例 |
| `workbook/docs/debugging.md` | デバッグ手順（小さい入力に戻す・生成アセンブリの読み方） |
| `workbook/docs/migration.md` | 教材更新に伴う手元ファイルとの非互換と移行手順（学習者向け・唯一の出典） |

---

## 資料への導線

教材の内容は変更されるため、ここでは入口だけを示す。個別教材の詳細は各 README と対象ファイルを確認すること。

| パス | 役割 |
|------|------|
| `workbook/README.md` | 学習者向け配布物の入口（本文は `workbook/docs/getting_started.md` へ一本化） |
| `workbook/sessions/` | 通常回の配布教材。各回の `README.md` を入口とする |
| `materials/sessions/` | 通常回の資料の Markdown 原稿 |
| `workbook/scaffold/` | 共通のフロントエンド、AST、テスト基盤 |
| `workbook/final/` | 標準トラックの最終統合物とテスト |
| `workbook/ocaml/` | OCaml 版参考実装（完成相当の言語横断ヒント） |
| `workbook/advanced/README.md` | 発展教材の入口 |
| `materials/advanced/` | 発展教材の資料の Markdown 原稿 |
| `materials/figures/` | 図の TikZ ソースと生成 SVG（sessions・advanced 共用。`ast/` は生成物） |
| `workbook/docker/` | 推奨実行環境 |
| `web/` | 補助ウェブアプリ（A1 AST ビジュアライザ / A2 RV64 シミュレータ）。企画は `design/webapps.md`、構成は `web/README.md` |
| `../c-comp-design/teacher/` | 非公開の完成解答・品質記録・隠しテスト（Private リポジトリ） |

### 目的別の参照順

- 通常回の教材を扱う: `materials/sessions/` の原稿、対応する `workbook/sessions/`、関連する `workbook/docs/` を確認する。
- 発展教材を扱う: `workbook/advanced/README.md` から対象トピックを特定し、`materials/advanced/<回ID>.md` の原稿と `workbook/advanced/<回ID>/` の配布物を確認する（原稿名とトピックディレクトリ名は一対一）。
- 言語仕様や到達範囲を判断する: `workbook/docs/language_spec.md`、`workbook/docs/getting_started.md`、`workbook/docs/code_example.md` を確認する。
- 教材をレビューする: `design/quality_guide.md` と `../c-comp-design/teacher/quality/records/` の対象記録を確認する。

`materials/` は資料の原稿、`workbook/` は学習者向け配布物として扱う。
学習者経路を確認するときは、原則として `workbook/` 内だけを参照する。

---

## ビルド・テスト

```bash
# 資料サイト（依存: pandoc + PyYAML）
make site         # .site/ に全ページを生成
make serve        # 生成して配信。原稿を保存すると作り直して自動リロード
make check-links  # 内部リンク切れを検査

# 原稿・配布物の整合の機械チェック（除外リストは tools/doc_check_allowlist.yaml）
make check-docs                              # 全チェック（check-deps も一緒に走る）
make check-deps                              # 発展課題の索引・位置づけブロック・依存グラフの三者一致
python3 tools/check_docs.py --only ident     # 1つだけ
python3 tools/check_docs.py --list-kinds     # 除外リストに書ける検出種別
# code_example.md の C コードを実際に処理系へ通し、期待する終了コードまで照合する
# （依存: dune + menhir、riscv64-linux-gnu-gcc、qemu-riscv64）
make check-code-examples

# 図の SVG（依存: lualatex + poppler-utils + Graphviz）。図を触ったときだけ
make figures

# コンパイラのテスト（workbook/ から）
cd workbook && python3 scaffold/test_runner.py sessions/03_arithmetic_codegen
cd workbook && python3 scaffold/test_runner.py    # final/mycc.py + final/tests

# AST の確認
cd workbook && python3 scaffold/parse_viewer.py sessions/02_interpreter/tests/add_mul.c

# OCaml 参考実装
cd workbook/ocaml && dune build
make ocaml-test   # 各回を sessions/*/tests に掛ける（qemu 必要）

# RV64 実行環境（Docker）
bash workbook/docker/rv64/run.sh python3 scaffold/test_runner.py

# 補助ウェブアプリ（依存: opam の js_of_ocaml 系 + node）
make web        # 一括ビルド（web/app/dist/）
make web-test   # 黄金テスト（parse_viewer.py とのバイト一致）+ vitest
make sim-test   # RV64 シミュレータを qemu と突き合わせる
```

補助ウェブアプリの AST 表示は `workbook/scaffold/parse_viewer.py` の出力が正である。
`scaffold/`（lexer・parser・parse_viewer）や `workbook/ocaml/support/` を変更したら
`make web-test`（パーサの一致）と `make ocaml-test`（コード生成の回帰）の両方で確認する。

文法の定義は `workbook/scaffold/parser.py`・`workbook/ocaml/support/parser.mly`・
`workbook/ocaml/reference/parser.mly` の3系統に分かれている（`reference/` は
`support/` を借りず自前の字句解析・構文解析を持つ）。`workbook/docs/language_spec.md`
で言語仕様を変えるときは、この3系統すべてに反映する。確認は `workbook/ocaml/run_tests.py`
の**等価性テスト(受理側)と拒否側テストの両方**で行う（`--no-equivalence` で等価性テストのみ
飛ばせるが、拒否側は文法が2系統あることの担保なので省略しない）。
