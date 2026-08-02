# F4: 再帰下降パーサ③ — 宣言・型・プログラム全体（最終回）

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F4_parser_decl/](https://yf-fyf.github.io/c-comp/advanced/F4_parser_decl/) にあります。

## 今日のゴール

型・宣言・`struct` 定義・関数を実装して `parse_program` を完成させる。
講義の全テスト入力（約100本の `.c`）で AST が スキャフォールド と完全一致したら、
Lexer（F1）とあわせてブラックボックスの完全な置き換え達成。

この回の主題は「同じ型の文法でも、書かれた位置（引数・変数・戻り値）で
許される型が違う」こと。スキャフォールド の scalar / obj / ret の3分類を自分で書く。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | F3 |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/` |
| 編集する | `myparser.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が全テスト入力（約100本の `.c`）でAST の完全一致を報告する |
| コマ数 | 1 |
| 備考 | フロントエンド発展シリーズの最終回。F1 とあわせてブラックボックスの完全な置き換えになる |

`ProgramParser` は、自分の F3 `StmtParser` を継承します。

## 編集するファイル

- `myparser.py`（Step 1〜5。`sizeof` への分岐など一部は完成済み）

## 動かし方

```bash
python3 myparser.py ../../sessions/13_struct_malloc_list/tests/list_min.c
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(Step 2 以降は scaffold と構造比較)
python3 golden.py    # 全テスト入力(約100本)で scaffold と突き合わせ
```

`check.py` には「弾かれるべき入力」（`void v;` / `f(struct Point p)` /
`sizeof x` など）の確認も入っています。

`golden.py` の全ファイル PASS がシリーズの完了条件です。
