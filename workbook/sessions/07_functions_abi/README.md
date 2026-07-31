# コマ7: 再帰的な変数宣言収集

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/07_functions_abi/](https://yf-fyf.github.io/c-comp/sessions/07_functions_abi/) にあります。

## 今日のゴール

関数本体を1つの `Block` ノードとして一様に扱い、宣言収集を AST の再帰走査として書き直す。新しいC構文の追加はない。

## 実装する主な機能

- `collect_decls()` を `Block` / `If` / `While` / `For` の内側まで降りる再帰走査に拡張する
- `_emit_func_body` が関数本体全体（`Block` ノード）を `gen_stmt()` に渡す形にそろえる
- 宣言はファイルスコープと関数本体先頭にしか書けないという言語仕様を前提に、`Decl` を取りこぼさない一般形にする

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/07_functions_abi
```
