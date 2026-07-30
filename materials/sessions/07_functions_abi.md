# コマ7: 再帰的な変数宣言収集

## 今日のゴール

関数本体の深い部分にある変数宣言も事前に収集できるようにする。

コマ4 では `_reset_func_state()` で関数直下の `Decl` だけを `collect_decls` して frame_size を計算していた。
しかし、次のように `if` の中に宣言があると、その宣言を見落としてしまう。

```c
int main() {
    int x;
    x = 3;
    if (x == 3) {
        int y;     // ← この宣言をコマ4 では見落とす
        y = 4;
        return x + y;
    }
    return 0;
}
```

コマ7 では `collect_decls()` を再帰的に拡張し、`Block` / `If` / `While` / `For` の内側まで宣言を収集できるようにする。

## この回で扱う範囲

この回では新しいCの構文は導入しない。
これまでに扱ったすべての機能を対象とし、その上で宣言収集の範囲を拡大する。

| 改良点 | 内容 |
|--------|------|
| 再帰的宣言収集 | `Block`, `If`, `While`, `For` の中の `Decl` も `collect_decls` で収集する |

関数呼び出しや再帰は第08回で扱う。

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

これでは、`if` や `while` の中の `int y;` を確保できず、実行時に正しい位置に変数領域が確保されない。

## collect_decls を拡張する

`collect_decls()` を `match node.kind` で拡張し、制御構文の中も再帰的に調べるようにする。

| `node.kind` | 処理 |
|-------------|------|
| `'Decl'` | `self.collect_decls_Decl(node)` — 変数を登録 |
| `'Block'` | `self.collect_decls_Block(node)` — `stmts` を再帰的に収集 |
| `'If'` | `self.collect_decls_If(node)` — `then` と `else_` の中を収集 |
| `'While'` | `self.collect_decls_While(node)` — `body` の中を収集 |
| `'For'` | `self.collect_decls_For(node)` — `body` の中を収集 |

コマ7 では、C の正確なブロックスコープはまだ実装しない。
関数内に出てくるすべてのローカル変数を、関数全体のフレームに一律で確保する。

![`collect_decls` の再帰走査と、フレームへの一括割り当て](figures/07_frame_nested.svg)

`if` の中の `decl "y"` も走査で発見し、`x` と同じように関数フレームへ割り当てる。

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
| `nested_block.c` | 入れ子ブロック内の変数宣言 | 7 |
| `eight_locals.c` | 8変数（アラインメント境界） | 36 |
| `minimal.c` | 最小関数（ローカル変数なし） | 42 |
| `nested_decl.c` | 入れ子ブロック内の宣言 | 対応する `.ans` を参照 |
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
それらは第08回で扱う。

この回では、Cの正確なブロックスコープは実装しない。
関数内のすべての変数を関数フレームに一律で確保する。
