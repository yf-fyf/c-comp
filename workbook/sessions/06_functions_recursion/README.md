# コマ6: 関数呼び出し・再帰

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/06_functions_recursion/](https://yf-fyf.github.io/c-comp/sessions/06_functions_recursion/) にあります。

## 今日のゴール

ユーザー定義関数の定義・呼び出し・再帰呼び出しを実装する。引数の受け渡し、関数呼び出し `call`、戻り値の受け取り、再帰呼び出しを正しく生成できるようにする。

## 実装する主な機能

- 関数定義・関数宣言（プロトタイプ）を扱う
- 引数の受け渡しと `call` によるRV64関数呼び出しをコード生成する
- 再帰呼び出し・相互再帰を正しく動作させる
- 最大8個までの引数を持つ関数呼び出しに対応する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/06_functions_recursion
```
