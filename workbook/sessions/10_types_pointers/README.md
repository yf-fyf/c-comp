# コマ10: Type + ポインタ演算

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/10_types_pointers/](https://yf-fyf.github.io/c-comp/sessions/10_types_pointers/) にあります。

## 今日のゴール

型サイズを管理する仕組みを導入し、ポインタ演算・`sizeof(型名)`・添字 `p[i]` を実装する。

## 実装する主な機能

- `int`・`char`・ポインタの型サイズを管理する
- ポインタ演算（`p + 2` などが指す先の型サイズ分進む）をコード生成する
- `sizeof(型名)` をコード生成する
- 添字 `p[i]`（`*(p + i)` の略記）をコード生成する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/10_types_pointers
```
