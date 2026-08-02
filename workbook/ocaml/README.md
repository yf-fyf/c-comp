# OCaml 参考実装

このディレクトリには、コマ2〜16 の各回の完成形に相当する OCaml 版実装をまとめて置いている。
Python 実装に詰まったときに、別言語での書き方と比較するための言語横断ヒントである。

- `sessions/lectureNN.ml`: コマ NN の正解に相当する OCaml 実装
- `reference/`: 必修パート（コマ2〜16）の完成版リファレンス実装。
  **生成されるアセンブリは lecture16 と同一である**（テストで担保している）が、
  実装は OCaml らしい設計で書き直した別実装であり、どの命令をどの生成関数が
  出したかを示すアセンブリコメントを付けられる
- `support/`: `sessions/` 全回で共通のフロントエンド（Lexer / Parser / AST 定義 / 前処理）。
  `reference/` が借りるのは前処理だけで、字句解析・構文解析・構文木は自前で持つ

### `reference/` の構成

`sessions/` とは別に、自分専用のフロントエンド（字句解析・構文解析・構文木）を持つ。
`support/` から借りるのは前処理（`Preprocess`）とファイル読み込み（`Utils`）だけである。

| ファイル | 役割 |
|----------|------|
| `loc.ml` / `ctype.ml` / `diag.ml` | 位置・型・エラーという、どこからも使われる土台 |
| `ast.ml` + `lexer.mll` / `parser.mly` | 構文木と、それを作る字句解析・構文解析。構文の形をそのまま写す |
| `parser.messages` | 構文エラーの状態ごとの日本語メッセージ（下記「構文エラーメッセージの保守」） |
| `layout.ml` | 型の大きさ・整列と struct のレイアウト。表は不変な Map |
| `strings.ml` | 文字列リテラルの通し番号（`.LC`）。採番の規則はここだけに書いてある |
| `tast.ml` / `typing.ml` | 型付き木と、それを作るパス。型・変数の置き場・フィールドの変位・ポインタ演算のスケールをここで決め、エラーもここで出す |
| `asm.ml` | レジスタ・命令・ラベル・ディレクティブを表す型と、その印字。文字列を組み立てるのはここだけ |
| `emitter.ml` | 注記つきの行バッファ。「同じ担当の注記は繰り返さない」「命令が出なかった見出しは捨てる」といった見せ方の規則を印字時にまとめて適用する |
| `codegen.ml` | 型付き木をなぞって命令を出す。型も変数も決まった後なので、場合分けは「どの順に命令を出すか」だけ |
| `compile.ml` / `mycc_ref.ml` | 駆動（前処理 → 構文解析 → 型付け → コード生成）と、コマンドラインの解釈 |

Python 版 `mycc.py` と `sessions/lecture16.ml` は、コード生成をしながらその場で型を計算する。
こちらは **型付けを独立したパスに分けてある**のが最大の違いで、`codegen.ml` には
型の計算も変数表もない（`typing.ml` が済ませている）。生成関数の名前
（`codegen` / `codegen_lval` / `gen_stmt` / `gen_func`）と命令を出す順番は
`mycc.py` に合わせてあるので、そこは読み替えられる。
状態の持ち方も違い、グローバルな可変変数ではなく `genv`（プログラム全体）と
`fenv`（関数 1 個）を引数で持ち回るので、手動のリセットが要らない。

**完成相当の実装を含む。** Python 版をそのまま写すためではなく、
自分の方針を考えた後に、AST の場合分け・状態管理・コード生成の流れを確認するために使う。
まず各回の `mycc.py` の TODO を自分で検討してから参照すること。

### 構文エラーメッセージの保守（`reference/parser.messages`）

`compile.ml` の `parse` は menhir の incremental API（`--table` で生成される
`Parser.MenhirInterpreter`）で構文解析する。エラーになったときは構文解析器の**状態番号**が
取れるので、その番号で `parser.messages` を引き、「ここには X か Y が来るはず」という
日本語メッセージを出す。載っていない状態は汎用の 1 文に落ちる。

**`parser.mly` の文法を変えたら `parser.messages` の更新が必要である。**
状態番号は文法から機械的に決まるので、規則を 1 つ足しただけでも番号がずれ、
既存のメッセージが別の状態に付いてしまう。手順は次のとおり。

```bash
cd workbook/ocaml/reference
tmp=$(mktemp -d)

# 1. 既存のメッセージを新しい状態番号・新しい自動コメントへ移す
menhir --update-errors parser.messages parser.mly > "$tmp/updated.messages"

# 2. 文法が増えて新しく現れたエラー状態を、空メッセージ付きで足す
menhir --list-errors parser.mly > "$tmp/auto.messages"
menhir parser.mly --merge-errors "$tmp/auto.messages" \
                  --merge-errors "$tmp/updated.messages" > "$tmp/merged.messages"

mv "$tmp/merged.messages" parser.messages
```

ずれや抜けの検査は dune から回せる。

```bash
cd workbook/ocaml
dune build @reference/check-messages   # 文法から生成した一覧と parser.messages を突き合わせる
```

このチェックが落ちたら、上の手順で `parser.messages` を作り直し、
新しく現れた状態には日本語のメッセージを書く。メッセージは
「その状態で実際に受理されうるトークン」を具体的に挙げること
（`menhir --list-errors` が各状態の LR(1) 項目を併記するので、それを見て書く）。

## 前提

- dune 3.19 以降
- menhir（`opam install dune menhir` で導入できる）

## ビルド

```bash
cd workbook/ocaml
dune build
```

## 実行例

各回の実行ファイルは `sessions/lectureNN.exe` という名前でビルドされる。
入力には各回の `../sessions/NN_xxx/tests/`（workbook/sessions/、こちらは Python 版の教材ディレクトリ）
の C ファイルをそのまま使える。

```bash
cd workbook/ocaml

# コマ2: インタープリター
dune exec sessions/lecture02.exe -- ../sessions/02_interpreter/tests/add_mul.c

# コマ4: 変数・代入
dune exec sessions/lecture04.exe -- ../sessions/04_variables/tests/target.c

# コマ16: 統合版（final/tests も入力にできる）
dune exec sessions/lecture16.exe -- ../final/tests/f01_arith.c
```

## 出力アセンブリのコメント（mycc_ref）

`mycc_ref.exe` は、どの命令をどの生成関数が出したのかを示すコメントを付けて出力する。
コメントを外した出力（`--no-comments`）は `lecture16.exe` の出力とバイト単位で同じである。

```asm
# ── i = 1;  [gen_stmt: Expr]
  addi a0, s0, -24           # codegen_lval: Var "i"
  addi sp, sp, -8            # push_a0: a0 をスタックへ退避
  sd a0, 0(sp)
  li a0, 1                   # codegen: Const 1
  ld a1, 0(sp)               # pop_into: 退避した値を a1 へ戻す
  addi sp, sp, 8
  sw a0, 0(a1)               # store: a1 のアドレスへint（4 バイト）を書く
```

- `# ──` の行が**文の見出し**である。元の C をそのまま切り出して出す。
  入れ子の文は字下げが1段深くなる
- 行末の注記は、その行を出した**生成関数と木のノード**である。
  担当が変わった行にだけ付くので、注記のない行は直前の行と同じ関数が出している
- 関数名（`codegen` / `codegen_lval` / `gen_stmt` / `gen_func`）は Python 版
  `mycc.py` と同じなので、そのまま読み替えられる。一方**ノードの名前は型付き木のもの**で、
  Python 版の `ND_*` とは一対一ではない（`Num` は `Const`、変数の読み出しは
  `Rval Var "i"`、ポインタ加算は `PtrAdd` のように、型付けで決まった形が出る）
- **コメントを出すのは OCaml 版の `mycc_ref` だけ**であり、`lecture16.exe` 自体は
  コメントなしで出力する

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

各回のテストに加えて、**等価性テスト**（`lecture16.exe` の出力 ==
`mycc_ref.exe --no-comments` の出力）を全テストソースに掛ける。
`reference/` を書き換えても生成コードが変わっていないことは、これで担保している
（切りたいときは `--no-equivalence`）。`.text` は 1 行の違いも許さないが、
`.data` と `.bss` だけはラベル単位に並べ替えてから比べる。どの順に置くかは実装の自由で、
`lecture16.exe` は表の走査順、`mycc_ref.exe` は定義順に出すためである。

続けて**拒否側のテスト**も回る。`reference/` は `support/` とは別に文法定義を持つので、
正しいプログラムの出力が一致するだけでは「同じ言語を受理する」ことの片側しか確かめられない。
受理してはいけない入力（`int main(void)`、入れ子ブロックでの宣言、ループの外の `break` など）を
両方に掛けて、揃って拒否することを見る。

コマ3 以降は `riscv64-linux-gnu-gcc` と `qemu-riscv64` が必要である
（無い場合は `docker/rv64/run.sh` 経由で実行する）。
コマ2 はインタープリターなので、`評価結果:` の印字を `.ans` と比べる。

## コマ番号と対応するテーマ

`lectureNN.ml` は累積で、その回までに実装した機能をすべて含む。

| 実装 | 対応するコマ | テーマ |
|------|--------------|--------|
| `sessions/lecture02.ml` | 02_interpreter | AST インタープリター |
| `sessions/lecture03.ml` | 03_arithmetic_codegen | 算術式のコード生成 |
| `sessions/lecture04.ml` | 04_variables | 変数・代入・シンボルテーブル |
| `sessions/lecture05.ml` | 05_if_else | if / else |
| `sessions/lecture06.ml` | 06_loops | while / for / break / continue |
| `sessions/lecture07.ml` | 07_functions_recursion | 関数呼び出し・再帰 |
| `sessions/lecture08.ml` | 08_lvalue_rvalue | lvalue / rvalue と `&` / `*` |
| `sessions/lecture09.ml` | 09_types | 型表・型別 load/store・`char` の昇格と縮小 |
| `sessions/lecture10.ml` | 10_pointer_arith | ポインタ演算・添字・`sizeof(型名)` |
| `sessions/lecture11.ml` | 11_strings_data_section | 文字列リテラル・`.data`・`printf` の基本形 |
| `sessions/lecture12.ml` | 12_expr_walk_libc | 式の走査・`lib.h` の残りの外部関数 |
| `sessions/lecture13.ml` | 13_struct_malloc_list | struct / `.` / `->` / `sizeof` / `malloc` / 連結リスト |
| `sessions/lecture14.ml` | 14_globals_scope | グローバル変数・スコープ |
| `sessions/lecture15.ml` | 15_preprocess_multifile | 前処理・複数ファイル |
| `sessions/lecture16.ml` | 16_integrate_mycc | 統合版（全機能） |
