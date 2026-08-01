# P1: C 移植・セルフホスト — Python 版を C で書き直す

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/P1_selfhost/](https://yf-fyf.github.io/c-comp/advanced/P1_selfhost/) にあります。

## このトピックのゴール

Python 版コンパイラを C 言語で書き直し、最終的に自分自身をコンパイルできる状態
（セルフホスト）を目指す長期プロジェクト。他の発展課題と違い、**1回では終わりません**。
「今日中にここまで」という区切りは置かず、自分のペースで進めます。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ16（完成した `final/mycc.py`） |
| 推奨の前提 | F1〜F4（フロントエンドの移植がかなり楽になる） |
| 改変しない | `mycc.py`、`scaffold/`（読解の対象であって、書き換えない） |
| 編集する | 自分で用意する `src/`（構成は自由。雛形は配らない） |
| 完了条件 | 自動採点は無い。参考達成条件（必達目標ではない）は、`mycc_stage1` の生成成功、`final/tests`（`fixed17`）の全通、前処理（`#include` / `#define`）の自前実装が動くこと |
| コマ数 | - |
| 備考 | 移植・セルフホスト発展シリーズ。他のトピックと違って1回では終わらず、`check.py` / `golden.py` も無い。資料が示すのは大まかな方針だけである |

## このトピックについて

他のトピックのような `check.py` / `golden.py` による自動採点は**ない**。
資料が示すのは、進め方の大まかな方針だけである。実装は自分で
`src/` ディレクトリ（好きな構成でよい）を用意して進める。

## 進め方

1. データ構造の移植（`struct Node`・`struct Type`・シンボルテーブル・`emit()`）
2. コード生成の移植（算術・変数・制御構文 → 関数・ポインタ → 配列・構造体・グローバル変数）
3. フロントエンドの移植（`scaffold/lexer.py` / `parser.py` を読解。
   F 系列（[`F1_lexer`](../F1_lexer/README.md) 〜 [`F4_parser_decl`](../F4_parser_decl/README.md)）を
   先にやっておくと楽になる）
4. セルフホストへの挑戦（`#include` / `#define` の自前実装 + Stage 0/Stage 1 の確認）

詳しい方針は資料本文を参照。

## 検証の例

```bash
gcc -o mycc_stage0 src/*.c
./mycc_stage0 src/*.c -o mycc_stage1
python3 ../../scaffold/test_runner.py --compiler ./mycc_stage1 --tests ../../final/tests
```

参考達成条件（必達目標ではない）: `mycc_stage1` の生成成功 + `final/tests`（fixed17）全通 +
前処理の自前実装が動くこと。
