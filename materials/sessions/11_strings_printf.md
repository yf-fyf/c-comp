# コマ11: 文字列リテラル + printf

## 今日のゴール

文字列リテラルを `.data` セクションに出力し、`printf` 呼び出しを動かす。

コマ10までに、ポインタ、ポインタ演算、関数呼び出し、型サイズを扱えるようになった。
この回では、文字列リテラルをメモリ上に配置し、その先頭アドレスを `char *` として使う。

```c
printf("x=%d\n", 42);
```

上のコードでは、`"x=%d\n"` をプログラム中のデータ領域に置き、そのアドレスを第1引数として `printf` に渡す。

## この回で扱う範囲

対象にする機能は次の通り。

| 種類 | 例 |
|------|----|
| 文字列リテラル | `"hello"` |
| 外部関数呼び出し | `printf("hi\n")` |
| ストリーム操作 | `fdopen` / `fprintf` / `fopen` / `fread` / `fclose` |
| 標準出力テスト | `tests/foo.stdout` |

この回では、`printf` 自体は実装しない。
コンパイル後のアセンブリを `riscv64-linux-gnu-gcc -static` でリンクすると、libc の `printf` が使われる。

## AST を確認する

まず、`printf` と文字列リテラルを含むプログラムがどのような AST になるか確認する。

```bash
python3 scaffold/parse_viewer.py sessions/11_strings_printf/tests/printf_number.c
```

このプログラムの内容は次の通り。

```c
int printf(char *fmt, ...);

int main() {
    printf("x=%d\n", 42);
    return 0;
}
```

実行すると、次のようなS式が表示される。

```lisp
(program
  (funcproto "printf" :type int
    (params (param "fmt" :type (ptr char))))
  (funcdef "main" :type int (params)
    (block
      (exprstmt
        (call "printf"
          (args (str "x=%d\n") (num 42))))
      (return (num 0)))))
```

![`printf_number.c` の AST](figures/ast/11_printf_number_ast.svg)

新しく重要になるノードは `(str "...")` である。
これは `ND_STR` として表され、`node.sval` に文字列の内容が入っている。

## 文字列リテラルはどこに置くか

整数リテラル `42` は、命令中に即値として直接埋め込める。
しかし文字列リテラルは複数バイトのデータなので、命令列の中ではなくデータ領域に置く。

```asm
  .data
.LC1:
  .byte 120    # 'x'
  .byte 61     # '='
  .byte 37     # '%'
  .byte 100    # 'd'
  .byte 10     # '\n'
  .byte 0      # 終端NUL
```

C の文字列は、最後に `0` が入る NUL 終端文字列である。
そのため、文字列本体のバイト列を出した後に `.byte 0` を必ず出力する。

## `.data` と `.text`

アセンブリでは、データと命令をセクションで分ける。

| セクション | 内容 |
|------------|------|
| `.data` | 文字列リテラルなどのデータ |
| `.text` | 実行される命令列 |

出力の形は次のようにする。

```asm
  .data
.LC1:
  .byte ...
  .byte 0

  .text
  .globl main
main:
  ...
```

文字列がないプログラムでも `.text` は必要である。

![`.data` に置いた文字列と、`.text` からの参照](figures/11_sections.svg)

`.text` 側の `la a0, .LC1` が、`.data` に置いた文字列の先頭アドレスを `a0` に入れる。

## 文字列ラベル

各文字列リテラルには、一意なラベルを付ける。

たとえば、`"hello"` に `.LC1`、`"x=%d\n"` に `.LC2` のようなラベルを割り当てる。

Codegen クラスは instance 変数で文字列ラベルを管理する。

```python
# __init__ 内
self._strings: dict[str, str] = {}
self._label_counter = 0
```

同じ文字列が複数回出てきた場合は、同じラベルを再利用してもよい。
実装を単純にするため、`node.sval` をキーにした辞書で管理する。

```python
def _intern(self, s: str) -> str:
    if s not in self._strings:
        self._label_counter += 1
        self._strings[s] = f".LC{self._label_counter}"
    return self._strings[s]
```

## `ND_STR` のコード生成

文字列リテラルを式として評価すると、その文字列の先頭アドレスが得られる。
型は `char *` と考える。

```python
if node.kind == ND_STR:
    label = self._intern(node.sval)
    self.emit(f"  la a0, {label}")
    return
```

`la` は疑似命令で、ラベルのアドレスをレジスタに入れる。
この結果、`a0` に文字列先頭アドレスが入る。

## `printf` 呼び出し

`printf` は普通の関数呼び出しと同じ ABI で呼び出せる。

```c
printf("x=%d\n", 42);
```

この呼び出しでは、引数は次のように渡される。

| 引数 | 内容 |
|------|------|
| `a0` | `"x=%d\n"` の先頭アドレス |
| `a1` | `42` |

コマ8で作った関数呼び出しのコード生成がそのまま使える（`self._gen_call()` または `ND_CALL` ハンドラメソッド）。
新しく必要なのは、`ND_STR` を評価したときに文字列アドレスを `a0` に入れる処理である。

## `#include "lib.h"`

実際のプログラムでは、`printf` の宣言を自分で書く代わりに `lib.h` を include できる。

```c
#include "lib.h"

int main() {
    printf("Hello, World!\n");
    return 0;
}
```

`scaffold/lib.h` には次の宣言が用意されている。

```c
int printf(char *fmt, ...);
```

`...` は可変長引数を表す。
この講義の Parser は外部関数宣言に限って `...` を読み飛ばす。
呼び出し側では、通常の関数呼び出しと同じように引数を左から評価すればよい。

## `lib.h` の残りの関数: ストリーム

`lib.h` には `printf` のほかにストリーム操作の宣言もある。
言語仕様の「標準ライブラリ」節に載っている関数はこれで全部で、
どれも libc にそのままリンクされる。

```c
struct FILE;                                    // 不透明型。中身は見ない
int fprintf(struct FILE *f, char *fmt, ...);
struct FILE *fdopen(int fd, char *mode);
struct FILE *fopen(char *path, char *mode);
int fread(void *buf, int size, int n, struct FILE *f);
int fclose(struct FILE *f);
```

`struct FILE` は**前方宣言だけがあって定義がない**型である。
フィールドを持たないので `.` や `->` は書けず、使い方は `struct FILE *` という
ポインタを受け渡すことに限られる。ポインタのサイズは指し先の中身によらず 8 バイトなので、
構造体そのものを扱えるようになる**コマ12 を待たずにこの回で使える**。
コード生成としては、コマ8 の関数呼び出しとコマ10 の `ty_str` 管理がそのまま働く。

用途は主に 2 つある。

| やりたいこと | 書き方 |
|--------------|--------|
| 標準エラーへ出す | `fdopen(2, "w")` でストリームを作り、そこへ `fprintf` する |
| ファイルを読む | `fopen` → `fread` → `fclose`。`fopen` は失敗すると `NULL` を返す |

残る `exit(code)` は、指定した終了コードでその場でプログラムを終わらせる。
戻ってこないので、`exit` の後に書いた文は実行されない。
これで `lib.h` の宣言は全部使ったことになる（`malloc` はコマ10 で使っている）。

自作コンパイラのエラーメッセージを標準エラーへ出す形は、
発展課題 P1（セルフホスト）で実際に使うことになる。

```c
struct FILE *err;
err = fdopen(2, "w");
fprintf(err, "error: unexpected token\n");
```

## 標準出力テスト

これまでのテストは、主に終了コードを `.ans` で確認してきた。
コマ11では標準出力も確認する。

```text
tests/printf_hello.c
tests/printf_hello.ans
tests/printf_hello.stdout
```

`.ans` には終了コードを書く。
`.stdout` には期待する標準出力をそのまま書く。

たとえば、次のプログラムなら、

```c
printf("Hello, World!\n");
return 0;
```

`.ans` は次の通り。

```text
0
```

`.stdout` は次の通り。

```text
Hello, World!
```

## 編集するファイル

- `mycc.py`

`importlib` でコマ10 の `Codegen10` を継承した `Codegen11` に、以下の機能を追加する（クラスの骨組みはスケルトンにあらかじめ書かれている）。

| 実装対象 | 役割 |
|----------|------|
| `_intern(value)` | 同じ文字列を重複登録せず `.LCn` ラベルを割り当てる |
| `collect_strings_stmt_*` | 文の中を再帰的にたどる（`Decl` / `ExprStmt` / `Return` / `Block` / `If` / `While` / `For`） |
| `collect_strings_expr_*` | 式の中を再帰的にたどる（二項演算・単項演算・`Cond`・`Index`・`Call` など） |
| `collect_strings_expr_Str(node)` | `node.sval` を `_intern` する |
| `emit_data_section()` | 登録済みの文字列を `.data` に `.byte` 列として出力する |
| `type_of_expr_Str(node)` | 文字列リテラルの型を返す |
| `codegen_Str(node)` | `la a0, ラベル` で文字列の先頭アドレスをロードする |

`collect_strings_stmt()` の呼び出しと `emit_data_section()` の呼び出し自体は `main()` に書かれている。
実装するのは、呼ばれる側のハンドラの中身である。

## 実装手順

1. スケルトンの `importlib` 継承によりコマ10の Codegen クラスを引き継ぐ（あらかじめ書かれている）
2. `self._strings` と `self._intern()` を追加して文字列ラベル管理を作る
3. 文字列を集める走査の呼び出し自体は `main()` に書かれている（各 `FuncDef` の本体に対して `collect_strings_stmt()` を呼ぶ）。学習者が実装するのは、AST を再帰的にたどって文字列を集める各ハンドラ（`_intern()` と `collect_strings_stmt_*` / `collect_strings_expr_*`、特に `collect_strings_expr_Str()`）の中身である
4. `.data` セクションを出力する呼び出し（`emit_data_section()`）も `main()` に書かれている。学習者が実装するのは `emit_data_section()` 自体の中身で、登録済みの各文字列を `.byte` 列として出力する処理である
5. `.text` セクションの出力と関数本体の生成は、コマ10までの実装がそのまま使われる（この回で新しく書く部分はない）
6. `self._type_of_expr(node)` で `ND_STR` を `char *` にする
7. `ND_STR` のハンドラメソッドで `la a0, label` を出す
8. `printf_hello.c` と `printf_number.c` の stdout テストを通す
9. `file_stream.c` と `lib_exit.c` を通す<br>（`lib.h` のストリーム関数一式と `exit`。`struct FILE *` は 8 バイトのポインタなので、7 までができていれば新しく書く処理はない。）

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `printf_hello.c` | 文字列だけを出力する | `Hello, World!` |
| `printf_number.c` | `%d` に整数を渡す | `x=42` |
| `strlen_literal.c` | 文字列を `strlen` に渡す | 終了コード `3` |
| `file_stream.c` | `fdopen`/`fprintf`/`fopen`/`fread`/`fclose` | `stream ok` / 終了コード `42` |
| `lib_exit.c` | `exit` で終了コードを指定して打ち切る | `before exit` / 終了コード `7` |

## テスト

```bash
python3 scaffold/test_runner.py sessions/11_strings_printf
```

`tests/printf_hello.c` が `Hello, World!` を出力すれば基本形は成功。

個別に動かす場合は、次のようにする。

```bash
python3 sessions/11_strings_printf/mycc.py sessions/11_strings_printf/tests/printf_hello.c \
  | riscv64-linux-gnu-gcc -x assembler -static - -o out

qemu-riscv64 ./out
echo $?
```

標準出力を伴う回なので、`echo $?` の前に出力そのものも目で確認する。

## 注意

`printf` はこの回でも実装しない。
`riscv64-linux-gnu-gcc -static` でリンクしたとき、libc の `printf` が使われる。
`lib.h` が与えるのは宣言だけである。

文字列リテラルは `.data` に置く読み出し専用のデータとして扱う。
同じ内容の文字列は `_intern()` が1つのラベルにまとめるので、
同じ文字列を2回書いても `.data` には1つしか出ない。

`ND_STR` の値は文字列そのものではなく先頭アドレスである。型は `char *` になる。
文字列リテラルの中身を書き換える操作はこの回では扱わない。

`.stdout` を置いたテストは、終了コード（`.ans`）と標準出力の両方が一致して初めて通る。
末尾の改行の有無まで一致させる必要がある。
