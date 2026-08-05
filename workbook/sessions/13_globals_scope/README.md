# コマ13: グローバル変数・スコープ管理

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/13_globals_scope/](https://yf-fyf.github.io/c-comp/sessions/13_globals_scope/) にあります。

## 今日のゴール

グローバル変数とローカル変数を混在させたプログラムを動かす。

## 実装する主な機能

- トップレベルの変数宣言をグローバル変数として登録する
- グローバル変数を `.bss` に出力する（初期化子は書けず、全て 0 初期化される）
- 変数探索を `self._locals` → `self._globals` の順にする（ローカルがグローバルを隠す）
- グローバル変数の lvalue を `la a0, name` で生成する
- 論理否定 `!`・論理積 `&&`・論理和 `||` を実装する（`&&` `||` は**短絡評価をしない**。左辺の値にかかわらず右辺も必ず評価する）

## 編集するファイル

- `mycc.py`

## テスト

> - `workbook/` から実行する。
> - 前回までのテストが全通していることを前提とする。
> - FAIL したら、まず最初の失敗ケースを単体で確認する。詳しい手順は [`docs/testing.md`](../../docs/testing.md) を参照。

```bash
python3 scaffold/test_runner.py sessions/13_globals_scope
```
