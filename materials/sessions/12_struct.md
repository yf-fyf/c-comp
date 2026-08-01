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

したがって `codegen_lval()` では次のようにする。

```python
if node.kind == ND_MEMBER and not node.is_arrow:
    self.codegen_lval(node.operand)
    struct_ty = self._type_of_lval(node.operand)
    offset = self.field_offset(struct_ty, node.name, self._struct_defs, node.line)
    self.emit(f"  addi a0, a0, {offset}")
    return
```

## `->` のコード生成

`p->x` は `(*p).x` と同じ意味である。
`p` の値は構造体先頭アドレスなので、まず `p` を rvalue として評価する。

```text
address(p->x) = value(p) + offset(x)
```

```python
if node.kind == ND_MEMBER and node.is_arrow:
    self.codegen(node.operand)
    ptr_ty = self._type_of_expr(node.operand)        # e.g. "struct Point*"
    struct_ty = self.elem_ty_str(ptr_ty)             # "struct Point"
    offset = self.field_offset(struct_ty, node.name, self._struct_defs, node.line)
    self.emit(f"  addi a0, a0, {offset}")
    return
```

`.` と `->` で構造体型名の求め方が違うだけなので、
スケルトンではこの分岐を `self._member_struct_type(node)` に切り出してある。

## 編集するファイル

- `mycc.py`

`importlib` でコマ11 の `Codegen11` を継承した `Codegen12` に、以下の機能を追加する。

スケルトンに**あらかじめ書かれている**ものは次の通りで、実装対象ではない。

| 提供済み | 役割 |
|----------|------|
| `parse_struct_defs(source)` / `parse_field_decls(body)` | ソースから構造体定義を集める |
| `align_of_ty_str(ty)` / `is_struct_ty_str(ty, defs)` | 境界と struct 判定 |
| `field_offset(...)` / `field_ty(...)` | フィールドのオフセットと型 |
| `_member_struct_type(node)` の呼び出し口 | `.` と `->` の分岐をまとめる場所 |

実装対象は次の通りである。

| 実装対象 | 役割 |
|----------|------|
| `_member_struct_type(node)` | `.` と `->` の違いを踏まえて対象の構造体型名を返す |
| `alloc_local` / `_scale_index` / `_load_ty` / `_store_ty` | `size_of_ty_str` に `self._struct_defs` を渡す |
| `_load_ty(ty)` の struct 分岐 | struct 型はロードせずアドレスのまま扱う |
| `type_of_expr_Member` / `type_of_lval_Member` | メンバの型を `field_ty` で求める |
| `codegen_lval_Member(node)` | ベースアドレス + `field_offset` |
| `codegen_Member(node)` | 左辺値アドレスを作り、メンバ型でロードする |
| `collect_strings_expr_Member(node)` | `Member` の operand も文字列収集の対象にする |

## 実装手順

1. スケルトンの `importlib` 継承によりコマ11の Codegen クラスを引き継ぐ（あらかじめ書かれている）
2. `CodegenNN.parse_struct_defs(source)` で構造体定義をパースし `self._struct_defs` に渡す
3. `self._type_of_lval()` に `ND_MEMBER` を追加する（フィールドの型は `self._struct_defs` から引く）
4. `self.codegen_lval()` に `ND_MEMBER` ハンドラを追加する（`self._struct_defs` からフィールドオフセットを引く）
5. `alloc_local()` / `_scale_index()` / `_load_ty()` / `_store_ty()` の `size_of_ty_str` 呼び出しに `self._struct_defs` を渡す
6. `_load_ty()` は `struct` 型のときロードせず、アドレスのまま扱う（`is_struct_ty_str` で判定）

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
