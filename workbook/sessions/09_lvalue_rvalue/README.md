# コマ9: lvalue / rvalue + ポインタ

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/09_lvalue_rvalue/](https://yf-fyf.github.io/c-comp/sessions/09_lvalue_rvalue/) にあります。

## 今日のゴール

`codegen()` と `codegen_lval()` を分離し、`&` と `*` を実装する。式を rvalue（評価して得られる値）と lvalue（書き込み先として使える場所）の2通りで扱う。

## 実装する主な機能

- 式を rvalue（値）と lvalue（書き込み先アドレス）の2通りで扱う
- `&` によるアドレス取得をコード生成する
- `*` による間接参照（読み出し・書き込み）をコード生成する
- ポインタを引数として渡す関数呼び出しを扱う

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/09_lvalue_rvalue
```
