# コマ15: 複数ファイル・前処理の概念

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

`#include "file.h"` や `#define NAME value` を含む入力を扱い、複数 `.c` ファイルをまとめてコンパイルできるようにする。

## 実装する主な機能

- 既存の `preprocess()` 関数で `#include` / `#define` を扱う
- `parse_file(filename)` を導入し、ファイルごとの処理をまとめる
- コマンドライン引数に複数の `.c` ファイルを受け取る
- 全ファイルの AST を1つに連結する
- `ND_FUNCPROTO` はコード生成しない

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/15_preprocess_multifile
```
