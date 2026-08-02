# テストとデバッグ

`scaffold/test_runner.py` の使い方とテストケースの形式、
そして落ちたときに原因を絞り込む手順。

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

落ちたときの調べ方は、後半の[「症状から当たりをつける」](#症状から当たりをつける)を参照。

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

---

## デバッグの基本手順

動かないときは、複雑な入力をそのまま追わず、**小さい入力に戻す**。

1. 失敗したテストを単体で確認する
2. 生成アセンブリをファイルに保存して読む
3. qemu の終了コードを確認する
4. 関数呼び出しで壊れる場合は `ra`、`s0`、スタックアラインメントを見る
5. ポインタで壊れる場合は `codegen()` と `codegen_lval()` の区別を見る

```bash
python3 sessions/03_arithmetic_codegen/mycc.py sessions/03_arithmetic_codegen/tests/add.c > out.s
riscv64-linux-gnu-gcc -x assembler -static out.s -o out
qemu-riscv64 ./out; echo $?
```

## 症状から当たりをつける

| 症状 | よくある原因 | 見るところ |
|------|-------------|-----------|
| `FAIL: compile — NotImplementedError: …` | その回の TODO が残っている | メッセージが指す関数を実装する。全文が要るなら `python3 sessions/NN_xxx/mycc.py <入力.c>` を直接実行する |
| `FAIL: assemble — …` | 出力したアセンブリが構文として通らない | 生成結果をファイルに保存して該当行を見る（`python3 … > out.s`） |
| `Illegal instruction` / `Bus error` | スタックアラインメント違反（16バイト境界） | `align_to(n, 16)` を通しているか。`call` 直前の `sp` も対象で、そのとき積んでいる一時値が奇数個ならずれている（[`rv64_reference.md`](./rv64_reference.md)） |
| 終了コードが 0 になる | `return` の値が `a0` に残っていない | 最後の `codegen()` のあとで `a0` を上書きしていないか |
| 期待値と 256 ずれる | 終了コードは 0〜255 | テスト側の期待値を見直す |
| 関数から戻ると壊れる | `ra` / `s0` の退避漏れ、フレームサイズの計算違い | プロローグとエピローグが対称か |
| 再帰の途中で壊れる | 引数の退避漏れ（`a0`–`a7` は caller-saved） | 再帰呼び出しの前後で引数を保存しているか |
| ポインタ経由の代入が効かない | `codegen()` と `codegen_lval()` の混同 | `*p = v;` の左辺は `codegen_lval()` |
| 配列の添字がずれる | ポインタ演算で要素サイズを掛けていない | `size_of_ty_str()` / `elem_ty_str()` を通しているか |
| 未定義変数で黙って動く | シンボルテーブルの探索順序 | `_locals` → `_globals` の順に引いているか |
| `AttributeError: … has no attribute '_continue_stack'` / `'_align_to'` / `'align_to'` | 2026-08-01 より前に取得したファイルと後のファイルが混ざっている | 回ごとのスケルトンは前の回を継承するので、一部だけ差し替えると壊れる。取得時期の違うファイルを混ぜず、まとめて取り直す（移行手順は担当教員から受け取る） |
| 最適化をかけたのに命令数が変わらない（発展課題） | 環境変数が旧名のままで黙って無視されている | [発展課題の「環境変数の名前」](../advanced/README.md#環境変数の名前)の規則と突き合わせる |
| AST の構造が分からない（優先順位・結合の向き） | 目視では判断しづらい | [AST ビジュアライザ](../../tools/ast.html) にソースを貼って構文木と S 式を確認する |
| 生成されたアセンブリの動きを目で追いたい | 静的に読むだけでは1命令ごとのレジスタ・スタックの変化が分からない | [RV64 シミュレータ](../../tools/sim.html) にアセンブリを貼って1命令ずつ実行する |

## アセンブリを読むときの順序

1. `.globl` とラベルが期待どおり出ているか
2. プロローグでフレームサイズが正しいか
3. 問題の式だけを追う（値が `a0` に残るか、アドレスが `a0` に残るか）
4. エピローグがプロローグと対称か

## gdb でステップ実行する

終了コードだけでは原因が分からないときに使う。

```bash
# qemu をデバッグサーバとして起動
qemu-riscv64 -g 1234 ./out

# 別のターミナルで gdb を繋ぐ
gdb-multiarch ./out
(gdb) target remote :1234
(gdb) break main
(gdb) stepi
(gdb) info registers a0 sp s0 ra
```

`Illegal instruction` の発生箇所を特定するときは、止まった時点の `sp` が
16 の倍数になっているかを確認する。
