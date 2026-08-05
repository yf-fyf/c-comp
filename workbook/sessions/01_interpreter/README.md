# コマ1: AST + インタープリター

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/01_interpreter/](https://yf-fyf.github.io/c-comp/sessions/01_interpreter/) にあります。

## 今日のゴール

提供 Lexer/Parser が返す AST を走査し、`eval_ast()` で式を評価する。
この回では RV64 アセンブリは出力しない。`main` 関数の中にある `return 式;` の「式」だけを評価する。

## スキャフォールドの動作確認

実装に入る前に、教員提供の Lexer/Parser が AST を正しく構築できることを確認する。

```bash
python3 scaffold/parse_viewer.py sessions/01_interpreter/tests/add_mul.c
```

次のようなS式が表示されれば成功。

```lisp
(program
  (funcdef "main" :type int (params)
    (block
      (return
        (add (num 1)
          (mul (num 2) (num 3)))))))
```

`1 + 2 * 3` が `(add (num 1) (mul (num 2) (num 3)))` のように、掛け算が先にまとめられている（演算子の優先順位が正しく反映されている）ことを確認する。

S 式ではなく木の形で見たいときは、[AST ビジュアライザ](../../tools/app.html?mode=build) に同じソースを貼るとブラウザ上に構文木が表示される。

## 実装する主な機能

- 提供 Lexer/Parser が返す AST を `parse_viewer.py` で確認する
- `eval_ast(node)` で AST を再帰的に評価する
- 整数リテラル・単項マイナスを評価する
- 四則演算（`+` `-` `*` `/`）と剰余 `%` を評価する
- カッコで囲まれた式を評価する

## 編集するファイル

- `mycc.py` の `eval_ast(node)`。`run_main()` は提供済みであり、変更しない。

## テスト

> - `workbook/` から実行する。
> - 前回までのテストが全通していることを前提とする。
> - FAIL したら、まず最初の失敗ケースを単体で確認する。詳しい手順は [`docs/testing.md`](../../docs/testing.md) を参照。

```bash
python3 sessions/01_interpreter/check.py
```

実装に詰まった場合は、[`../../ocaml/README.md`](../../ocaml/README.md) から別言語の参考実装を確認できる。完成相当の実装を含むため、まずPython版のTODOを自分で検討してから参照すること。
