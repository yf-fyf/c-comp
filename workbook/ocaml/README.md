# OCaml 参考実装

このディレクトリには、コマ2〜16 の各回の完成形に相当する OCaml 版実装をまとめて置いている。
Python 実装に詰まったときに、別言語での書き方と比較するための言語横断ヒントである。

- `sessions/komaNN.ml`: コマ NN の正解に相当する OCaml 実装
- `reference/`: 必修パート（コマ2〜16）の完成版リファレンス実装。
  **生成されるアセンブリは koma16 と同一である**（テストで担保している）が、
  実装は OCaml らしい設計で書き直した別実装であり、どの命令をどの生成関数が
  出したかを示すアセンブリコメントを付けられる
- `support/`: 全回で共通のフロントエンド（Lexer / Parser / AST 定義 / 前処理）

### `reference/` の構成

| ファイル | 役割 |
|----------|------|
| `asm.ml` | レジスタ・命令・ラベル・ディレクティブを表す型と、その印字。文字列を組み立てるのはここだけ |
| `emitter.ml` | 注記つきの行バッファ。「同じ担当の注記は繰り返さない」「命令が出なかった見出しは捨てる」といった見せ方の規則を印字時にまとめて適用する |
| `codegen.ml` | コンパイラ本体。状態はグローバル変数ではなく `genv`（プログラム全体）と `fenv`（関数 1 個）のレコードを引数で持ち回る |
| `mycc_ref.ml` | コマンドライン・パース・駆動のみ |

主要な関数名（`codegen` / `codegen_lval` / `gen_stmt` / `gen_func`）と走査の順番は、
Python 版 `mycc.py` および `sessions/koma16.ml` と対応させたままである。
違うのは状態の持ち方（`gen_func` は `fenv` を作り直すだけで、手動リセットが要らない）と、
出力を型で表していること、エラーがその場の `exit` ではなく例外であることである。

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

各回の実行ファイルは `sessions/komaNN.exe` という名前でビルドされる。
入力には各回の `../sessions/NN_xxx/tests/`（workbook/sessions/、こちらは Python 版の教材ディレクトリ）
の C ファイルをそのまま使える。

```bash
cd workbook/ocaml

# コマ2: インタープリター
dune exec sessions/koma02.exe -- ../sessions/02_interpreter/tests/add_mul.c

# コマ4: 変数・代入
dune exec sessions/koma04.exe -- ../sessions/04_variables/tests/target.c

# コマ16: 統合版（final/tests も入力にできる）
dune exec sessions/koma16.exe -- ../final/tests/f01_arith.c
```

## 出力アセンブリのコメント（mycc_ref）

`mycc_ref.exe` は、どの命令をどの生成関数が出したのかを示すコメントを付けて出力する。
コメントを外した出力（`--no-comments`）は `koma16.exe` の出力とバイト単位で同じである。

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
  OCaml 版の `mycc_ref` だけ**であり、`koma16.exe` 自体はコメントなしで出力する

素のアセンブリが欲しいときは `--no-comments` を付ける。発展課題で生成結果を
行単位に書き換える場合はこちらを使う。

```bash
dune exec reference/mycc_ref.exe -- --no-comments ../final/tests/f01_arith.c
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

各回のテストに加えて、**等価性テスト**（`koma16.exe` の出力 ==
`mycc_ref.exe --no-comments` の出力）を全テストソースに掛ける。
`reference/` を書き換えても生成コードが変わっていないことは、これで担保している
（切りたいときは `--no-equivalence`）。

コマ3 以降は `riscv64-linux-gnu-gcc` と `qemu-riscv64` が必要である
（無い場合は `docker/rv64/run.sh` 経由で実行する）。
コマ2 はインタープリターなので、`評価結果:` の印字を `.ans` と比べる。

## コマ番号と対応するテーマ

| 実装 | 対応するコマ | テーマ |
|------|--------------|--------|
| `sessions/koma02.ml` | 02_interpreter | AST インタープリター |
| `sessions/koma03.ml` | 03_arithmetic_codegen | 算術式のコード生成 |
| `sessions/koma04.ml` | 04_variables | 変数・代入・シンボルテーブル |
| `sessions/koma05.ml` | 05_if_else | if / else |
| `sessions/koma06.ml` | 06_loops | while / for / break / continue |
| `sessions/koma07.ml` | 07_functions_abi | 再帰的な変数宣言収集 |
| `sessions/koma08.ml` | 08_functions_recursion | 関数呼び出し・再帰 |
| `sessions/koma09.ml` | 09_lvalue_rvalue | lvalue / rvalue と `&` / `*` |
| `sessions/koma10.ml` | 10_types_pointers | 型・ポインタ演算 |
| `sessions/koma11.ml` | 11_strings_printf | 文字列リテラル・`printf` |
| `sessions/koma12.ml` | 12_struct | struct / `.` / `->` |
| `sessions/koma13.ml` | 13_sizeof_malloc_list | `sizeof` / `malloc` / 連結リスト |
| `sessions/koma14.ml` | 14_globals_scope | グローバル変数・スコープ |
| `sessions/koma15.ml` | 15_preprocess_multifile | 前処理・複数ファイル |
| `sessions/koma16.ml` | 16_integrate_mycc | 統合版（全機能） |
