---
introduces:
  - struct_definition
  - struct_layout_padding
  - struct_defs_table
  - size_of_ty_str_struct
  - member_access_dot
  - member_access_arrow
  - struct_pointer_param
requires:
  - int_type
  - codegen_lval_split
  - pointer_type
  - deref
  - pointer_param
  - char_type
  - type_sizes
  - size_of_ty_str
---

# コマ12: 構造体（struct / . / ->）

## 今日のゴール

`struct タグ { ... };` の定義、構造体変数、`.`、`->` を実装する。

コマ10までに、型サイズとポインタ演算を扱えるようになった。
この回では、複数のフィールドをまとめた構造体を扱う。

```c
struct Point {
    int x;
    int y;
};
```

`struct Point` は、`x` と `y` という2つのフィールドを持つ型である。

## この回で扱う範囲

対象にする機能は次の通り。

| 種類 | 例 |
|------|----|
| struct 定義 | `struct Point { int x; int y; };` |
| 直接メンバアクセス | `p.x` |
| ポインタ経由メンバアクセス | `p->x` |
| 構造体ポインタ引数 | `int f(struct Point *p)` |

言語仕様どおり、構造体のフィールドは `int`、`char`、ポインタに限られる。
扱わない範囲（struct 値の入れ子、構造体代入、グローバル構造体変数）は「注意」節にまとめた。

## AST を確認する: `.`

まず、`.` を使うプログラムがどのような AST になるか確認する。

```bash
python3 scaffold/parse_viewer.py sessions/12_struct/tests/dot_access.c
```

このプログラムの内容は次の通り。

```c
struct Point {
    int x;
    int y;
};

int main() {
    struct Point p;
    p.x = 3;
    p.y = 4;
    return p.x + p.y;
}
```

実行すると、次のようなS式が表示される。

```lisp
(program
  (funcdef "main" :type int (params)
    (block
      (decl "p" :type (struct "Point"))
      (exprstmt
        (assign
          (member "." "x" (var "p"))
          (num 3)))
      (exprstmt
        (assign
          (member "." "y" (var "p"))
          (num 4)))
      (return
        (add
          (member "." "x" (var "p"))
          (member "." "y" (var "p")))))))
```

![`dot_access.c` の AST](figures/ast/12_dot_access_ast.svg)

`p.x` は AST 上では `(member "." "x" (var "p"))` になる。

## AST を確認する: `->`

次に、構造体ポインタを使うプログラムを確認する。

```bash
python3 scaffold/parse_viewer.py sessions/12_struct/tests/arrow_access.c
```

このプログラムの内容は次の通り。

```c
struct Point {
    int x;
    int y;
};

int distance_sq(struct Point *p) {
    return p->x * p->x + p->y * p->y;
}

int main() {
    struct Point p;
    p.x = 3;
    p.y = 4;
    return distance_sq(&p);
}
```

実行すると、次のようなS式が表示される。

```lisp
(program
  (funcdef "distance_sq" :type int
    (params
      (param "p" :type
        (ptr (struct "Point"))))
    (block
      (return
        (add
          (mul
            (member "->" "x" (var "p"))
            (member "->" "x" (var "p")))
          (mul
            (member "->" "y" (var "p"))
            (member "->" "y" (var "p")))))))
  (funcdef "main" :type int (params)
    (block
      (decl "p" :type (struct "Point"))
      (exprstmt
        (assign
          (member "." "x" (var "p"))
          (num 3)))
      (exprstmt
        (assign
          (member "." "y" (var "p"))
          (num 4)))
      (return
        (call "distance_sq"
          (args
            (addr (var "p"))))))))
```

![`arrow_access.c` の AST](figures/ast/12_arrow_access_ast.svg)

`p->x` は AST 上では `(member "->" "x" (var "p"))` になる。
意味としては `(*p).x` と考えればよい。

## 構造体のメモリレイアウト

`struct Point` は `int x; int y;` を持つ。
この講義では `int` を4バイトとして扱うため、次のように配置する。

| フィールド | オフセット | サイズ |
|------------|------------|--------|
| `x` | 0 | 4 |
| `y` | 4 | 4 |

したがって `struct Point` 全体のサイズは8バイトである。

```text
struct Point p;

p + 0 byte : x
p + 4 byte : y
```

![`Point` のメモリ配置と `.` / `->` のアドレス計算](figures/12_struct_layout.svg)

図の `q` は `&p` を代入した `struct Point *q` である（`distance_sq(&p)` の仮引数も同じ状態になる）。
`.` は構造体変数のアドレスから、`->` はポインタの値から、どちらも「+ フィールドオフセット」で場所が決まる。

## struct 定義を読む

Parser は `struct Point { ... };` のフィールド一覧を AST には残さない。
そのため、この回ではソース文字列を走査して構造体情報を集める。

```python
# スケルトンがあらかじめ source から構造体情報を収集し、
# self._struct_defs としてコンストラクタに渡す設計
```

`self._struct_defs` は `"struct Point"` の形の型名をキーとする辞書である。
たとえば `struct Point` のエントリは次の形をとる。

```python
{
    "size": 8,
    "align": 4,
    "fields": {
        "x": (0, "int"),        # (オフセット, ty_str)
        "y": (4, "int"),
    },
}
```

タプルの中身を直接取り出す必要はない。スケルトンは次の2つを提供している。

| 提供済み | 役割 |
|----------|------|
| `field_offset(struct_ty, name, struct_defs, line)` | フィールドのオフセットを返す |
| `field_ty(struct_ty, name, struct_defs, line)` | フィールドの `ty_str` を返す |

スケルトンは次のクラスメソッドでソースから構造体情報を抽出する。

```python
@classmethod
def parse_struct_defs(cls, source: str) -> dict[str, dict]:
    """構造体定義をパースしてフィールド情報を返す"""
    ...
```

この関数は、次の形だけを対象にすればよい（タグは必須）。

```c
struct Point {
    int x;
    int y;
};
```

## size_of_ty_str に引数が増える

コマ10 の `size_of_ty_str(ty)` は `int` / `char` / ポインタしか知らなかった。
`struct Point` のサイズは定義を見ないと分からないので、この回で第2引数が増える。

```python
# コマ10〜コマ11
size_of_ty_str(ty_str) -> int

# コマ12 以降
size_of_ty_str(ty_str, struct_defs=None) -> int
```

`struct_defs` は省略でき、省略した場合の結果はコマ10 と同じである。
そのため、コマ11 までに書いた呼び出しはそのまま動く。
ただし **`struct` のサイズが要る場所では `self._struct_defs` を必ず渡す**。
渡し忘れると `struct Point` のサイズが `int` と同じ4バイトとして扱われ、
エラーにならないまま結果だけがずれる。

```python
self.size_of_ty_str("struct Point", self._struct_defs)   # 8
self.size_of_ty_str("struct Point")                      # 4（渡し忘れ）
```

`alloc_local` / `_scale_index` / `_load_ty` / `_store_ty` は、
この引数を渡す形に直す必要がある。以降のコマ13〜コマ16 でもこの2引数の形を使う。

## `.` のコード生成

`p.x` の lvalue は、`p` のアドレスにフィールドオフセットを足したアドレスである。

```text
address(p.x) = address(p) + offset(x)
```

`'Member'` ノードの lvalue を作るのは `codegen_lval_Member(node)` ハンドラである
（`codegen_lval()` のディスパッチはスケルトンに書かれているので、書くのはハンドラだけでよい）。
`.` の場合、対象の構造体型は operand の左辺値型そのものである。

```python
def codegen_lval_Member(self, node):
    # . の場合
    self.codegen_lval(node.operand)
    struct_ty = self._type_of_lval(node.operand)     # "struct Point"
    offset = self.field_offset(struct_ty, node.name, self._struct_defs, node.line)
    self.emit(f"  addi a0, a0, {offset}")
```

## `->` のコード生成

`p->x` は `(*p).x` と同じ意味である。
`p` の値は構造体先頭アドレスなので、まず `p` を rvalue として評価する。

```text
address(p->x) = value(p) + offset(x)
```

```python
def codegen_lval_Member(self, node):
    # -> の場合
    self.codegen(node.operand)
    ptr_ty = self._type_of_expr(node.operand)        # e.g. "struct Point*"
    struct_ty = self.elem_ty_str(ptr_ty)             # "struct Point"
    offset = self.field_offset(struct_ty, node.name, self._struct_defs, node.line)
    self.emit(f"  addi a0, a0, {offset}")
```

`.` と `->` で違うのは、アドレスの求め方（`codegen_lval` か `codegen` か）と
構造体型名の求め方だけである。後者はスケルトンで `self._member_struct_type(node)` に
切り出してあるので、`codegen_lval_Member` は `node.is_arrow` による分岐と
`_member_struct_type` の呼び出しで書ける。

## 編集するファイル

- `mycc.py`

`importlib` でコマ11 の `Codegen11` を継承した `Codegen12` に、以下の機能を追加する。

スケルトンに**あらかじめ書かれている**ものは次の通りで、実装対象ではない。

| 提供済み | 役割 |
|----------|------|
| `parse_struct_defs(source)` / `parse_field_decls(body)` | ソースから構造体定義を集める |
| `size_of_ty_str(ty, defs=None)` / `align_of_ty_str(ty)` / `is_struct_ty_str(ty, defs)` | サイズ・境界と struct 判定 |
| `field_offset(...)` / `field_ty(...)` | フィールドのオフセットと型 |
| `_type_of_expr()` / `_type_of_lval()` / `codegen_lval()` / `codegen()` / `collect_strings_expr()` のディスパッチ | `'Member'` の分岐は既に書かれている。書くのは飛び先のハンドラだけである |

実装対象は、スケルトンの `raise NotImplementedError` が置かれている次の10個である。

| # | 実装対象 | 役割 |
|---|----------|------|
| 1 | `_member_struct_type(node)` | `.` と `->` の違いを踏まえて対象の構造体型名を返す |
| 2 | `alloc_local(name, ty_str)` | `size_of_ty_str` に `self._struct_defs` を渡し、struct のサイズで領域を確保する |
| 3 | `_scale_index(elem_ty)` | 同上。struct へのポインタの添字で要素サイズを正しく求める |
| 4 | `_load_ty(ty_str)` | 同上。加えて struct 型はロードせずアドレスのまま扱う（`is_struct_ty_str` で判定） |
| 5 | `_store_ty(ty_str)` | 同上。struct のサイズを引けるようにする |
| 6 | `type_of_expr_Member(node)` | `Member` の型は左辺値型と同じ |
| 7 | `type_of_lval_Member(node)` | `_member_struct_type` と `field_ty` でメンバの型を求める |
| 8 | `codegen_lval_Member(node)` | ベースアドレス + `field_offset` |
| 9 | `codegen_Member(node)` | 左辺値アドレスを作り、メンバ型でロードする |
| 10 | `collect_strings_expr_Member(node)` | `Member` の operand も文字列収集の対象にする |

2〜5 の4つは、コマ11 まで動いていたコードに `self._struct_defs` を足すだけの修正である。
ただし直し忘れに気づけるよう、スケルトンでは4つとも `raise NotImplementedError` を置き、
コマ11 版のコードは TODO コメントの中に残してある。

## 実装手順

1. スケルトンの `importlib` 継承によりコマ11の Codegen クラスを引き継ぐ（あらかじめ書かれている）
2. `Codegen12.parse_struct_defs(source)` で構造体定義をパースし、コンストラクタで `self._struct_defs` に渡す（あらかじめ書かれている）
3. `alloc_local()` / `_scale_index()` / `_load_ty()` / `_store_ty()` の `size_of_ty_str` 呼び出しに `self._struct_defs` を渡す
4. `_load_ty()` は `struct` 型のときロードせず、アドレスのまま扱う（`is_struct_ty_str` で判定）
5. `_member_struct_type(node)` を実装する（`.` は `_type_of_lval`、`->` は `_type_of_expr` + `elem_ty_str`）
6. `type_of_lval_Member(node)` と `type_of_expr_Member(node)` を実装する（フィールドの型は `field_ty` で引く）
7. `codegen_lval_Member(node)` を実装する（ベースアドレスに `field_offset` を足す）
8. `codegen_Member(node)` を実装する（`codegen_lval_Member` のアドレスを `_load_ty` でロードする）
9. `collect_strings_expr_Member(node)` を実装する（`Member` の operand を走査する）
10. `dot_access.c` を通し、続けて `arrow_access.c` を通す

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `dot_access.c` | `p.x`, `p.y` の読み書き | `7` |
| `arrow_access.c` | `struct Point *p` に対する `p->x` | `25` |

## テスト

```bash
python3 scaffold/test_runner.py sessions/12_struct
```

`tests/dot_access.c` がコンパイルでき、終了コード `7` になれば基本形は成功。

個別に動かす場合は、次のようにする。

```bash
python3 sessions/12_struct/mycc.py sessions/12_struct/tests/dot_access.c \
  | riscv64-linux-gnu-gcc -x assembler -static - -o out

qemu-riscv64 ./out
echo $?
```

## 注意

構造体代入は言語仕様にないため扱わない。
`struct Point a; a = b;` のように構造体そのものを代入することはできず、
フィールドを1つずつ代入するか、ポインタで渡す。
関数の引数・戻り値も同じで、構造体を値で受け渡すことはしない（`struct Point *` を渡す）。

フィールドに書けるのは `int`、`char`、ポインタだけである。
struct 値を入れ子にすることはできない（`struct Node *next` のようなポインタは書ける）。

`.` と `->` の違いは、対象の構造体アドレスをどう得るかだけである。
`.` は構造体変数のアドレス（`codegen_lval`）、`->` はポインタの値（`codegen`）を使う。
どちらもその後は「+ フィールドオフセット」で同じ計算になる。

`struct Point` のサイズが 8 なのは `int` を2つ並べた結果であって、
フィールド間に余白（パディング）が入る例はこの回には出てこない。
自然な境界に合わせるための余白はコマ13 の `struct Node` で出てくる。

グローバルな構造体変数はコマ14 で扱う。この回はローカル変数と引数だけである。

## ここまでで着手できる発展課題

構造体まで学んだので、構造体の代入を仕様（不可）へ合わせる
[S3](../../workbook/advanced/S3_struct/README.md) と、型検査パスを足す
[Q1](../../workbook/advanced/Q1_typecheck/README.md) に着手できる。

生成したアセンブリでメンバの offset 計算を1命令ずつ確認したいときは、[RV64 シミュレータ](../../tools/sim.html) に貼り付ける。

この回の完成形に相当する OCaml 版参考実装が [`../../workbook/ocaml/README.md`](../../workbook/ocaml/README.md) にある。完成相当の実装なので、まず自分の実装方針を検討してから確認すること。
