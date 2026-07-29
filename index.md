---
title: 実践・C コンパイラ演習 — 講義資料
tags: compiler, RISC-V, Python, 教材
description: C 言語サブセットのコンパイラを段階的に作る演習教材。全16回 + 発展25トピックの資料一覧。
---

<!--
  HackMD 用のルートページ。このファイルの内容をそのまま HackMD に貼って使う。

  公開前に必須の作業:
    {{BASE_URL}} を実際のリポジトリ URL に一括置換する。
    blob 形式（例: https://github.com/<user>/<repo>/blob/main）にすると
    PDF と Markdown の両方が同じベースで開ける。
    置換したら下の :::warning ブロックを削除する。

  教材を追加・改名したときは、この index.md の表も更新する
  （手順は design/maintaining.md の「教材追加の手順」）。
-->

:::warning
**このページのリンクはまだ有効ではありません。** `{{BASE_URL}}` を実際のリポジトリ URL に置換してから公開してください。
:::

# 実践・C コンパイラ演習

C 言語サブセットのコンパイラを、**動く状態を保ちながら**段階的に作り上げる演習教材です。

[TOC]

## この教材について

- **方針**: 「Python で理解 → C に移植」。前半は Python でコンパイラの論理だけに集中し、後半は動く Python 版を参照実装として C へ移植する
- **ターゲット**: RISC-V RV64（qemu で実行。実機は不要）
- **到達点**: 標準トラックは Python 版 C サブセットコンパイラの完成。その先に C 移植・セルフホストへの挑戦がある
- **対象**: C 言語既習・コンパイラ理論未習の学習者

### 設計の考え方

Ghuloum (2006) のインクリメンタル方式を採り、次の原則で全体を組んでいます。

| 原則 | 内容 |
|------|------|
| 1コマ1機能 | 各回は資料を読んで実装し、その日のうちに動かして確認できる粒度に分割してある |
| 常に動く | どの時点でも実行可能なコンパイラを維持する |
| テストが先 | 機能を足す前にテストを書く |
| 実機で確かめる | 生成アセンブリは毎回 qemu で実行して確認する |
| 複雑さは後回し | 初期は外部ツールに任せ、自前化を後ろに送る |

Lexer / Parser は最初は黒箱として提供されるので、**コード生成から書き始められます**。
フロントエンドの自作そのものは発展課題（F 系列）として用意してあります。

## 進め方

| フェーズ | 回 | 内容 |
|----------|------|------|
| Phase 0 | 1〜2 | 環境構築 + AST 理解 |
| Phase 1 | 3〜11 | Python 版ミニコンパイラを完成させる |
| Phase 2 | 12〜16 | Python 版標準機能を完成させる |
| Phase 3 | 発展 | 選択制の発展課題 / C 移植・セルフホスト |

Phase 1 の終わり（コマ11）で「小さいが動くコンパイラ」が一度完成します。
ここで到達感を作ってから、Phase 2 で構造体などの重い機能に進む構成です。

「コマ」は1回分の作業単位（資料を読む + 実装 70〜90 分程度）を表します。
週1回のペースでも、集中して一気に進めても構いません。

## 通常回（コマ1〜16）

テーマ名をクリックすると資料 PDF が開きます。

| コマ | テーマ | 到達目標 |
|------|--------|---------|
| 1 | [環境構築 + スキャフォールド概観 + RV64 手書きアセンブリ体験]({{BASE_URL}}/workbook/sessions/01_environment/handout.pdf) | qemu 上でアセンブリが動く。提供 Lexer/Parser で `1+2*3` の AST を表示できる |
| 2 | [AST の仕組み + インタープリターを書く]({{BASE_URL}}/workbook/sessions/02_interpreter/handout.pdf) | `eval_ast()` が動く。AST を走査して意味を取り出す感覚を掴む |
| 3 | [コード生成①：算術式 → RV64 アセンブリ出力]({{BASE_URL}}/workbook/sessions/03_arithmetic_codegen/handout.pdf) | `codegen()` が動く。`echo $?` で計算結果を確認できる |
| 4 | [コード生成②：変数・代入・シンボルテーブル]({{BASE_URL}}/workbook/sessions/04_variables/handout.pdf) | `int a=3; return a;` をコンパイルして実行できる |
| 5 | [制御構文①：if/else]({{BASE_URL}}/workbook/sessions/05_if_else/handout.pdf) | `if(a>b) return a; else return b;` が動く |
| 6 | [制御構文②：while / for]({{BASE_URL}}/workbook/sessions/06_loops/handout.pdf) | フィボナッチ（ループ版）が動く |
| 7 | [再帰的な変数宣言収集]({{BASE_URL}}/workbook/sessions/07_functions_abi/handout.pdf) | 入れ子ブロック内の変数宣言も収集し、フレームサイズを正しく計算できる |
| 8 | [関数呼び出し・再帰]({{BASE_URL}}/workbook/sessions/08_functions_recursion/handout.pdf) | 再帰フィボナッチが動く |
| 9 | [lvalue / rvalue の概念 + `&` / `*`]({{BASE_URL}}/workbook/sessions/09_lvalue_rvalue/handout.pdf) | `codegen()` と `codegen_lval()` を別関数として設計・実装できる |
| 10 | [Type + ポインタ演算 + 配列]({{BASE_URL}}/workbook/sessions/10_types_arrays/handout.pdf) | `int a[5]; a[i]` と `*(p + 2)` のポインタ演算が動く |
| 11 | [文字列リテラル + `printf` + 総合確認]({{BASE_URL}}/workbook/sessions/11_strings_printf/handout.pdf) | `printf("hello\n")` が動く。ミニコンパイラの完成を確認する |
| 12 | [struct / typedef / `.` / `->`]({{BASE_URL}}/workbook/sessions/12_struct_typedef/handout.pdf) | `Point` や単純な構造体ポインタ操作が動く |
| 13 | [`sizeof` + `malloc` + 連結リスト]({{BASE_URL}}/workbook/sessions/13_sizeof_malloc_list/handout.pdf) | リンクリストが動く |
| 14 | [グローバル変数・スコープ管理]({{BASE_URL}}/workbook/sessions/14_globals_scope/handout.pdf) | グローバル変数とローカル変数を混在したプログラムが動く |
| 15 | [複数ファイル・前処理の概念（`#include` / `#define`）]({{BASE_URL}}/workbook/sessions/15_preprocess_multifile/handout.pdf) | `#include` / `#define` を含む複数 `.c` ファイルをまとめてコンパイルできる |
| 16 | [Python 版総合演習・`mycc.py` 統合]({{BASE_URL}}/workbook/sessions/16_integrate_mycc/handout.pdf) | 標準トラック完成（`final/mycc.py` に統合し、`final/tests` 全通を目安とする） |

## 発展課題（25トピック）

すべて**選択制**です。回 ID の頭文字がカテゴリを表します。

| 頭文字 | カテゴリ | 内容 |
|--------|----------|------|
| **F** | フロントエンド | 字句解析・構文解析を自分で作り、スキャフォールドを置き換える |
| **B** | 最適化入門 | 測定基盤なしで始められる軽量な最適化（前提はコマ8） |
| **O** | 最適化 | 測定 → 解析 → 変換を積み上げる本格版（前提はコマ16） |
| **R** | ランタイム | libc なしで動かす、`printf` / `malloc` の自作 |
| **S** | 意味論 | 短絡評価、`int` の32ビット性、ポインタ差 — 本実装との差を埋める |
| **L** | 言語機能 | 構造体の拡張、初期化子、可変長引数 |
| **Q** | 品質 | 型検査でエラーを出す |

「コマ」列はその回にかかる作業単位の数です。

### どこから始めるか

| やりたいこと | おすすめ |
|--------------|----------|
| コンパイラの入口（字句・構文解析）を理解したい | **F0**（コンパイラ本編と独立。前提はコマ2 まで） |
| コマ16 を待たずに最適化を試したい | **B1**（測定基盤なしで始められる） |
| 生成したコードを本気で速くしたい | **O1**（まず測る物差しを作る） |
| 自分のコンパイラの「嘘」を直したい | **S1**（`&&` が短絡していないことの確認から） |
| OS もライブラリも無い世界を見たい | **R1** |

### F: フロントエンド

スキャフォールドで黒箱として使ってきた Lexer / Parser を、自分の手で理解し、作り、置き換えます。
F0 は独立した導入回。F1 以降は積み上げ式で、最終目標は自作の Lexer / Parser で `final/tests` を通すことです。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| F0 | [字句解析と構文解析とは何か（CYK 法で数式を解く）]({{BASE_URL}}/workbook/advanced/F0_cyk/handout.pdf) | 1 | コマ2 |
| F1 | [字句解析: `scaffold/lexer.py` 読解 + Core lexer 自作]({{BASE_URL}}/workbook/advanced/F1_lexer/handout.pdf) | 1 | F0 |
| F2 | [再帰下降①: 式のパーサ（EBNF の階層 = 関数の階層）]({{BASE_URL}}/workbook/advanced/F2_parser_expr/handout.pdf) | 1 | F1 |
| F3 | [再帰下降②: 文・制御構文（dangling else）]({{BASE_URL}}/workbook/advanced/F3_parser_stmt/handout.pdf) | 1 | F2 |
| F4 | [再帰下降③: 宣言・型・typedef（黒箱の完全置き換え）]({{BASE_URL}}/workbook/advanced/F4_parser_decl/handout.pdf) | 1 | F3 |

### B: 最適化入門

生成したコードを速くするトピックのうち、**測定基盤を必要としない**もの。
前提はコマ8（関数呼び出し）までなので、コマ16 を待たずに始められます。各回は独立しています。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| B1 | [最適化入門: 定数畳み込み + ピープホール]({{BASE_URL}}/workbook/advanced/B1_fold_peephole/handout.pdf) | 1 | コマ8 |
| B2 | [式の途中結果を t レジスタへ（スタックマシンを卒業する）]({{BASE_URL}}/workbook/advanced/B2_regalloc/handout.pdf) | 1 | コマ8 |
| B3 | [末尾呼び出し最適化（再帰をループに変える）]({{BASE_URL}}/workbook/advanced/B3_tailcall/handout.pdf) | 1 | コマ8 |

:::info
**B2 と O4 の違い**: B2 が扱うのは**式の途中結果**の退避先（メモリ → t レジスタ）。O4 が扱うのは**局所変数**の置き場所（メモリ → callee-saved レジスタ）。別の問題を解いているので、両方やっても効果は重なりません。
:::

### O: 最適化

**測定 → 解析 → 変換**の順に積み上げます。全部で10コマですが、各回は独立して取り組めます。
O1 と O2 を先に済ませておけば、O3・O4・O7 はどれから始めてもよいです。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| O1 | [最適化の測り方（静的/動的命令数、ベンチマーク集）]({{BASE_URL}}/workbook/advanced/O1_measure/handout.pdf) | 1 | コマ16 |
| O2 | [基本ブロックとフローグラフ]({{BASE_URL}}/workbook/advanced/O2_cfg/handout.pdf) | 1 | コマ16 |
| O3 | [命令選択（複数命令を1命令に畳む）]({{BASE_URL}}/workbook/advanced/O3_isel/handout.pdf) | 2 | O1 |
| O4 | [局所変数を callee-saved レジスタへ]({{BASE_URL}}/workbook/advanced/O4_regalloc/handout.pdf) | 2 | コマ16, O1 |
| O5 | [生存変数解析]({{BASE_URL}}/workbook/advanced/O5_liveness/handout.pdf) | 1 | O2, O4 |
| O6 | [コピー伝播と死コード除去]({{BASE_URL}}/workbook/advanced/O6_copyprop/handout.pdf) | 2 | O1, O2, O4, O5 |
| O7 | [ブロック整列とループ回転]({{BASE_URL}}/workbook/advanced/O7_layout/handout.pdf) | 1 | O1 |

```text
O1(測定) ──┬─→ O3(命令選択)
           ├─→ O4(レジスタ割り当て) ─┐
           └─→ O7(ブロック整列)      │
                                      ├─→ O6(コピー伝播 / 死コード除去)
O2(フローグラフ) ─→ O5(生存解析) ────┘
```

全部かけたときの効果（5本のベンチマーク合計）: 静的命令数 1089 → 781（-28.3%）、動的命令数 209492 → 158005（-24.6%）。

### R: ランタイム

gcc とライブラリに任せていた部分を、自分の手で開けます。
R2 は R1 の `syscall.s` を土台にします。R3 は独立しています（libc を使ってよい）。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| R1 | [libc なしで動かす（システムコール直接発行）]({{BASE_URL}}/workbook/advanced/R1_nolibc/handout.pdf) | 1 | コマ11 |
| R2 | [自前 printf（整数→10進文字列の変換）]({{BASE_URL}}/workbook/advanced/R2_printf/handout.pdf) | 1 | R1 |
| R3 | [自前 malloc（バンプ割り当て → フリーリスト）]({{BASE_URL}}/workbook/advanced/R3_malloc/handout.pdf) | 1 | コマ13 |

### S: 意味論

いまの実装が C の規格とずれている箇所を、自分で見つけて直します。
どれも「テストが通ってしまうので気づきにくい」性質を持ちます。各回は独立しています。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| S1 | [短絡評価（`&&` / `\|\|` が右辺を評価してしまう）]({{BASE_URL}}/workbook/advanced/S1_shortcircuit/handout.pdf) | 1 | コマ8 |
| S2 | [`int` の演算が32bitで折り返さない]({{BASE_URL}}/workbook/advanced/S2_int32/handout.pdf) | 1 | コマ10 |
| S3 | [ポインタ同士の引き算が要素数にならない]({{BASE_URL}}/workbook/advanced/S3_ptrdiff/handout.pdf) | 1 | コマ10 |

### L: 言語機能

Core プロファイルで「扱わない」と決めた機能を、あとから足します。
どれも `mycc.py` と `scaffold/` を書き換えず、ラッパーで差し込みます。各回は独立しています。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| L1 | [構造体の代入・ネスト（値渡しは発展課題）]({{BASE_URL}}/workbook/advanced/L1_struct/handout.pdf) | 1 | コマ12 |
| L2 | [初期化子リスト（`int a[3] = {1,2,3}`、`char s[] = "hi"`）]({{BASE_URL}}/workbook/advanced/L2_initializer/handout.pdf) | 1 | コマ14 |
| L3 | [可変長引数の「定義」（`int sum(int n, ...)`）]({{BASE_URL}}/workbook/advanced/L3_variadic/handout.pdf) | 1 | コマ11 |

### Q: 品質

コンパイラ本体には手を入れず、独立したパスとして追加します。
「正しいプログラムを1つも拒まない」ことを、教材のテスト入力全体で確認します。

| 回 | 内容 | コマ | 前提 |
|----|------|------|------|
| Q1 | [型検査パス（実行前に誤りをまとめて報告する）]({{BASE_URL}}/workbook/advanced/Q1_typecheck/handout.pdf) | 1 | コマ12 |

### 共通のルール

- `mycc.py` と `scaffold/` は書き換えない。機能はラッパー、独立したパス、またはパッチとして差し込む
- **`final/tests`（fixed15）が通り続けること**を、意味を壊していないことの基準にする
- 完了条件は各トピックの `README.md` と資料 PDF に書いてある

## C 移植・セルフホスト

Python 版コンパイラを C へ移植するトラックは、1回で完結するトピックではないため別に分けてあります。
`struct Node` などのインフラ移植 → コード生成移植 → フロントエンド移植 → セルフホスト挑戦、の順に進みます。

移植の原則は「アルゴリズムの再発明」ではなく「データ構造の C 化」です。

- [C 移植・セルフホストの進め方]({{BASE_URL}}/workbook/porting/README.md) — 移植の原則・C 実装の規約・セルフホストの検証
- [C 版の到達目標コード例]({{BASE_URL}}/workbook/porting/code_example.md) — 各段階でどこまでコンパイルできればよいか

## 仕様・参考文書

学習者向けドキュメントは「読むもの」と「引くもの」に分かれています（索引は [`docs/README.md`]({{BASE_URL}}/workbook/docs/README.md)）。

| 文書 | 種別 | 内容 |
|------|------|------|
| [進め方ガイド]({{BASE_URL}}/workbook/docs/getting_started.md) | 読む | 環境の用意・全24コマ一覧・到達目標・コマ16 のあと |
| [実装の約束ごと]({{BASE_URL}}/workbook/docs/conventions.md) | 読む | `codegen` / `codegen_lval` の分離など、守ってほしい設計 |
| [デバッグ手順]({{BASE_URL}}/workbook/docs/debugging.md) | 読む | 症状から原因を絞る表・gdb の使い方 |
| [Core プロファイル言語仕様]({{BASE_URL}}/workbook/docs/language_spec.md) | 引く | 対象言語の型・演算子・文法（EBNF）・除外機能 |
| [RV64 リファレンス]({{BASE_URL}}/workbook/docs/rv64_reference.md) | 引く | 呼び出し規約・スタックフレーム・よく使う命令 |
| [テストの走らせ方]({{BASE_URL}}/workbook/docs/testing.md) | 引く | `test_runner` の使い方・テストケースの形式 |
| [到達目標コード例]({{BASE_URL}}/workbook/docs/code_example.md) | 引く | 各コマ終了時点でコンパイルできるプログラム（コマ1〜16） |
| [発展課題の入口]({{BASE_URL}}/workbook/advanced/README.md) | 引く | 全25トピックの一覧と依存関係 |

## 手を動かす

演習は `workbook/` の中で完結します。

```bash
git clone {{BASE_URL}}
cd workbook
```

### 実行環境

Docker を推奨します（RV64 クロスコンパイラと qemu が入った環境が用意されています）。

```bash
# コンテナ起動（初回はイメージをビルド）
bash docker/rv64/run.sh

# 1コマンドだけ実行する（例: コマ1の環境確認）
bash docker/rv64/run.sh python3 sessions/01_environment/check.py
```

ネイティブ実行も可能です。その場合 `riscv64-linux-gnu-gcc` と `qemu-riscv64` が必要です。

### 各回の進め方

1. `sessions/NN_xxx/handout.pdf` を読む
2. `sessions/NN_xxx/README.md` の作業指示を見る
3. `sessions/NN_xxx/mycc.py` を編集する
4. テストを走らせる

```bash
# コマ3のテスト
python3 scaffold/test_runner.py sessions/03_arithmetic_codegen

# 最終統合版（コマ16以降）のテスト
python3 scaffold/test_runner.py
```

### AST を確認する

各回の資料は、冒頭で対象プログラムの AST を眺めることから始まります。

```bash
python3 scaffold/parse_viewer.py sessions/02_interpreter/tests/add_mul.c
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --tokens
```

### 詰まったとき

各回の完成形に相当する **OCaml 参考実装**が `ocaml/` に入っています。
Python 版をそのまま写すためではなく、自分の方針を考えたあとに
AST の場合分けと再帰の流れを別言語で確認するために使ってください。

```bash
cd ocaml && dune build
dune exec ./koma04.exe -- ../sessions/04_variables/tests/target.c
```

## 補助ツール

| 資料 | 内容 |
|------|------|
| [OpenCode 導入ガイド]({{BASE_URL}}/workbook/guides/opencode.pdf) | AI コーディング支援ツールの導入手順（任意） |

## ライセンス・出典

この教材とリポジトリ内の自作コードは [MIT License]({{BASE_URL}}/LICENSE) です。
第三者依存の扱いは [`THIRD_PARTY_NOTICES.md`]({{BASE_URL}}/THIRD_PARTY_NOTICES.md) を参照してください。

参考文献:

- Abdulaziz Ghuloum, "An Incremental Approach to Compiler Construction" (Scheme Workshop 2006)
- Rui Ueyama「低レイヤを知りたい人のための C コンパイラ作成入門」
