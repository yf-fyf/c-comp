# コマ12: 構造体（struct / . / ->）

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/12_struct/](https://yf-fyf.github.io/c-comp/sessions/12_struct/) にあります。

## 今日のゴール

`struct タグ { ... };` の定義、構造体変数、`.`、`->` を実装する。

## 実装する主な機能

- `struct タグ { ... };` の定義を読み、フィールドのレイアウトを管理する
- 構造体変数を扱う（フィールドは `int`・`char`・ポインタに限る）
- `.` による直接メンバアクセスをコード生成する
- `->` によるポインタ経由メンバアクセスをコード生成する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/12_struct
```
