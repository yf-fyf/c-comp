# コマ14: グローバル変数・スコープ管理

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/14_globals_scope/](https://yf-fyf.github.io/c-comp/sessions/14_globals_scope/) にあります。

## 今日のゴール

グローバル変数とローカル変数を混在させたプログラムを動かす。

## 実装する主な機能

- トップレベルの変数宣言をグローバル変数として登録する
- 未初期化グローバル変数を `.bss` に出力する
- 初期値付きグローバル変数を `.data` に出力する
- 変数探索を `self._locals` → `self._globals` の順にする（ローカルがグローバルを隠す）
- グローバル変数の lvalue を `la a0, name` で生成する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/14_globals_scope
```
