# コマ10: Type + ポインタ演算

## 今日のゴール

型サイズを管理する仕組みを導入し、ポインタ演算・`sizeof(型名)`・添字 `p[i]` を実装する。

コマ9では、ポインタも整数もすべて8バイト値として扱った。
しかし、ポインタ演算を扱うには「指している先の型サイズ」が必要になる。

```c
int *p;
p + 2;   // 2バイト進むのではなく、2 * sizeof(int) バイト進む
```

この回では、次の3つを実装する。

| 機能 | 例 |
|------|----|
| ポインタ演算 | `p + 2`, `p - 1` |
| `sizeof(型名)` | `sizeof(int)` |
| 添字 | `p[i]`（`*(p + i)` の略記） |

## この回で扱う範囲

対象にする型は、`int`、`char`、ポインタである。

| 型 | サイズ |
|----|--------|
| `int` | 4バイト |
| `char` | 1バイト |
| `T *` | 8バイト |

この言語に配列はない。連続した int の並びが必要なときは、
`malloc(sizeof(int) * N)` で確保したヒープ上の領域をポインタで指して使う。
`malloc` の呼び出し自体はコマ8 で実装済みの関数呼び出しがそのまま使える
（`lib.h` の宣言を `#include` して、リンク時に libc の `malloc` に解決する）。
構造体、連結リストの本格的な利用、グローバル変数は後の回で扱う。

## AST を確認する: malloc 領域の添字アクセス

まず、malloc で確保した領域を添字で使うプログラムがどのような AST になるか確認する。

```bash
python3 scaffold/parse_viewer.py sessions/10_types_pointers/tests/ptr_sum.c
```

このプログラムの内容は次の通り。

```c
#include "lib.h"

int main() {
    int *a;
    int i;
    int sum;
    a = malloc(sizeof(int) * 5);
    a[0] = 1;
    a[1] = 2;
    a[2] = 3;
    a[3] = 4;
    a[4] = 5;
    sum = 0;
    for (i = 0; i < 5; ++i) {
        sum = sum + a[i];
    }
    return sum;
}
```

実行すると、`lib.h` の関数プロトタイプが並んだ後に、次のような `main` が表示される。

```lisp
  (funcdef "main" :type int (params)
    (block
      (decl "a" :type (ptr int))
      (decl "i" :type int)
      (decl "sum" :type int)
      (exprstmt
        (assign (var "a")
          (call "malloc"
            (args
              (mul (sizeof-type int) (num 5))))))
      (exprstmt
        (assign
          (index (var "a") (num 0))
          (num 1)))
      ...
      (for
        (init
          (assign (var "i") (num 0)))
        (cond
          (lt (var "i") (num 5)))
        (step
          (preinc (var "i")))
        (body
          (block
            (exprstmt
              (assign (var "sum")
                (add (var "sum")
                  (index (var "a") (var "i"))))))))
      (return (var "sum")))))
```

![`ptr_sum.c` の AST](figures/ast/10_ptr_sum_ast.svg)

`a[i]` は AST 上では `(index (var "a") (var "i"))` になる。
このノードは、`*(a + i)` と同じ意味で扱う。
`sizeof(int)` は `(sizeof-type int)` というノードになり、実行時ではなく
コンパイル時に値（4）が決まる。

## AST を確認する: ポインタ演算

次に、領域の先頭アドレスを別のポインタに代入し、ポインタ演算で読む例を確認する。

```bash
python3 scaffold/parse_viewer.py sessions/10_types_pointers/tests/ptr_arith.c
```

このプログラムの内容は次の通り。

```c
#include "lib.h"

int main() {
    int *a;
    int *p;
    a = malloc(sizeof(int) * 4);
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    a[3] = 40;
    p = a;
    return *(p + 2) + *(p + 3);
}
```

`main` の部分の S式は次のようになる。

```lisp
  (funcdef "main" :type int (params)
    (block
      (decl "a" :type (ptr int))
      (decl "p" :type (ptr int))
      (exprstmt
        (assign (var "a")
          (call "malloc"
            (args
              (mul (sizeof-type int) (num 4))))))
      ...
      (exprstmt
        (assign (var "p") (var "a")))
      (return
        (add
          (deref
            (add (var "p") (num 2)))
          (deref
            (add (var "p") (num 3))))))))
```

![`ptr_arith.c` の AST](figures/ast/10_ptr_arith_ast.svg)

`p + 2` は、単にアドレスに `2` を足すのではない。
`p` は `int *` なので、`2 * sizeof(int)`、つまり8バイト進む。

## 型の扱い

新しいスキャフォールドでは、`Type` クラスを使わず、`ty_str` 文字列で型を扱う。

型サイズが必要なときは、次のヘルパーメソッドを使う。

| メソッド | 役割 |
|----------|------|
| `self.size_of_ty_str(ty)` | `ty_str` から型のバイトサイズを返す |
| `self.elem_ty_str(ty)` | ポインタの要素型（指し先型）の `ty_str` を返す |
| `self.is_ptr_ty_str(ty)` | ポインタ型かどうか |

`ty_str` の例:

| Cコード | `ty_str` |
|---------|----------|
| `int a;` | `int` |
| `char c;` | `char` |
| `int *p;` | `int*` |
| `int **pp;` | `int**` |

`self.alloc_local()` では、`ty_str` から `self.size_of_ty_str()` を使って必要なスタック領域を計算する。

## `sizeof(型名)` のコード生成

`sizeof` は値を計算する式だが、実行時にメモリを読む必要はない。
型名から `size_of_ty_str()` でサイズを求め、即値として出力するだけでよい。

```python
def codegen_SizeofType(self, node):
    self.emit(f'  li a0, {self.size_of_ty_str(node.ty_str)}')
```

`malloc(sizeof(int) * 5)` のように、確保サイズの計算に使うのが典型的な用途である。

## `p[i]` のコード生成

`p[i]` は、ポインタ `p` の値に `i * 要素サイズ` を足した場所を表す。

```text
address(p[i]) = value(p) + i * sizeof(element)
```

![malloc した領域のメモリ配置と `p[i]` / `p + 2` のアドレス計算](figures/10_malloc_ptr.svg)

要素1つは `sizeof(int)` = 4 バイトなので、`p + 2` はアドレスを 8 バイト進める。
この倍率を決めるために、要素型のサイズが必要になる。

lvalue としての `p[i]` は、次の流れでアドレスを作る。

```python
self.codegen(node.lhs)   # p の値（領域の先頭アドレス）
push a0
self.codegen(node.rhs)   # 添字 i
scale by element size
pop a1
add a0, a1, a0           # a0 = base + i * size
```

rvalue としての `p[i]` は、このアドレスから値を読む。

## ポインタ演算

`p + n` では、`n` に要素サイズを掛けてからアドレスに加える。

| 式 | 実際に足す値 |
|----|--------------|
| `int *p; p + 2` | `2 * 4` |
| `char *p; p + 2` | `2 * 1` |
| `int **p; p + 2` | `2 * 8` |

`self.elem_ty_str()` がないと、この倍率を決められない。

前置 `++`（コマ6）もこの回で型対応になる。`++p` は `p` を
「1 要素ぶん」、つまり指し先型のサイズだけ進める。

## _emit_load / _emit_store

型サイズに応じて、読み書きする命令を変える。

```python
def _emit_load(self, ty):
    size = self.size_of_ty_str(ty)
    if size == 1:
        self.emit("  lb a0, 0(a0)")
    elif size == 4:
        self.emit("  lw a0, 0(a0)")
    else:
        self.emit("  ld a0, 0(a0)")

def _emit_store(self, ty):
    size = self.size_of_ty_str(ty)
    if size == 1:
        self.emit("  sb a0, 0(a1)")
    elif size == 4:
        self.emit("  sw a0, 0(a1)")
    else:
        self.emit("  sd a0, 0(a1)")
```

コマ9では常に `ld` / `sd` でよかったが、この回からは型サイズを見て命令を選ぶ。

## 編集するファイル

- `mycc.py`

`importlib` でコマ9 の `Codegen09` を継承した `Codegen10` に、以下の機能を追加する（スケルトンにあらかじめ書かれている）。

| ハンドラメソッド | 変更内容 |
|------------------|----------|
| `_load_ty(ty)` / `_store_ty(ty)` | 型サイズに応じて `lb`/`lw`/`ld` と `sb`/`sw`/`sd` を選ぶ |
| `self.size_of_ty_str(ty)` | `ty_str` から型のバイトサイズを計算する |
| `self.elem_ty_str(ty)` | ポインタの要素型 `ty_str` を返す |
| `codegen(node)` の `match` 節に `'Index'` | `p[i]` のアドレス計算とロード |
| `codegen(node)` の `match` 節 `'SizeofType'` | `sizeof(型名)` を即値で出力 |
| `codegen(node)` の `match` 節 `'Add'` / `'Sub'` | ポインタ演算：添字に要素サイズを掛ける |
| `codegen_PreInc` / `codegen_PreDec` | 前置 `++`/`--` を型対応にする（ポインタは要素サイズで進む） |

## 実装手順

1. スケルトンの `Codegen10` が `Codegen09` を `importlib` で継承していることを確認する
2. `_load_ty` / `_store_ty` を型サイズ対応にする（`size_of_ty_str` を使う）
3. `self.alloc_local()` で `ty_str` から `size_of_ty_str` を呼んでスタック領域を決める
4. `codegen_lval(node)` に `'Index'` handler を追加する（`a0 = base + i * elem_size`）
5. `codegen(node)` の `'Index'` handler を追加する（lval → `_load_ty`）
6. `codegen(node)` の `'SizeofType'` handler を追加する（翻訳時定数）
7. `codegen(node)` の `'Add'` / `'Sub'` handler でポインタ演算を追加する
8. `codegen_PreInc` / `codegen_PreDec` を型対応にする

## テスト

```bash
python3 scaffold/test_runner.py sessions/10_types_pointers
```

この回の主要テストは次の通り。

| テスト | 内容 | 期待値 |
|--------|------|--------|
| `ptr_sum.c` | malloc 領域を `a[i]` で合計 | `15` |
| `ptr_arith.c` | `*(p + 2)` と `*(p + 3)` | `70` |
