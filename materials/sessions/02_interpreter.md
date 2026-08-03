---
introduces:
  - ast_node_structure
  - ast_recursive_traversal
  - eval_ast_interpreter
requires:
  - provided_lexer_parser
---

# コマ2: AST + インタープリター

## 今日のゴール

提供 Lexer/Parser が返す AST を走査し、`eval_ast()` で式を評価する。

この回では RV64 アセンブリは出力しない。
Cプログラム全体を実行するのではなく、`main` 関数の中にある `return 式;` の「式」だけを評価する。

目的は、AST を「木」として読み、再帰的に処理する感覚を掴むことである。

## スキャフォールドの動作確認 — AST を見てみる

実装に入る前に、教員提供の Lexer/Parser が AST を正しく構築できることを確認する。
この回で初めて提供 Lexer/Parser を使うため、まずここで動作を確かめる。

```bash
python3 scaffold/parse_viewer.py sessions/02_interpreter/tests/add_mul.c
```

このプログラムの内容は次の通り。

```c
int main() {
    return 1 + 2 * 3;
}
```

実行すると、次のようなS式が表示される。

```lisp
(program
  (funcdef "main" :type int (params)
    (block
      (return
        (add (num 1)
          (mul (num 2) (num 3)))))))
```

![`add_mul.c` の AST](figures/ast/02_add_mul_ast.svg)

この出力は、`1 + 2 * 3` が次の構造として解析されたことを表している。

| S式の部分 | 意味 |
|-----------|------|
| `(program ...)` | プログラム全体 |
| `(funcdef "main" ...)` | `main` 関数の定義 |
| `(block ...)` | 関数本体の `{ ... }` |
| `(return ...)` | `return` 文 |
| `(add A B)` | `A + B` |
| `(mul A B)` | `A * B` |
| `(num 1)` | 整数リテラル `1` |

つまり、`1 + 2 * 3` は次のような木として表されている。

```lisp
(add
  (num 1)
  (mul (num 2) (num 3)))
```

`2 * 3` が `add` の右側の子になっている。
掛け算が先にまとめられている（演算子の優先順位が正しく反映されている）ことを確認する。
演算子の優先順位は Parser がすでに処理しているため、`eval_ast()` は渡された木をそのまま評価すればよい。

S 式ではなく木の形で見たいときは、[AST ビジュアライザ](../../tools/app.html?mode=build) に同じソースを貼るとブラウザ上に構文木が表示され、ノードとソース範囲の対応も確認できる。

## この回で扱う範囲

対象にするプログラムは、次の形に限定する。

```c
int main() {
    return 式;
}
```

扱う式は以下の通り。

| 種類 | 例 |
|------|----|
| 整数リテラル | `42` |
| 単項マイナス | `-3` |
| 足し算 | `1 + 2` |
| 引き算 | `10 - 3` |
| 掛け算 | `2 * 3` |
| 割り算 | `10 / 2` |
| 剰余 | `10 % 3` |
| カッコ | `(1 + 2) * 3` |

変数、代入、if、while、関数呼び出しはまだ扱わない。

## Node の構造

`parse_viewer.py` のS式は表示用の形式である。
`mycc.py` に渡される実体は、`scaffold/ast_def.py` で定義されている `Node` オブジェクトである。

`Node` は、AST の1つの節点を表す入れ物である。
たとえば、数値、足し算、掛け算は、それぞれ別の種類の `Node` として表される。

主に見るフィールドは次の通り。

| フィールド | 意味 |
|------------|------|
| `node.kind` | ノードの種類 |
| `node.val` | 整数リテラルの値 |
| `node.lhs` | 二項演算の左側の子ノード |
| `node.rhs` | 二項演算の右側の子ノード |
| `node.operand` | 単項演算の対象ノード |

ノードの種類は、`ast_def.py` で定義されている定数で判定する。

| S式 | `Node` での表現 |
|-----|-----------------|
| `(num 42)` | `node.kind == ND_NUM`, `node.val == 42` |
| `(neg A)` | `node.kind == ND_NEG`, `node.operand == A` |
| `(add A B)` | `node.kind == ND_ADD`, `node.lhs == A`, `node.rhs == B` |
| `(sub A B)` | `node.kind == ND_SUB`, `node.lhs == A`, `node.rhs == B` |
| `(mul A B)` | `node.kind == ND_MUL`, `node.lhs == A`, `node.rhs == B` |
| `(div A B)` | `node.kind == ND_DIV`, `node.lhs == A`, `node.rhs == B` |
| `(mod A B)` | `node.kind == ND_MOD`, `node.lhs == A`, `node.rhs == B` |

たとえば、次のS式を考える。

```lisp
(add (num 1) (mul (num 2) (num 3)))
```

これは `Node` では次のような関係になっている。

| 場所 | 内容 |
|------|------|
| 一番上のノード | `kind == ND_ADD` |
| `ND_ADD` の `lhs` | `ND_NUM`, `val == 1` |
| `ND_ADD` の `rhs` | `ND_MUL` |
| `ND_MUL` の `lhs` | `ND_NUM`, `val == 2` |
| `ND_MUL` の `rhs` | `ND_NUM`, `val == 3` |

## 実装方針

`eval_ast(node)` は、`node.kind` を見て処理を分ける。
`node.kind` は文字列（`'Num'`, `'Add'`, ...）であり、`ast_def.py` で定数 `ND_NUM`, `ND_ADD` 等も定義されている。
スケルトンでは `eval_ast` が TODO になっているため、以下の各ケースを実装する。

方針は次の通り。

| ノード種別 | 評価方法 |
|------------|----------|
| `'Num'` (`ND_NUM`) | `node.val` を返す |
| `'Neg'` (`ND_NEG`) | `node.operand` を評価し、符号を反転する |
| `'Add'` (`ND_ADD`) | `node.lhs` と `node.rhs` を評価し、足す |
| `'Sub'` (`ND_SUB`) | `node.lhs` と `node.rhs` を評価し、引く |
| `'Mul'` (`ND_MUL`) | `node.lhs` と `node.rhs` を評価し、掛ける |
| `'Div'` (`ND_DIV`) | `node.lhs` と `node.rhs` を評価し、割る |
| `'Mod'` (`ND_MOD`) | `node.lhs` と `node.rhs` を評価し、剰余を求める |

重要なのは、子ノードもまた `Node` であるという点である。
そのため、子ノードの値を求めるときも同じ `eval_ast()` を使える。

このように、自分自身を使って木をたどる関数を再帰関数という。

![`eval_ast` が `1 + 2 * 3` の AST を評価する流れ](figures/02_eval_tree.svg)

葉の値が親に返り、根まで上がると式全体の値になる。
①〜⑤は値が確定する順番である。

## 編集するファイル

- `mycc.py`

`eval_ast(node)` を実装する。

## tests/

| ファイル | 内容 | 期待値 |
|----------|------|--------|
| `add_mul.c` | `1 + 2 * 3` | 7 |
| `div_mod.c` | `100 / 4 + 17 % 5` | 27 |
| `paren.c` | `(10 - 3) * 2` | 14 |
| `neg.c` | `-3 + 10` | 7 |

## テスト

```bash
python3 sessions/02_interpreter/check.py
```

`tests/*.c` の `main` 関数内の `return` 式を評価し、対応する `.ans` と比較する。

個別に実行する場合は、次のようにする。

```bash
python3 sessions/02_interpreter/mycc.py sessions/02_interpreter/tests/add_mul.c
```

成功すると、次のように表示される。

```text
評価結果: 7
```

## 注意

この回のテストでは、割り算・剰余の右辺は 0 にならない。

また、この回では負数を含む割り算・剰余は扱わない。
Python の `//` や `%` は、負数を含む場合に C の整数除算・剰余と挙動が異なるためである。

## ここまでで着手できる発展課題

AST とインタープリターまで作ったので、字句解析・構文解析とは何かを CYK 法で体験する
[F0](../../workbook/advanced/F0_cyk/README.md)（コンパイラ本編と独立、前提はこのコマまで）に着手できる。
