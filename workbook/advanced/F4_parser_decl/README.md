# F4: 再帰下降パーサ③ — 宣言・型・プログラム全体（最終回）

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F4_parser_decl/](https://yf-fyf.github.io/c-comp/advanced/F4_parser_decl/) にあります。

## 今日のゴール

宣言・型・関数・typedef を実装して `parse_program` を完成させる。
講義の全テスト入力（約100本の `.c`）で AST が scaffold と完全一致したら、
Lexer（F1）とあわせて黒箱の完全な置き換え達成。

前提は F3（`ProgramParser` は自分の F3 `StmtParser` を継承する）。

## 編集するファイル

- `myparser.py`（Step 1〜5。`sizeof` への分岐など一部は完成済み）

## 動かし方

```bash
python3 myparser.py ../../sessions/13_sizeof_malloc_list/tests/list_min.c
```

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(Step 2 以降は scaffold と構造比較)
python3 golden.py    # 全テスト入力(約100本)で scaffold と突き合わせ
```

`golden.py` の全ファイル PASS がシリーズの完了条件です。
