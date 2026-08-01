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

### ローカル変数表に型を持たせる

型ごとにサイズと命令が変わるため、この回で `self._locals` の中身を変える。

```python
# コマ4〜コマ9
self._locals: dict[str, int]                 # name → offset

# コマ10 以降
self._locals: dict[str, tuple[int, str]]     # name → (offset, ty_str)
```

コマ9 まではオフセットだけを覚えていればよかったが、
`*p` や `p[i]` で `lb` / `lw` / `ld` を選ぶには、変数の型も覚えておく必要がある。

値の取り出し方も変わる。オフセットは `self._locals[name][0]`、
型は `self._locals[name][1]` である。スケルトンでは前者を `self.lookup_var()`、
後者を `self.lookup_local_ty()` として用意してあるので、
添字を直接書かずにこの2つを使う。この表現はコマ16 まで変えない。

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

## _load_ty / _store_ty

型サイズに応じて、読み書きする命令を変える。

```python
def _load_ty(self, ty):
    size = self.size_of_ty_str(ty)
    if size == 1:
        self.emit("  lb a0, 0(a0)")
    elif size == 4:
        self.emit("  lw a0, 0(a0)")
    else:
        self.emit("  ld a0, 0(a0)")

def _store_ty(self, ty):
    size = self.size_of_ty_str(ty)
    if size == 1:
        self.emit("  sb a0, 0(a1)")
    elif size == 4:
        self.emit("  sw a0, 0(a1)")
    else:
        self.emit("  sd a0, 0(a1)")
```

コマ9では常に `ld` / `sd` でよかったが、この回からは型サイズを見て命令を選ぶ。

### `char` の昇格と縮小

`char` 変数は、この `_load_ty` / `_store_ty` を型サイズ 1 で通せばそのまま動く。
言語仕様上の約束は次の 2 つで、どちらも命令の選択だけで自然に満たされる。

| 場面 | 仕様 | 生成 |
|------|------|------|
| `char` を読む | int へ昇格する（値を保存する） | `lb`（符号拡張して 64 ビットに載る） |
| `char` へ代入する | int から下位 8 ビットへ縮小する | `sb`（下位 1 バイトだけを書く） |

算術そのものは常に int で行うので、`d = c + 2` のような式に特別な処理は要らない。
`c + 2` を int として計算し、代入のところで `sb` を出せばよい。

### 多段ポインタ

`int **pp;` のような多段ポインタも、`ty_str` の末尾の `*` を 1 つ剥がす
`elem_ty_str()` がそのまま働くので、専用の処理は要らない。
`elem_ty_str("int**")` は `"int*"` で、そのサイズは 8 である。
`*pp` は 8 バイトを読み、`**pp` はさらにその先の 4 バイトを読む、という具合に
段数ぶん `_load_ty` が重なるだけである。

## 編集するファイル

- `mycc.py`

`importlib` でコマ9 の `Codegen09` を継承した `Codegen10` に、以下の機能を追加する。

スケルトンに**あらかじめ書かれている**ものは次の通りで、実装対象ではない。
呼び出して使うだけでよい。

| 提供済み | 役割 |
|----------|------|
| `size_of_ty_str(ty)` | `ty_str` から型のバイトサイズを返す |
| `elem_ty_str(ty)` | ポインタの要素型 `ty_str` を返す |
| `is_ptr_ty_str(ty)` | ポインタ型かどうかを返す |
| `alloc_local(name, ty_str)` | `size_of_ty_str` を使って型付きで領域を確保する |
| `lookup_var(name, line)` / `lookup_local_ty(name, line)` | `self._locals` からオフセットと型を引く |
| `_push_a0()` / `_pop_into(reg)` | 一時値の退避と復帰 |
| `_type_of_expr` / `_type_of_lval` / `codegen` / `codegen_lval` の `match` | 各ハンドラへの振り分け |

実装対象は次の通りである。

| 実装対象 | 役割 |
|----------|------|
| `_load_ty(ty)` / `_store_ty(ty)` | 型サイズに応じて `lb`/`lw`/`ld` と `sb`/`sw`/`sd` を選ぶ |
| `_scale_index(elem_ty)` | 添字 `a0` に要素サイズを掛ける |
| `type_of_expr_*` / `type_of_lval_*` | 各ノードの型を求める |
| `codegen_lval_Index(node)` | `p[i]` のアドレス計算 |
| `codegen_Var` / `codegen_Assign` / `codegen_Deref` / `codegen_Index` | 型に応じたロード・ストアに置き換える |
| `codegen_Add` / `codegen_Sub` | ポインタ演算：整数側に要素サイズを掛ける |
| `codegen_SizeofType(node)` | `sizeof(型名)` を即値で出力 |
| `codegen_PreInc` / `codegen_PreDec` | 前置 `++`/`--` を型対応にする（ポインタは要素サイズで進む） |
| `collect_decls_Decl(node)` | `node.ty_str` を渡して型付きで `alloc_local` する |
| `_alloc_params(node)` / `_emit_func_prologue` | パラメータも型付きで確保・保存する |

## 実装手順

1. スケルトンの `Codegen10` が `Codegen09` を `importlib` で継承していることを確認する
2. `_load_ty` / `_store_ty` を型サイズ対応にする（提供済みの `size_of_ty_str` を使う）
3. `type_of_expr_*` / `type_of_lval_*` を埋めて、式の型を引けるようにする
4. `codegen_lval(node)` の `'Index'` handler を実装する（`a0 = base + i * elem_size`）
5. `codegen(node)` の `'Index'` handler を実装する（lval → `_load_ty`）
6. `codegen(node)` の `'SizeofType'` handler を実装する（翻訳時定数）
7. `codegen(node)` の `'Add'` / `'Sub'` handler でポインタ演算を実装する
8. `codegen_PreInc` / `codegen_PreDec` を型対応にする
9. `char_var.c`（`char` 変数）・`ptr_to_ptr.c`（多段ポインタ）・`main_argv.c`（`main(int argc, char **argv)`）を通す<br>（2〜3 が正しくできていれば新しく書く処理はない。取りこぼしの検出用である。）

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `ptr_sum.c` | malloc 領域を `a[i]` で合計 | `15` |
| `ptr_arith.c` | `*(p + 2)` と `*(p + 3)` | `70` |
| `char_var.c` | `char` 変数の読み書き（`lb`/`sb`）・int への昇格・代入時の縮小 | `67` |
| `ptr_to_ptr.c` | 多段ポインタ `int **`（`&`/`*` の重ね掛けと 8 バイト尺度） | `20` |
| `main_argv.c` | `int main(int argc, char **argv)` 形のエントリポイント | `41` |

## テスト

```bash
python3 scaffold/test_runner.py sessions/10_types_pointers
```

`tests/ptr_sum.c` がコンパイルでき、終了コード `15` になれば基本形は成功。

個別に動かす場合は、次のようにする。

```bash
python3 sessions/10_types_pointers/mycc.py sessions/10_types_pointers/tests/ptr_sum.c \
  | riscv64-linux-gnu-gcc -x assembler -static - -o out

qemu-riscv64 ./out
echo $?
```

## 注意

この言語に配列はない。`int a[10];` のような宣言は書けず、`p[i]` も `*(p + i)` の略記でしかない。
連続した領域が必要なときは `malloc(sizeof(int) * N)` で確保し、ポインタで指して使う。

`char` は 1 バイトだが、読み出すと int へ昇格する。
`lb` は符号拡張して 64 ビットレジスタに載せるので、負の値を入れた `char` は負のまま読める。
`char` への代入は `sb` で下位 8 ビットだけを書く（縮小）。
算術そのものは常に int で行うため、`d = c + 2` に特別な処理は要らない。

`_load_ty` / `_store_ty` の判定は型サイズだけで行う。
ポインタはどの型を指していても 8 バイトなので、`ld` / `sd` になる。

この回の `size_of_ty_str(ty)` は引数が1つでよい。
構造体サイズを引くために `self._struct_defs` を渡す2引数版になるのはコマ12 からである。

## ここまでで着手できる発展課題

ポインタまで学んだので、`int` の演算が32bitで折り返さない点を仕様へ寄せる
[S2](../../workbook/advanced/S2_int32/README.md) と、ポインタ同士の引き算に意味を足す
[L1](../../workbook/advanced/L1_ptrdiff/README.md) に着手できる。

生成したアセンブリでポインタ演算のアドレス計算を1命令ずつ確認したいときは、[RV64 シミュレータ](../../tools/sim.html) に貼り付ける。

この回の完成形に相当する OCaml 版参考実装が [`../../workbook/ocaml/README.md`](../../workbook/ocaml/README.md) にある。完成相当の実装なので、まず自分の実装方針を検討してから確認すること。
