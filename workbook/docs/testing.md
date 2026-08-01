# テストの走らせ方

`scaffold/test_runner.py` の使い方とテストケースの形式。

---

## 基本

`workbook/` から実行する。

```bash
# 各回のテスト（その回の mycc.py と tests/ を使う）
python3 scaffold/test_runner.py sessions/03_arithmetic_codegen
python3 scaffold/test_runner.py sessions/06_loops

# 最終統合版（引数を省略すると final/mycc.py + final/tests/）
python3 scaffold/test_runner.py
```

出力例:

```text
[PASS] sessions/06_loops/tests/for_count.c
[FAIL: exit code expected=55 got=0] sessions/06_loops/tests/while_sum.c

=============================
  PASS: 7  FAIL: 1  SKIP: 0
=============================
```

`SKIP` は `.ans`（期待する終了コード）が無いファイルである。
コマ15 の `math_util.c` / `stat_lib.c` のように、**単体では実行せず他のテストと一緒に
コンパイルする補助ソース**がこれに当たるので、ここに出るのは正常である。

一方、発展課題の `check.py` が出す `SKIP` は**未実装**を意味する。
そちらは SKIP が残っている間は完了条件を満たさず、終了コードも 0 にならない。

## コンパイラとテストを個別に指定する

```bash
python3 scaffold/test_runner.py --compiler final/mycc.py --tests final/tests
```

発展課題ではラッパー経由で走らせることが多い。

```bash
# 最適化パスを差し込んだコンパイラで fixed17 を通す
python3 scaffold/test_runner.py --compiler advanced/optcc.py --tests final/tests
```

## テストケースの形式

入力 C ファイルと期待結果ファイルの組で構成する。

```text
foo.c       # 入力ソース
foo.ans     # 期待する exit code
foo.stdout  # 期待する標準出力（必要な場合のみ）
foo.files   # 一緒にコンパイルする追加ソース（複数ファイル構成の場合のみ）
```

例:

```text
sessions/06_loops/tests/while_sum.c
sessions/06_loops/tests/while_sum.ans
sessions/11_strings_printf/tests/printf_hello.stdout
final/tests/f01_arith.c
final/tests/f01_arith.ans
```

`.ans` は終了コードで結果を確認するため、値は 0〜255 に収める。
テストケース側で未定義動作（UB）に踏み込まないようにする。

### `.files`（複数ファイルのテスト）

`foo.files` があると、`foo.c` に加えてそこに列挙したファイルもコンパイル対象に含める。
1行に1ファイル名で、パスは `foo.c` と同じディレクトリからの相対で書く。

```text
sessions/15_preprocess_multifile/tests/multifile_global.files:
stat_lib.c
```

`stat_lib.c` 自身には対応する `.ans` が無い。**単体では実行せず他のテストと
一緒にコンパイルされる補助ソース**であり、テストランナーが直接 `stat_lib.c` を
拾ったときは `.ans` が無いので `SKIP` になる（前述のとおり正常な挙動）。

## `final/tests`（fixed17）

コマ1〜16（07 は欠番）の機能をまとめて確認する17本のテスト。
**標準トラック完成の目安**であり、発展課題では「意味を壊していないこと」の安全網として使う。

発展課題に取り組むときは、変更を入れたあと毎回これを通すこと。

## 手で1本だけ確認する

テストランナーを使わず、生成アセンブリを目で見たいときの手順。

```bash
python3 sessions/03_arithmetic_codegen/mycc.py test.c > out.s
riscv64-linux-gnu-gcc -x assembler -static out.s -o out
qemu-riscv64 ./out; echo $?
```

パイプでつなぐこともできる。

```bash
python3 final/mycc.py test.c \
  | riscv64-linux-gnu-gcc -x assembler -static - -o out
qemu-riscv64 ./out; echo $?
```

落ちたときの調べ方は [`debugging.md`](./debugging.md) を参照。

## AST を確認する

コンパイル結果ではなく、Parser が返した AST を見たいとき。

```bash
python3 scaffold/parse_viewer.py sessions/02_interpreter/tests/add_mul.c
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --tokens
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --format tree
python3 scaffold/parse_viewer.py sessions/03_arithmetic_codegen/tests/add.c --format dot > ast.dot
```

## 発展課題のテスト

各トピックのディレクトリから実行する。

```bash
python3 check.py     # ステップごとの確認
python3 golden.py    # 存在し、README で指定されている場合
```

トピックによって専用のコマンドがあるので、対象の `README.md` を確認すること。
