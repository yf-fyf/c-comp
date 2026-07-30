# OCaml 参考実装

このディレクトリには、コマ2〜16 の各回の完成形に相当する OCaml 版実装をまとめて置いている。
Python 実装に詰まったときに、別言語での書き方と比較するための言語横断ヒントである。

- `komaNN.ml`: コマ NN の正解に相当する OCaml 実装
- `support/`: 全回で共通のフロントエンド（Lexer / Parser / AST 定義 / 前処理）

**完成相当の実装を含む。** Python 版をそのまま写すためではなく、
自分の方針を考えた後に、AST の場合分け・状態管理・コード生成の流れを確認するために使う。
まず各回の `mycc.py` の TODO を自分で検討してから参照すること。

## 前提

- dune 3.19 以降
- menhir（`opam install dune menhir` で導入できる）

## ビルド

```bash
cd workbook/ocaml
dune build
```

## 実行例

各回の実行ファイルは `komaNN.exe` という名前でビルドされる。
入力には各回の `sessions/NN_xxx/tests/` の C ファイルをそのまま使える。

```bash
cd workbook/ocaml

# コマ2: インタープリター
dune exec ./koma02.exe -- ../sessions/02_interpreter/tests/add_mul.c

# コマ4: 変数・代入
dune exec ./koma04.exe -- ../sessions/04_variables/tests/target.c

# コマ16: 統合版（final/tests も入力にできる）
dune exec ./koma16.exe -- ../final/tests/f01_arith.c
```

## 出力アセンブリのコメント（コマ16）

`koma16.exe` は、どの命令をどの生成関数が出したのかを示すコメントを付けて出力する。

```asm
# ── i = 1;  [gen_stmt: ExprStmt]
  addi a0, s0, -24           # codegen_lval: Var "i"
  addi sp, sp, -8            # push_a0: a0 をスタックへ退避
  sd a0, 0(sp)
  li a0, 1                   # codegen: Num 1
  ld a1, 0(sp)               # pop_into: 退避した値を a1 へ戻す
  addi sp, sp, 8
  sw a0, 0(a1)               # store: a1 のアドレスへint（4 バイト）を書く
```

- `# ──` の行が**文の見出し**である。元の C をそのまま切り出して出す。
  入れ子の文は字下げが1段深くなる
- 行末の注記は、その行を出した**生成関数と AST ノード**である。
  担当が変わった行にだけ付くので、注記のない行は直前の行と同じ関数が出している
- 関数名（`codegen` / `codegen_lval` / `gen_stmt` / `gen_func`）は Python 版
  `mycc.py` と同じなので、そのまま読み替えられる。ただし**コメントを出すのは
  OCaml 版のコマ16 だけ**である

素のアセンブリが欲しいときは `--no-comments` を付ける。発展課題で生成結果を
行単位に書き換える場合はこちらを使う。

```bash
dune exec ./koma16.exe -- --no-comments ../final/tests/f01_arith.c
```

## テスト

各回の実装を、対応する `sessions/NN_xxx/tests/` に一括で掛けられる。
テストケースの規約（`.ans` / `.stdout` / `.files`）は Python 版と同じ。

```bash
cd workbook/ocaml
dune build
python3 run_tests.py           # 全回
python3 run_tests.py 13        # コマ13 だけ
python3 run_tests.py -q        # PASS を伏せて失敗だけ見る
```

コマ3 以降は `riscv64-linux-gnu-gcc` と `qemu-riscv64` が必要である
（無い場合は `docker/rv64/run.sh` 経由で実行する）。
コマ2 はインタープリターなので、`評価結果:` の印字を `.ans` と比べる。

## コマ番号と対応するテーマ

| 実装 | 対応するコマ | テーマ |
|------|--------------|--------|
| `koma02.ml` | 02_interpreter | AST インタープリター |
| `koma03.ml` | 03_arithmetic_codegen | 算術式のコード生成 |
| `koma04.ml` | 04_variables | 変数・代入・シンボルテーブル |
| `koma05.ml` | 05_if_else | if / else |
| `koma06.ml` | 06_loops | while / for / break / continue |
| `koma07.ml` | 07_functions_abi | 再帰的な変数宣言収集 |
| `koma08.ml` | 08_functions_recursion | 関数呼び出し・再帰 |
| `koma09.ml` | 09_lvalue_rvalue | lvalue / rvalue と `&` / `*` |
| `koma10.ml` | 10_types_pointers | 型・ポインタ演算・配列 |
| `koma11.ml` | 11_strings_printf | 文字列リテラル・`printf` |
| `koma12.ml` | 12_struct | struct / typedef / `.` / `->` |
| `koma13.ml` | 13_sizeof_malloc_list | `sizeof` / `malloc` / 連結リスト |
| `koma14.ml` | 14_globals_scope | グローバル変数・スコープ |
| `koma15.ml` | 15_preprocess_multifile | 前処理・複数ファイル |
| `koma16.ml` | 16_integrate_mycc | 統合版（全機能） |
