---
introduces:
  - sizeof_struct
  - malloc_struct
  - void_ptr_conversion
  - self_referential_struct
  - struct_tag_scope
  - null_macro
  - linked_list_traversal
requires:
  - while_stmt
  - pointer_type
  - sizeof_typename
  - malloc_call
  - include_libh
  - struct_definition
  - size_of_ty_str_struct
  - member_access_arrow
---

# コマ13: sizeof + malloc + 連結リスト

## 今日のゴール

`sizeof` と `malloc` を使い、構造体をヒープ上に確保して連結リストを動かす。

コマ12では、スタック上の構造体変数と `.` / `->` を扱った。
この回では、構造体を `malloc` で動的に確保し、ポインタでつないだデータ構造を作る。

```c
struct Node {
    int val;
    struct Node *next;
};
```

`struct Node` は、自分と同じ型へのポインタ `next` を持つ。
このような構造体を自己参照構造体と呼ぶ。

## この回で扱う範囲

対象にする機能は次の通り。

| 種類 | 例 |
|------|----|
| `sizeof(型名)` | `sizeof(int)`, `sizeof(struct Node)` |
| `malloc` | `malloc(sizeof(struct Node))` |
| 自己参照構造体 | `struct Node *next` |
| 連結リスト | `head = head->next` |

`malloc` 自体は自作しない。
`lib.h` の宣言を使い、リンク時に libc の `malloc` を呼び出す。

## AST を確認する: sizeof

まず、`sizeof` がどのような AST になるか確認する。

```bash
python3 scaffold/parse_viewer.py sessions/13_sizeof_malloc_list/tests/sizeof_test.c
```

このプログラムの内容は次の通り。

```c
int main() {
    return sizeof(int) + sizeof(char);
}
```

実行すると、次のようなS式が表示される。

```lisp
(program
  (funcdef "main" :type int (params)
    (block
      (return
        (add (sizeof-type int) (sizeof-type char))))))
```

![`sizeof_test.c` の AST](figures/ast/13_sizeof_test_ast.svg)

`sizeof(int)` は `(sizeof-type int)` になる。
`sizeof(char)` は `(sizeof-type char)` になる。
これらは実行時に計算する必要はなく、コンパイル時に型サイズを見て定数を出せばよい。

## AST を確認する: malloc と自己参照構造体

次に、`malloc` と `struct Node *next` を含む小さな例を見る。

```bash
python3 scaffold/parse_viewer.py sessions/13_sizeof_malloc_list/tests/list_min.c
```

このプログラムの内容は次の通り。

```c
#include "lib.h"

struct Node {
    int val;
    struct Node *next;
};

int main() {
    struct Node *n;
    n = malloc(sizeof(struct Node));
    n->val = 10;
    n->next = NULL;
    return n->val;
}
```

実行すると、次のようなS式が表示される。

先頭には `lib.h` の関数プロトタイプが並び（`#include` がファイル結合であることが
そのまま見える）、その後に `main` が続く。`main` の部分は次のようになる。

```lisp
  (funcdef "main" :type int (params)
    (block
      (decl "n" :type
        (ptr (struct "Node")))
      (exprstmt
        (assign (var "n")
          (call "malloc"
            (args
              (sizeof-type (struct "Node"))))))
      (exprstmt
        (assign
          (member "->" "val" (var "n"))
          (num 10)))
      (exprstmt
        (assign
          (member "->" "next" (var "n"))
          (num 0)))
      (return
        (member "->" "val" (var "n"))))))
```

![`list_min.c` の AST](figures/ast/13_list_min_ast.svg)

`malloc(sizeof(struct Node))` は、`sizeof(struct Node)` の結果を引数として `malloc` を呼び出すだけである。
`lib.h` の宣言は `void *malloc(int size);` である。`void *` は任意の `T *` へ暗黙変換されるので、
そのまま `struct Node *n` に代入できる。逆向き（`T *` から `void *`）も同じく暗黙変換で、
`void *v;` のような変数や `int f(void *p)` のような仮引数も書ける
（`void` 単独の変数は書けない。`*` を伴う形だけである）。
この言語にキャスト `(type)expr` は無いので、ポインタの型を変える手段はこの暗黙変換だけである。
どちらもサイズ 8 のポインタなので、変換のために命令を出す必要はない。

## sizeof のコード生成

`sizeof` は値を計算する式だが、実行時にメモリを読みに行く必要はない。
型情報からサイズを調べ、即値を `a0` に入れる。

```python
if node.kind == ND_SIZEOF_TYPE:
    self.emit(f"  li a0, {self.size_of_ty_str(node.ty_str, self._struct_defs)}")
    return
```

`sizeof` の被演算子は型名だけである。`sizeof 式`（`sizeof x` のように式を書く形）は
言語仕様の対象外なので（`language_spec.md` の「除外」節）、スキャフォールドの AST にも
対応するノードは無い。

たとえば `sizeof(struct Node)` は、`self._struct_defs["struct Node"]["size"]` が16なら `li a0, 16` を出す。

## malloc は普通の関数呼び出し

`malloc` はライブラリ関数である。
コンパイラが行うことは、通常の関数呼び出しと同じである。

```c
n = malloc(sizeof(struct Node));
```

この式では、まず `sizeof(struct Node)` を `a0` に計算し、それを第1引数として `malloc` を呼び出す。
戻り値も `a0` に返る。

## malloc を呼び出すと何が起きるか

`malloc` は、指定されたバイト数ぶんのメモリ領域をヒープから確保し、その先頭アドレスを返すライブラリ関数である。

```c
n = malloc(sizeof(struct Node));
```

この例では、まず `sizeof(struct Node)` によって `struct Node` 1個ぶんに必要なバイト数を求める。
その値を第1引数として `malloc` に渡す。
`malloc` は実行時に、そのサイズ以上の連続したメモリ領域をヒープから確保し、その先頭アドレスを返す。

返ってきた値は、構造体そのものではなく、確保されたメモリ領域の先頭アドレスである。
そのアドレスを `struct Node *n` に代入することで、以後その領域を `struct Node` として扱える。

```c
n->val = 10;
n->next = NULL;
```

この代入によって、確保した領域の中に実際のフィールド値を書き込んでいる。

重要なのは、`malloc` はメモリを確保するだけで、中身を初期化しないことである。
確保直後の `n->val` や `n->next` の値は未定義なので、使う前に自分で代入する必要がある。

実際の `malloc` の内部では、未使用のヒープ領域を管理し、要求されたサイズに合う領域を探して返している。
多くの実装では、確保した領域の前後に管理用の情報を持ったり、足りない場合に OS から追加のメモリを取得したりする。
ただし今回のコンパイラでは、その仕組みを実装しない。
コンパイラが担当するのは、引数を `a0` に置き、呼び出し規約に従って libc の `malloc` を呼び出すところまでである。

なお、本来は `malloc` で確保したメモリは、不要になったら `free` で解放する。
この回では、プログラムがすぐ終了する小さな例だけを扱うため、`free` は実装範囲に含めない。

## 自己参照構造体

`struct Node` の定義には `struct Node *next` が含まれている。

```c
struct Node {
    int val;
    struct Node *next;
};
```

`next` は `struct Node` そのものではなく、`struct Node` へのポインタである。
ポインタのサイズは常に8バイトなので、構造体の中に自分自身へのポインタを持てる。

レイアウトは次のようになる。

| フィールド | 型 | オフセット | サイズ |
|------------|----|------------|--------|
| `val` | `int` | 0 | 4 |
| `next` | `struct Node *` | 8 | 8 |

`next` は8バイト境界に置くため、`val` の後に4バイトの余白が入る。
この簡易実装では、各フィールドをその型サイズに応じて自然な境界に揃える。

## struct のタグ名

構造体の型は常に `struct タグ名` の形で参照する。この言語に `typedef` は
ないため、構造体型の名前はタグ名の 1 種類だけである。

```python
# タグ名でサイズを引く
self.size_of_ty_str("struct Node", self._struct_defs)
```

`self._struct_defs` のキーも `"struct Node"` の形で持てば、
型文字列（`ty_str`）をそのままキーとして使える。

## 連結リストの走査

連結リストは、各ノードが次のノードへのポインタを持つ構造である。

```c
int list_sum(struct Node *head) {
    int sum;
    sum = 0;
    while (head != NULL) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}
```

`head != 0` は、ポインタが `NULL` でないことを調べている。
`head->val` で現在のノードの値を読み、`head = head->next` で次のノードへ進む。

::: note

**`while (head != 0 && head->val > 0)` とは書けない**。
このスキャフォールドの `&&` は両辺を必ず評価するため、
`head` が `NULL` のときに `head->val` を読んでクラッシュする。
NULL の判定と中身の判定は、上の例のように分けて書くこと
（短絡評価の実装は発展課題 S1 で扱う）。

:::

![スタック上の `head` とヒープ上に確保された3ノード](figures/13_linked_list.svg)

`head` はスタック上のローカル変数だが、各ノードは `malloc` で確保したヒープ上にある。
`head = head->next` は、`head` の指す先を矢印1つぶん右のノードへ進める。

## 編集するファイル

- `mycc.py`

`importlib` でコマ12 の Codegen クラスを継承した `Codegen13` に、以下の機能を追加する。

| 実装対象 | 役割 |
|----------|------|
| `type_of_expr_SizeofType(node)` | `sizeof(型名)` の型は `int` |
| `codegen_SizeofType(node)` | `node.ty_str` のサイズを求め、`li a0, <size>` を出力する |

この回で新しく書くコードはこの2つだけである。
`malloc` も自己参照構造体も、コマ8 の関数呼び出しとコマ12 の構造体処理がそのまま働く。

## 実装手順

1. スケルトンの `importlib` 継承によりコマ12の Codegen クラスを引き継ぐ（あらかじめ書かれている）
2. `parse_struct_defs()` が自己参照フィールド（`struct Node *next`）を扱えることを確認する（ポインタは中身を知らなくてもサイズ 8 で確定する）
3. `self.size_of_ty_str("struct Node", self._struct_defs)` が構造体サイズを返すことを確認する
4. `sizeof(struct Node)` が `malloc` の引数として使えることを確認する
5. `malloc(sizeof(struct Node))` が通常の関数呼び出しとして動くことを確認する
6. `list_sum.c` まで通す
7. `void_ptr.c` を通す<br>（`void *` と任意の `T *` の相互変換。`void *` の変数・仮引数も書ける。ポインタ同士なのでサイズは常に 8 で、変換のための命令は要らない。）

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `sizeof_test.c` | `sizeof(int) + sizeof(char)` | `5` |
| `malloc_struct.c` | `malloc(sizeof(struct Box))` と `->` | `17` |
| `list_min.c` | `malloc` した1ノードを `->` で読む最小形 | `10` |
| `list_sum.c` | `struct Node` の連結リスト走査 | `60` |
| `void_ptr.c` | `void *` と `T *` のキャストなしの相互変換 | `47` |

## テスト

```bash
python3 scaffold/test_runner.py sessions/13_sizeof_malloc_list
```

`tests/sizeof_test.c` がコンパイルでき、終了コード `5` になれば基本形は成功。

個別に動かす場合は、次のようにする。

```bash
python3 sessions/13_sizeof_malloc_list/mycc.py sessions/13_sizeof_malloc_list/tests/sizeof_test.c \
  | riscv64-linux-gnu-gcc -x assembler -static - -o out

qemu-riscv64 ./out
echo $?
```

## 注意

`sizeof` は翻訳時に値が決まる。生成されるのは `li a0, <サイズ>` の1命令だけで、
実行時に型を調べる処理は出てこない。
扱うのは `sizeof(型名)` の形だけで、`sizeof(式)` は扱わない。

`malloc` は自作しない。`lib.h` の宣言を使い、リンク時に libc の `malloc` に解決する。
`free` を呼ばないので、確保した領域はプログラム終了まで残る。

構造体には境界合わせの余白が入ることがある。
`struct Node { int val; struct Node *next; }` では `next` を8バイト境界に置くため
`val` の後に4バイトの余白が入り、`sizeof(struct Node)` は 16 になる。
`4 + 8 = 12` と数えて `malloc` に渡すと、`next` の書き込みが領域外に出る。
サイズは必ず `sizeof` で求める。

`struct Node *next` はポインタなので、`struct Node` のサイズが確定していなくても
8バイトとして扱える。自己参照構造体が書けるのはこのためである。

## ここまでで着手できる発展課題

`sizeof`・`malloc` まで学んだので、自前 `malloc`（バンプ割り当て → フリーリスト）を作る
[R3](../../workbook/advanced/R3_malloc/README.md) に着手できる。

生成したアセンブリで `malloc` が返すアドレスとリストの辿り方を1命令ずつ確認したいときは、[RV64 シミュレータ](../../tools/sim.html) に貼り付ける。

この回の完成形に相当する OCaml 版参考実装が [`../../workbook/ocaml/README.md`](../../workbook/ocaml/README.md) にある。完成相当の実装なので、まず自分の実装方針を検討してから確認すること。
