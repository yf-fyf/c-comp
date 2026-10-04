# コマ8: 型検査の導入

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/08_types/](https://yf-fyf.github.io/c-comp/sessions/08_types/) にあります。

## 今日のゴール

`int`・`char`・ポインタの型をコンパイラが覚えるようにし、型サイズに応じてロード・ストア命令を選ぶ。

## 実装する主な機能

- ローカル変数表に型を持たせる（`name → (offset, ty_str)`）
- 式と左辺値の型を求める（`type_of_expr_*` / `type_of_lval_*`）
- 関数呼出しの戻り値型を、提供済みの関数表から取得する（`type_of_expr_Call`）
- 型サイズに応じてロード・ストア命令を選ぶ（`lb`/`lw`/`ld`、`sb`/`sw`/`sd`）
- `char` の昇格と、代入・固定引数・戻り値での縮小
- 宣言とパラメータを型付きで確保する

戻り値型と固定仮引数型を集める`collect_function_returns(prog)`、その呼出し、
char変換の`_convert_to(ty)`、条件式の共通型を求める`type_of_expr_Cond`は提供済み。
学習者は表から呼出し式の型を取得し、自分のコマ6の呼出し処理とコマ4のreturn処理へ
固定仮引数型・戻り値型への変換を加える。可変長部は縮小しない。
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
