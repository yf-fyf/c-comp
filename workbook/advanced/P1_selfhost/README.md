# P1: C 移植・セルフホスト — Python 版を C で書き直す

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/P1_selfhost/](https://yf-fyf.github.io/c-comp/advanced/P1_selfhost/) にあります。

## 今日のゴール

Python 版コンパイラを C 言語で書き直し、最終的に自分自身をコンパイルできる状態
（セルフホスト）を目指す長期プロジェクト。他の発展課題と違い、1回では終わらない。

前提はコマ16 の完成した `../../final/mycc.py`。

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
