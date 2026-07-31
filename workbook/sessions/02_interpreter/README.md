# コマ2: AST + インタープリター

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/02_interpreter/](https://yf-fyf.github.io/c-comp/sessions/02_interpreter/) にあります。

## 今日のゴール

提供 Lexer/Parser が返す AST を走査し、`eval_ast()` で式を評価する。
この回では RV64 アセンブリは出力しない。`main` 関数の中にある `return 式;` の「式」だけを評価する。

## 実装する主な機能

- `eval_ast(node)` で AST を再帰的に評価する
- 整数リテラル・単項マイナスを評価する
- 四則演算（`+` `-` `*` `/`）と剰余 `%` を評価する
- カッコで囲まれた式を評価する

## 編集するファイル

- `mycc.py` の `eval_ast(node)`。`run_main()` は提供済みであり、変更しない。

## テスト

```bash
python3 sessions/02_interpreter/check.py
```

実装に詰まった場合は、[`../../ocaml/README.md`](../../ocaml/README.md) から別言語の参考実装を確認できる。完成相当の実装を含むため、まずPython版のTODOを自分で検討してから参照すること。
