# コマ3: 変数・代入・シンボルテーブル

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/03_variables/](https://yf-fyf.github.io/c-comp/sessions/03_variables/) にあります。

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

> - `workbook/` から実行する。
> - 前回までのテストが全通していることを前提とする。
> - FAIL したら、まず最初の失敗ケースを単体で確認する。詳しい手順は [`docs/testing.md`](../../docs/testing.md) を参照。

```bash
python3 scaffold/test_runner.py sessions/03_variables
```
