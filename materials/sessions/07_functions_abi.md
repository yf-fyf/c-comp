# コマ7: 再帰的な変数宣言収集

## 今日のゴール

関数本体を 1 つの `Block` ノードとして一様に扱い、宣言収集を AST の再帰走査として書き直す。

コマ4 では `_reset_func_state()` が関数直下の文を 1 つずつ見て、`Decl` だけを `collect_decls` して frame_size を計算していた。
コマ7 では**関数本体そのもの**（`Block` ノード）を `collect_decls()` に渡し、`_emit_func_body` も `body` 全体を `gen_stmt()` に渡す形にそろえる。

```c
int main() {
    int x;
    int y;         // 宣言は関数本体の先頭にまとめて書く
    x = 3;
    if (x == 3) {
        y = 4;     // 入れ子ブロックの中では、宣言済みの変数を使うだけ
        return x + y;
    }
    return 0;
}
```

この言語では**宣言を書けるのはファイルスコープと関数本体の先頭だけ**で、入れ子ブロックには文しか書けない（`language_spec.md`「宣言」節）。
入れ子ブロックは新しいスコープも作らないので、`if` の中の `y` は関数先頭で宣言した `y` そのものである。

それでもコマ7 では `collect_decls()` を `Block` / `If` / `While` / `For` の内側まで降りる再帰走査にする。
関数本体が `Block` である以上、少なくとも 1 段は降りなければ何も収集できないからである。
`If` / `While` / `For` へも再帰させておけば、`Decl` が AST のどこにあっても取りこぼさない一般形になる。

## この回で扱う範囲

この回では新しいCの構文は導入しない。
これまでに扱ったすべての機能を対象とし、その上で宣言収集の範囲を拡大する。

| 改良点 | 内容 |
|--------|------|
| 再帰的宣言収集 | `Block`, `If`, `While`, `For` の中の `Decl` も `collect_decls` で収集する |

関数呼び出しや再帰はコマ8で扱う。

## コマ4 の制限

コマ4 の `collect_decls()` は関数直下の `Decl` だけを収集していた。

```python
# コマ4 の実装例
def collect_decls(self, node: Node) -> None:
    match node.kind:
        case 'Decl':
            self.collect_decls_Decl(node)
        case _:
            pass
```

これでは `collect_decls(node.body)` のように関数本体の `Block` を丸ごと渡しても、何も収集できない。
`Decl` 以外のノードはすべて素通りしてしまうため、`Block` の `stmts` の中は一度も見られないからである。

## collect_decls を拡張する

`collect_decls()` を `match node.kind` で拡張し、制御構文の中も再帰的に調べるようにする。

| `node.kind` | 処理 |
|-------------|------|
| `'Decl'` | `self.collect_decls_Decl(node)` — 変数を登録 |
| `'Block'` | `self.collect_decls_Block(node)` — `stmts` を再帰的に収集 |
| `'If'` | `self.collect_decls_If(node)` — `then` と `else_` の中を収集 |
| `'While'` | `self.collect_decls_While(node)` — `body` の中を収集 |
| `'For'` | `self.collect_decls_For(node)` — `body` の中を収集 |

本物の C にあるブロックごとのスコープは、この言語には無い（入れ子ブロックは新しいスコープを作らない）。
そのため、関数内のローカル変数はすべて関数全体のフレームへ一律に確保してよい。

![`collect_decls` の再帰走査と、フレームへの一括割り当て](figures/07_frame_nested.svg)

走査で見つけた `decl "x"` と `decl "y"` を、関数に入った時点でまとめて関数フレームへ割り当てる。

同じ関数内で同じ名前の変数を2回宣言するケースは扱わない。

## _reset_func_state の更新

コマ6 まででは `_reset_func_state()` の処理が分散していた（コマ4 の TODO とコマ6 のラベルスタック初期化が別々に行われていた）。
コマ7 では `_reset_func_state()` で次の初期化をひとつにまとめる。

```text
1. self._locals をクリアする
2. self._stack_offset を 0 にする
3. self._break_stack / self._continue_stack をクリアする
4. self._ret_label を self._new_label() で生成する
5. self.collect_decls(node.body) で再帰的に宣言を収集する
6. align_to(self._stack_offset, 16) を frame_size として返す
```

これまで `main()` の中で行っていたラベルスタック等のクリア処理も、`_reset_func_state` に統合する。

## _emit_func_body の変更

コマ6 までは `_emit_func_body` で `body.stmts` を 1 つずつ `gen_stmt` していた。
しかし `If` の `else_` に `Block` が含まれる場合など、文構造を保ったままの処理が必要になる。

そのため、`_emit_func_body` では `body` 全体を `gen_stmt(node)` に渡す形にする。

```python
def _emit_func_body(self, body: Node) -> None:
    self.gen_stmt(body)  # Block ノードとして扱う
```

## 編集するファイル

- `mycc.py`

`importlib` でコマ6 の `Codegen06` を継承した `Codegen07` に、以下の機能を拡張する。

| 実装対象 | 役割 |
|----------|------|
| `collect_decls_Block(node)` | ブロック内の各 `stmt` を再帰的に収集 |
| `collect_decls_If(node)` | `then` 側と `else_` 側を収集 |
| `collect_decls_While(node)` | `body` を収集 |
| `collect_decls_For(node)` | `body` を収集 |
| `_reset_func_state(node)` | 全状態の初期化と再帰的宣言収集。`align_to` した frame_size を返す |
| `_emit_func_body(body)` | `body` 全体を `gen_stmt` に渡す形に変更 |

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `many_locals.c` | 6変数の総和 | 21 |
| `nested_block.c` | 関数先頭で宣言した変数を `if` の中で使う | 7 |
| `eight_locals.c` | 8変数（アラインメント境界） | 36 |
| `minimal.c` | 最小関数（ローカル変数なし） | 42 |
| `nested_use.c` | 二重の入れ子ブロックの中での変数の使用 | 対応する `.ans` を参照 |
| `early_return.c` | 複数のreturn文 | 対応する `.ans` を参照 |

## テスト

```bash
python3 scaffold/test_runner.py sessions/07_functions_abi
```

確認するポイント:

- `ra` と `s0` を保存・復元する
- フレームサイズを 16 バイト境界に揃える
- 入れ子ブロック内の変数宣言も事前に収集する
- ローカル変数が0個でも正しく動く

## 注意

この回では、関数呼び出し、引数、戻り値の受け渡し、再帰はまだ扱わない。
それらはコマ8で扱う。

この言語には、C にあるブロックごとのスコープが無い（入れ子ブロックは新しいスコープを作らない）。
そのため、関数内のすべての変数を関数フレームに一律で確保してよい。
