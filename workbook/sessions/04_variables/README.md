# コマ4: 変数・代入・シンボルテーブル

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/04_variables/](https://yf-fyf.github.io/c-comp/sessions/04_variables/) にあります。

## 今日のゴール

ローカル変数の宣言・参照・代入を実装する。変数 `a`, `b`, `c` をスタック上に確保し、代入・参照できるようにする。

## 実装する主な機能

- ローカル変数宣言（`int a;`）をスタック上に確保する
- 変数への代入と参照をコード生成する
- 変数を含む算術式を扱う
- 複数文からなる関数本体を順に実行する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/04_variables
```
