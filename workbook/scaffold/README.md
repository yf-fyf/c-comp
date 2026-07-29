# scaffold

教員提供の共通部品を置く。
標準トラックでは Lexer/Parser は基本的に黒箱として扱い、学生は主にコード生成を実装する。

## 主なファイル

- `lexer.py`: C サブセットの字句解析と簡易前処理
- `parser.py`: トークン列から AST を構築する
- `ast_def.py`: AST ノード・定数定義
- `parse_viewer.py`: Parser の構文解析結果を表示する学習用ツール
- `lib.h`: `printf` や `malloc` などの宣言
- `test_runner.py`: テスト実行スクリプト

## Parser 表示ツール

`parse_viewer.py` は、入力 C ファイルを字句解析・構文解析し、Parser が返す AST を表示する。
デフォルト表示は S-expression 形式。

```bash
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --tokens
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --format tree
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --format json
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --format dot > ast.dot
dot -Tpng ast.dot -o ast.png
```

S-expression では、変数名・関数名などの文字列値は double quotation 付きで表示し、型は構造化して表示する。

```lisp
(decl "p" :type (ptr int))
(decl "arr" :type (array int 10))
```

## テストランナー

```bash
python3 scaffold/test_runner.py sessions/03_arithmetic_codegen
python3 scaffold/test_runner.py
```
