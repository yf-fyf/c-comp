# コマ8: 型検査の導入

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/08_types/](https://yf-fyf.github.io/c-comp/sessions/08_types/) にあります。

## 今日のゴール

`int`・`char`・ポインタの型をコンパイラが覚えるようにし、型サイズに応じてロード・ストア命令を選ぶ。

## 実装する主な機能

- ローカル変数表に型を持たせる（`name → (offset, ty_str)`）
- 式と左辺値の型を求める（`type_of_expr_*` / `type_of_lval_*`）
- 関数呼出しの戻り値型を、提供済みの関数表から取得する（`type_of_expr_Call`）
- 型サイズに応じてロード・ストア命令を選ぶ（`lb`/`lw`/`ld`、`sb`/`sw`/`sd`）
- `char` の昇格（読み出しで int へ）と縮小（代入で下位 8 ビットへ）
- 宣言とパラメータを型付きで確保する

関数の戻り値型を集める `collect_function_returns(prog)` と、その呼出しは提供済み。
実装するのは、この表から呼出し式の型を取得する処理である。
`call_ptr.c` は、プロトタイプの戻り値型を使って、関数が返したポインタを参照できることを確認する。

## 編集するファイル

- `mycc.py`

## テスト

> - `workbook/` から実行する。
> - 前回までのテストが全通していることを前提とする。
> - FAIL したら、まず最初の失敗ケースを単体で確認する。詳しい手順は [`docs/testing.md`](../../docs/testing.md) を参照。

```bash
python3 scaffold/test_runner.py sessions/08_types
```
