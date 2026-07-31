# 実装の約束ごと

Python 版コンパイラ（`sessions/` と `final/`）を書くときの規約。
C 版へ移植するときの規約は発展課題 [`P1_selfhost`](../advanced/P1_selfhost/README.md) にある。

---

## 編集するファイル

| 時期 | 編集対象 |
|------|---------|
| 通常回 | `sessions/NN_xxx/mycc.py` |
| コマ16 以降 | `final/mycc.py`（各回の成果を統合したもの） |

`scaffold/` は書き換えない。Lexer / Parser / AST 定義は提供物として扱う
（自作したい場合は発展課題の F 系列で扱う）。

## 守ってほしい設計

### `codegen()` と `codegen_lval()` を分ける

**この教材でいちばん重要な設計**である。コマ9 で導入し、以降ずっと使う。

```python
def codegen(self, node):
    """rvalue（値）を a0 に残す"""

def codegen_lval(self, node):
    """lvalue（アドレス）を a0 に残す"""
```

ポインタ・配列・構造体メンバへのアクセスは、すべてこの2つの組み合わせで書ける。
1つの関数に混ぜると、`*p = *q;` のような式で破綻する。

### 出力は `emit()` を通す

```python
self.emit("  add a0, a1, a0")     # ○
print("  add a0, a1, a0")         # × 直接呼ばない
```

出力先を差し替えられる状態を保つ。発展課題（最適化・意味論の各回）は
生成されたアセンブリを行単位で書き換えるので、この前提に依存している。

### シンボルテーブルは `dict` でよい

Python 版では素直に `dict` を使う。C 版へ移植するときに連結リストへ置き換える
（対応表は [`../advanced/P1_selfhost/README.md`](../advanced/P1_selfhost/README.md)）。

### アラインメントはヘルパーに任せる

`align_to(n, 16)` を必ず使う。手で計算すると無音クラッシュの原因になる。
詳細は [`rv64_reference.md`](./rv64_reference.md) を参照。

## 命名の目安

| 対象 | 例 |
|------|-----|
| コード生成メソッド | `codegen`、`codegen_lval`、`gen_func` |
| 型の問い合わせ | `_type_of_expr`、`_type_of_lval` |
| 一時値の退避 | `_push_a0`、`_pop_into` |
| 関数ごとの状態 | `_locals`、`_stack_offset`、`_reset_func_state` |
| グローバルな状態 | `_globals`、`_struct_defs`、`_strings` |

先頭の `_` は「その回の実装の内部状態」を表す目印として使っている。

`_push_a0` / `_pop_into` は**名前を変えないこと**。
発展課題（B・O・S・L 系列）のラッパーは、この名前でコード生成クラスを探す。
別の名前にすると、発展課題に進んだ時点で「コード生成クラスが見つからない」と拒否される。

## コメント

複雑な処理にだけ短く書く。行数を稼ぐためのコメントは書かない。
「なぜこうしたか」が読み取れないところに1〜2行入れるのが目安である。
