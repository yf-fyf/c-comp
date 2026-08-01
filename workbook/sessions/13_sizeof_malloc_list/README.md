# コマ13: sizeof + malloc + 連結リスト

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/13_sizeof_malloc_list/](https://yf-fyf.github.io/c-comp/sessions/13_sizeof_malloc_list/) にあります。

## 今日のゴール

`sizeof` と `malloc` を使い、構造体をヒープ上に確保して連結リストを動かす。

## 実装する主な機能

- `sizeof` を構造体へ広げる（`sizeof(struct Node)`。`sizeof(int)` などはコマ10 で導入済み）
- `malloc` で構造体をヒープに確保する（`malloc` 自体は自作せず libc のものを呼ぶ）
- `NULL`（`lib.h` の `#define NULL 0`）を終端の印として使う
- 自己参照構造体（`struct Node *next` など）を扱う
- ポインタをたどる連結リストの走査を動かす

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/13_sizeof_malloc_list
```
