# コマ9: lvalue / rvalue + ポインタ

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/09_lvalue_rvalue/](https://yf-fyf.github.io/c-comp/sessions/09_lvalue_rvalue/) にあります。

## 今日のゴール

`codegen_lval()` を `*p` へ拡張し、`&` と `*` を実装する。`codegen()`（rvalue）と `codegen_lval()`（lvalue）の分離はコマ4 で入れてあり、この回では変数以外の式を書き込み先にできるようにする。

## 実装する主な機能

- `codegen_lval()` に `'Deref'` を足し、`*p` を代入先として扱えるようにする
- `&` によるアドレス取得をコード生成する
- `*` による間接参照（読み出し・書き込み）をコード生成する
- ポインタを引数として渡す関数呼び出しを扱う

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/09_lvalue_rvalue
```
