# コマ12: 構造体とヒープ（struct / `.` / `->` / `sizeof` / `malloc` / 連結リスト）

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/12_struct_malloc_list/](https://yf-fyf.github.io/c-comp/sessions/12_struct_malloc_list/) にあります。

## 今日のゴール

`struct タグ { ... };` の定義、構造体変数、`.`、`->` を実装する。
続けて `sizeof(struct タグ)` で求めたサイズを `malloc` に渡し、
ヒープ上に確保した構造体をポインタでつないで連結リストを動かす。

## 実装する主な機能

- `struct タグ { ... };` の定義を読み、フィールドのレイアウトを管理する
- 構造体変数を扱う（フィールドは `int`・`char`・ポインタに限る）
- `.` と `->` によるメンバアクセスをコード生成する
- `sizeof` を構造体へ広げる（`sizeof(struct Node)`。`sizeof(int)` などはコマ9 で導入済み）
- `malloc` で構造体をヒープに確保する（`malloc` 自体は自作せず libc のものを呼ぶ）
- `NULL`（`lib.h` の `#define NULL 0`）を終端の印として使う
- 自己参照構造体（`struct Node *next` など）と連結リストの走査を動かす

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/12_struct_malloc_list
```
