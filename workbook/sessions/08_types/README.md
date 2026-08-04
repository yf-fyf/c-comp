# コマ8: 型検査の導入

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/08_types/](https://yf-fyf.github.io/c-comp/sessions/08_types/) にあります。

## 今日のゴール

`int`・`char`・ポインタの型をコンパイラが覚えるようにし、型サイズに応じてロード・ストア命令を選ぶ。

## 実装する主な機能

- ローカル変数表に型を持たせる（`name → (offset, ty_str)`）
- 式と左辺値の型を求める（`type_of_expr_*` / `type_of_lval_*`）
- 型サイズに応じてロード・ストア命令を選ぶ（`lb`/`lw`/`ld`、`sb`/`sw`/`sd`）
- `char` の昇格（読み出しで int へ）と縮小（代入で下位 8 ビットへ）
- 宣言とパラメータを型付きで確保する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/08_types
```
