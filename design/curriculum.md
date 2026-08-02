# Cサブセットコンパイラ教材 設計書

> 対象: C言語既習・コンパイラ理論未習の学習者
> 到達目標: Python 版 C サブセットコンパイラの完遂。以降は選択制の発展課題（`workbook/advanced/`）
> ターゲット: RISC-V RV64IM（C拡張なし）、代替候補 x86-64
> 構成: 全16コマ（Phase 0〜2 の15コマ + 発表・振り返りのコマ17。番号は 01〜17 で 07 は欠番）

この文書は教材全体の設計思想を説明する。
学習者向けの進め方は [`workbook/docs/getting_started.md`](../workbook/docs/getting_started.md) を参照。

---

## 1. 設計コンセプト

### 基本方針: 「Python で理解 → C に移植」

従来型カリキュラムの問題は「C を知っている」と「C でコンパイラを書ける」を同一視していた点にある。
本教材は以下の戦略でこの問題を解決する。

```
Step 1（前半）: Python でコンパイラの「論理」だけに集中する
               メモリ管理・型・ポインタの苦労なしに、
               AST・コード生成・シンボルテーブルを理解する

Step 2（後半）: 動く Python コンパイラを手元に持った状態で
               「C への翻訳」として C 実装を理解する

Step 3（発展課題）: C 実装が動いたら、それ自体がコンパイル対象
               → 自然にセルフホストへ（P1）
```

### 提供物（前半のブラックボックス）

前半では、以下をあらかじめ提供する。
学習者が最初に取り組むのは「AST を受け取ってアセンブリを出力するコード生成器」だけでよい。

- Python 版 Lexer（C サブセットを字句解析してトークン列を返す）
- Python 版 Parser（トークン列を受け取って AST を返す）
- AST ノードの型定義
- テストランナー
- `lib.h`（`printf`・`fopen` 系・`malloc`・`exit` の宣言と `NULL` の定義。コマ11 以降のサンプルで使用する。
  提供する宣言の一覧は `workbook/scaffold/lib.h` を唯一の出典とし、ここには列挙しない。
  `strcmp` / `strlen` 相当は提供せず、学習者が言語内で書く）

標準トラックでは Lexer/Parser をブラックボックスとして扱う。
早く到達した学習者は、これらのコードを読解・移植し、発展課題（F 系列・P1）へ挑戦する。

### フェーズ構成

```
Phase 0 [ 2コマ]  環境 + AST 理解
Phase 1 [ 8コマ]  Python 版ミニコンパイラを完成させる（コマ3〜11。07 は欠番）
Phase 2 [ 5コマ]  Python 版標準機能を完成させる
最終デモ [ 1コマ]  発表・振り返り（コマ17。新しい機能は入れず、既存資産だけを使う）
```

Phase 1 の終わりで「小さいが動く Python 版コンパイラ」を一度完成させる。
ここで到達感を作り、重い機能（構造体など）と発展分岐に備える。

### 設計原則（Ghuloum 2006 より）

1. **One Sitting Rule**: 1コマ1機能。当日デモまで完了する粒度に分割する
2. **Always Working Rule**: どの時点でも実行可能なコンパイラを維持する
3. **Test-First Rule**: 機能追加の前にテストを書く
4. **Real Machine Rule**: 生成アセンブリを毎回 qemu / ネイティブで実行確認する
5. **Deferred Complexity Rule**: 初期は外部ツールに委譲し、複雑機能の自前化を後回しにする

---

## 2. トラック定義

標準トラックの最低目標は「Python で C 言語サブセットの簡易コンパイラを作る」ことに置く
（`fixed17` 全通が目安）。コマ16 でこれを完成させれば主目標は達成である。

その先は必修ではなく、選択制の発展課題（`workbook/advanced/`、全26トピック）として扱う。
Lexer/Parser の自作（F 系列）や C 移植・セルフホスト（P1）はここに含まれる、
かなりやる気のある学習者向けの最難関トピックという位置づけである。

---

## 3. 言語仕様（Core プロファイル）

言語仕様の詳細は [`workbook/docs/language_spec.md`](../workbook/docs/language_spec.md) を参照。

設計基準: **この仕様で書かれたコンパイラが、この仕様自体をコンパイルできる（セルフホスト可能）。**
自己記述の対象は本仕様の機能に限る（複合代入など、発展トピックが本仕様の外側に追加する機能は
含めない。到達範囲の定義は `language_spec.md` の「到達範囲」節を参照）。

---

## 4. フェーズ別の設計意図

各コマのテーマと到達目標の一覧は [`workbook/docs/getting_started.md`](../workbook/docs/getting_started.md)、
到達目標コード例は [`workbook/docs/code_example.md`](../workbook/docs/code_example.md) にある。
ここでは**なぜその順序なのか、なぜその設計を要求するのか**だけを書く。

### Phase 0: 環境 + AST 理解（コマ1〜2）

各コマの形式: 20分講義 + 70分実装 + 10分デモ

**コマ2 の意図**:
インタープリターを先に書かせることで「AST の各ノードが何を意味するか」を体で理解させる。
コード生成はインタープリターの `return value` を `emit assembly` に置き換えるだけという構造的類似性を体感させる。

```python
# コマ2: インタープリター（学習者が書く）
def eval_ast(node):
    if node.kind == 'Num':   return node.val
    if node.kind == 'Add':   return eval_ast(node.lhs) + eval_ast(node.rhs)

# コマ3 以降: コード生成（同じ構造を維持）
def codegen(node):
    if node.kind == 'Num':
        emit(f"  li a0, {node.val}")
    if node.kind == 'Add':
        codegen(node.lhs)
        emit("  addi sp, sp, -8"); emit("  sd a0, 0(sp)")
        codegen(node.rhs)
        emit("  ld a1, 0(sp)");    emit("  addi sp, sp, 8")
        emit("  add a0, a1, a0")
```

### Phase 1: Python 版ミニコンパイラを完成させる（コマ3〜11）

各コマの形式: 15分講義 + 75分実装 + 10分デモ

Phase 1 の最後までに、構造体などの重い機能を除いた「小さいが動く Python 版コンパイラ」を完成させる。
ここで一度到達感を作り、以降の発展分岐に備える。

> **コンパイラのデバッグ方針（毎回）**:
> 1. 生成アセンブリをファイルに保存し、目視で確認する
> 2. qemu 実行時の終了コードが想定と異なる場合、`gdb-multiarch` でステップ実行する
> 3. 小さい入力から段階的に複雑にする（Always Working Rule の実践）

各回で「何を導入させるか」を設計上の要点として決めている。

| コマ | 導入する設計 |
|------|-------------|
| 3 | インタープリターの構造を `emit()` に置き換える（構造を変えずに出力先だけ変える） |
| 4 | ローカル変数のスタックオフセット管理。関数本体（`Block` ノード）からの宣言収集とフレームサイズ計算を `_reset_func_state()` にまとめる |
| 5 | ラベル生成。Python の `str` でラベルを管理する。三項演算子 `?:`（`ND_COND`）も同回で導入する |
| 6 | ループ開始/終了ラベル、`break` / `continue` のジャンプ先管理（ラベルスタック）。前置 `++`/`--`（`preinc`/`predec`）も同回で導入する |
| 8 | `a0`〜`a7` での引数受け渡し、引数のスタック退避、`call` 前の16バイトアラインメント（奇数個引数の padding） |
| 9 | **`codegen()` / `codegen_lval()` の分離**。全ポインタ操作の根幹で、この設計なしに先へ進めない |
| 10 | `ty_str` 文字列による型サイズ管理（`size_of_ty_str` / `elem_ty_str`）。ポインタ演算に型サイズが要るため |
| 11 | `.data` セクションへの出力とラベル参照。`#include "lib.h"` を使い始める |

> **アラインメントの注意点（コマ4 以降）**: 16バイトアラインメント違反は無音クラッシュを招く。
> `align_to(n, 16)` ヘルパーをスケルトンで提供し、アラインメント計算を自動化する
> （コマ4 でフレームサイズ、コマ8 で `call` 前のスタックに適用する）。
>
> **デバッグ演習**: 意図的にアラインメントを1バイトずらしたコードを生成し、
> `gdb-multiarch` で `Illegal instruction` の発生箇所を特定する演習を行う。

```python
# コマ9 で設計させる2関数の構造
def codegen(node):
    """rvalue を a0 に返す"""
    if node.kind == 'Deref':
        codegen_lval(node)         # アドレスを a0 に
        emit("  ld a0, 0(a0)")     # アドレスから値をロード

def codegen_lval(node):
    """lvalue のアドレスを a0 に返す"""
    if node.kind == 'LocalVar':
        emit(f"  addi a0, s0, {node.offset}")
    if node.kind == 'Deref':
        codegen(node.child)        # ポインタ値（= アドレス）を a0 に
```

### Phase 2: Python 版標準機能を完成させる（コマ12〜16）

| コマ | 導入する設計 |
|------|-------------|
| 12 | 構造体情報（サイズ・フィールドオフセット）を `self._struct_defs` の `dict` で管理する |
| 13 | `sizeof(type)` は `size_of_ty_str()` でコンパイル時に定数化する |
| 14 | `self._locals` → `self._globals` の2段階探索で隠蔽を実現する |
| 15 | スキャフォールドの `preprocess()` で展開する。`#define` の自前実装は発展課題扱い |
| 16 | 新しい機能は入れない。統合と可読性の作り込みに充てる |

> **コマ16 の重要性**: 標準トラックの主目標はここで完了させる。
> 変数名・関数の役割・コメントを整理し、「自分が書いたが読める Python 版コンパイラ」にする。

### 最終デモ: 発表・振り返り（コマ17）

コマ16 で成果物は完成しているので、コマ17 に技術的な補完の役割は無い。
新しい機能もコードも入れず、既存資産（自分の `final/mycc.py`・`fixed17`・RV64 シミュレータ）の
再利用だけで、**「動くコンパイラ」を「説明できるコンパイラ」に変える**ことに充てる。
設計の発表、生成アセンブリの読み下し、コマ16 からコマ1 への逆順の振り返り、
自己レビューのルーブリック、発展課題の選び方の5つで構成する。

分離した理由は、コマ16 が統合・総合テスト・バグ切り分け・コードレビューで既に満杯であり、
発表と振り返りを同じ回に押し込むと、どちらも形だけになるためである。
§8 の「各コマ末に5分デモ」を、最後に一度だけ長い形で行う回とも言える。

コマ17 完了後は、選択制の発展課題（`workbook/advanced/`）に分岐する。
中でも C 移植・セルフホスト（P1）は「動く Python コンパイラを参照実装として、
アルゴリズムを再発明せず C にデータ構造だけを写す」という方針を取る、
最も範囲の広い自主課題である。詳細は
[`workbook/advanced/P1_selfhost/README.md`](../workbook/advanced/P1_selfhost/README.md) にある。

---

## 5. RISC-V 導入戦略

### なぜ RV64 が教育に適しているか

```
x86-64 の問題:
  - 可変長命令（1〜15バイト）
  - 暗黙のフラグレジスタ
  - REX/VEX 等の複雑なプレフィックス
  - レジスタ命名の歴史的混乱（rax/eax/ax/al）

RV64 の利点:
  - 全命令 32bit 固定長（C拡張除外なら）
  - 32本の汎用レジスタ（用途が明確）
  - 直交的な命令セット（Load/Store 分離）
  - 呼び出し規約がシンプルで一貫
  - オープンな仕様書が無料で入手可能
```

x86-64（System V ABI）は代替候補として検討したが、上記の問題（可変長命令・暗黙の
フラグレジスタ・複雑なプレフィックス・レジスタ命名の歴史的混乱）が学習の妨げになると
判断し、採用しなかった。`workbook/` 側の実行環境（`docker/rv64/`）とテストランナーは
RV64 専用で、x86-64 を選べる構成にはしていない。

### コマ1 でのアセンブリ手書き体験

```asm
    .global main
main:
    addi    a0, zero, 42    # 戻り値 = 42
    ret
```

```bash
riscv64-linux-gnu-gcc -static hello.s -o hello
qemu-riscv64 ./hello
echo $?   # → 42
```

### 配布するコード生成テンプレート（7種）

```c
void emit_li(int reg, long val)              { printf("  li a%d, %ld\n", reg, val); }
void emit_binop(char *op, int d, int l, int r){ printf("  %s a%d, a%d, a%d\n", op,d,l,r); }
void emit_load(int reg, int offset)          { printf("  ld a%d, %d(s0)\n", reg, offset); }
void emit_store(int reg, int offset)         { printf("  sd a%d, %d(s0)\n", reg, offset); }
void emit_beqz(int reg, char *label)         { printf("  beqz a%d, %s\n", reg, label); }
void emit_call(char *func)                   { printf("  call %s\n", func); }

int align_to(int n, int align) { return (n + align - 1) / align * align; }

void emit_prologue(int frame_size) {
    printf("  addi sp, sp, -%d\n", frame_size + 16);
    printf("  sd ra, %d(sp)\n",    frame_size + 8);
    printf("  sd s0, %d(sp)\n",    frame_size);
    printf("  addi s0, sp, %d\n",  frame_size + 16);
}
void emit_epilogue(int frame_size) {
    printf("  ld s0, %d(sp)\n",    frame_size);
    printf("  ld ra, %d(sp)\n",    frame_size + 8);
    printf("  addi sp, sp, %d\n",  frame_size + 16);
    printf("  ret\n");
}
```

---

## 6. リスク管理・補助ツール

学習者が「動かないのに原因が分からない」状態で止まることが、この教材でいちばん起きやすい失敗である。
そこに対して次の2つを用意している。使い方は
[`workbook/docs/testing.md`](../workbook/docs/testing.md)（テストとデバッグ）に書いてある。

### 補助ツール①: AST 確認（`scaffold/parse_viewer.py`）

入力 C ファイルの AST を S 式・木・Graphviz で表示する。

**なぜ用意するか**: コード生成は AST の形に完全に依存するので、
「自分が想像している AST」と「Parser が実際に返す AST」がずれていると、
コード生成側をいくら直しても解決しない。各コマの講義資料は冒頭で必ず
このツールによる AST 確認から入る構成にしている。

### 補助ツール②: 段階的テストスイート

```
workbook/
├── sessions/NN_xxx/tests/  # 各コマの小テスト（その回の機能だけ）
└── final/tests/            # fixed17（f01〜f17）。コマ1〜16 の全機能をまとめて確認
```

**なぜこの2層か**: 各回の小テストは「今日追加した機能が動くか」を、
`fixed17` は「**前に動いていたものを壊していないか**」を見る。
発展課題では後者が安全網として決定的に効く。回帰を検出できない状態で
最適化や意味論の変更を入れさせるのは無理がある。

### アラインメント違反の対処（コマ4 で導入）

16バイトアラインメント違反は `Illegal instruction` や `Bus error` として現れ、
**エラーメッセージが原因を指さない**。学習者が自力で辿り着くのは難しい種類のバグである。

対策として `align_to(n, 16)` をスケルトン側で提供し、アラインメント計算を
学習者に手計算させない。適用箇所はコマ4（フレームサイズ）とコマ8（`call` 前の `sp`）の2つ。

さらにコマ4 では、意図的にアラインメントを崩したコードを生成して
`gdb-multiarch` で発生箇所を特定する演習を入れている。
「この症状を見たらアラインメントを疑う」という対応づけを先に作らせるためである。

---

## 7. 技術スタック

### 開発環境（Docker 推奨）

```dockerfile
FROM ubuntu:22.04
RUN apt-get install -y \
    python3 \
    gcc-riscv64-linux-gnu \
    qemu-user \
    gdb-multiarch \
    make git vim
```

### 推奨学習リソース

主参考書と読むタイミングは [`workbook/docs/getting_started.md`](../workbook/docs/getting_started.md) の
参考資料の表にまとめてある。

Rui Ueyama の本を発展課題（C 移植・セルフホスト、P1）に挑戦する段階に置いているのは、
x86-64 で書かれているものを RV64 に読み替える作業が、自分の実装を持っていない段階では
負荷が高すぎるためである。

---

## 8. 進捗の作り方（脱落防止）

各コマ末に「今日の動いたもの」を 5 分デモすることを推奨する。
動かなくても「詰まっているポイント」の言語化を必須とする。

- 詰まりパターンを早期発見できる
- 学習者同士の知識共有が生まれる
- 「動かなくて恥ずかしい」ではなく「詰まりを共有する文化」をつくる

---

## 9. 概念導入台帳（`introduces:` / `requires:`）

### なぜ台帳を置くか

「どの概念をどのコマで初めて導入するか」を人手のレビューだけで守ろうとすると、
同じ概念が2回導入される・前提概念が導入前に使われる・存在しないコマを参照する、
といった劣化が積み上がる。台帳を単一の出典に置き、各回の原稿 frontmatter を
機械照合することで、これを構造で防ぐ。

- **この表が出典**である。原稿 frontmatter の `introduces:` は、この表で
  導入コマがそのコマになっている概念ID を、この表の順に列挙したものと一致する。
- 原稿 frontmatter の `requires:` は**導出値**である。その回が導入する各概念の
  前提概念をすべて集め、同じ回で導入される概念を除いたものと一致する。
  手で足し引きしてはならない。
- 検査は `python3 tools/check_concepts.py`（`make check-concepts`）で行う。
- 学習者向けの「機能 → 導入コマ → 検証テスト」の対応は
  [`workbook/docs/language_spec.md`](../workbook/docs/language_spec.md) の「到達範囲」節にある。
  こちらは仕様上の機能単位、本表は実装上の概念単位（設計要素を含む）で粒度が異なる。
- 07 は欠番なので、導入コマに 7 は現れない。

### 台帳

| 概念ID | 概念 | 導入コマ | 前提概念 |
|--------|------|---------|----------|
| `rv64_asm_handwritten` | 手書き RV64 アセンブリとレジスタ | 1 | — |
| `toolchain_qemu_link` | アセンブル・リンク・qemu 実行と終了コード | 1 | — |
| `provided_lexer_parser` | 提供 Lexer / Parser（ブラックボックス） | 1 | — |
| `line_comment` | 行コメント `//` | 1 | `provided_lexer_parser` |
| `keywords_identifiers` | 識別子とキーワード 12 語 | 1 | `provided_lexer_parser` |
| `ast_node_structure` | `Node` の構造（`kind` と子ノード） | 2 | `provided_lexer_parser` |
| `ast_recursive_traversal` | AST の再帰的走査 | 2 | `ast_node_structure` |
| `eval_ast_interpreter` | `eval_ast()` による式の評価 | 2 | `ast_recursive_traversal` |
| `codegen_a0_contract` | `codegen(node)` の約束（結果を `a0` に残す） | 3 | `eval_ast_interpreter`, `rv64_asm_handwritten` |
| `func_prologue_epilogue` | 関数プロローグ / エピローグ | 3 | `rv64_asm_handwritten` |
| `int_type` | `int` 型 | 3 | `codegen_a0_contract` |
| `int_literal` | 整数リテラル | 3 | `codegen_a0_contract` |
| `arith_ops` | 算術 `+ - * / %`・単項 `-`・括弧 | 3 | `codegen_a0_contract` |
| `div_mod_rounding` | `/` `%` の丸め（0 方向へ切り捨て） | 3 | `arith_ops` |
| `stack_temporaries` | スタック経由の中間値退避（`_push_a0` / `_pop_into`） | 3 | `codegen_a0_contract` |
| `return_stmt` | `return 式;` | 3 | `codegen_a0_contract`, `func_prologue_epilogue` |
| `main_function` | `int main()` | 3 | `return_stmt` |
| `local_var_decl` | ローカル変数宣言（初期化子なし） | 4 | `int_type` |
| `stack_frame_offsets` | スタックフレームと変数オフセット管理 | 4 | `func_prologue_epilogue` |
| `alloc_local` | `alloc_local()` による領域割り当て | 4 | `stack_frame_offsets` |
| `decl_collection` | 関数本体からの宣言収集とフレームサイズ計算 | 4 | `alloc_local` |
| `frame_align_16` | フレームサイズの16バイト整列（`align_to`） | 4 | `stack_frame_offsets` |
| `lvalue_rvalue_distinction` | rvalue と lvalue の区別 | 4 | `codegen_a0_contract` |
| `codegen_lval_var` | `codegen_lval()`（`'Var'` のみの最小形） | 4 | `lvalue_rvalue_distinction`, `alloc_local` |
| `var_reference` | 変数参照（アドレス取得 → `ld`） | 4 | `codegen_lval_var` |
| `assign_op` | 代入 `=` | 4 | `codegen_lval_var`, `stack_temporaries` |
| `gen_stmt_dispatch` | 文の生成 `gen_stmt()` と式との分離 | 4 | `codegen_a0_contract` |
| `expr_stmt` | 式文 | 4 | `gen_stmt_dispatch` |
| `comparison_ops` | 関係 `< > <= >=` | 5 | `arith_ops` |
| `equality_ops` | 等値 `== !=` | 5 | `arith_ops` |
| `bool_result_int01` | 比較結果が int の `0` / `1` | 5 | `comparison_ops`, `equality_ops` |
| `label_generation` | 一意ラベルの生成（`new_label()`） | 5 | `func_prologue_epilogue` |
| `if_else` | `if` / `else` / `else if` | 5 | `label_generation`, `gen_stmt_dispatch` |
| `block_stmt` | ブロック `{ }` | 5 | `gen_stmt_dispatch` |
| `nested_block_no_scope` | 入れ子ブロックが新しいスコープを作らない | 5 | `block_stmt`, `local_var_decl` |
| `ternary_op` | 条件 `? :` | 5 | `label_generation` |
| `common_epilogue` | 共通エピローグラベルへの合流 | 5 | `label_generation`, `return_stmt` |
| `while_stmt` | `while` | 6 | `label_generation`, `gen_stmt_dispatch` |
| `for_stmt` | `for` | 6 | `while_stmt` |
| `break_continue` | `break` / `continue` | 6 | `while_stmt` |
| `loop_label_stack` | ループラベルスタックによる飛び先管理 | 6 | `break_continue` |
| `prefix_incr_decr_int` | 前置 `++` `--`（int） | 6 | `assign_op` |
| `empty_stmt` | 空文 `;` と `for` の3式の省略 | 6 | `gen_stmt_dispatch` |
| `func_definition` | 関数定義 | 8 | `func_prologue_epilogue`, `gen_stmt_dispatch` |
| `func_params` | 仮引数の受け取りとスタック退避 | 8 | `func_definition`, `alloc_local` |
| `func_call` | 関数呼出し `f(args)` | 8 | `func_definition` |
| `rv64_calling_convention` | RV64 呼出し規約（`a0`〜`a7`・`ra`） | 8 | `func_call` |
| `call_stack_align_16` | `call` 前のスタック16バイト整列 | 8 | `rv64_calling_convention`, `frame_align_16` |
| `recursion` | 再帰呼び出し | 8 | `func_call` |
| `func_prototype` | プロトタイプ宣言 | 8 | `func_definition` |
| `mutual_recursion` | 相互再帰 | 8 | `func_prototype`, `recursion` |
| `codegen_lval_split` | `codegen()` / `codegen_lval()` の分離（`'Deref'` へ拡張） | 9 | `codegen_lval_var`, `lvalue_rvalue_distinction` |
| `pointer_type` | ポインタ型 `T *`（単段） | 9 | `int_type` |
| `addr_of` | アドレス取得 `&` | 9 | `codegen_lval_split` |
| `deref` | 間接参照 `*` | 9 | `codegen_lval_split`, `pointer_type` |
| `assign_through_pointer` | ポインタ経由の書き込み `*p = v;` | 9 | `deref`, `assign_op` |
| `pointer_param` | ポインタ引数 | 9 | `addr_of`, `func_params` |
| `void_return_type` | 戻り値型 `void` と `return;` | 9 | `func_definition`, `common_epilogue` |
| `char_type` | `char` 型 | 10 | `int_type` |
| `char_literal` | 文字リテラル `'a'` | 10 | `char_type` |
| `type_table_ty_str` | ローカル変数表の型情報（`ty_str`） | 10 | `pointer_type`, `char_type` |
| `type_sizes` | 型サイズ（`int` 4 / `char` 1 / `T *` 8） | 10 | `type_table_ty_str` |
| `size_of_ty_str` | `size_of_ty_str()` | 10 | `type_sizes` |
| `elem_ty_str` | `elem_ty_str()`（指し先の型） | 10 | `type_table_ty_str` |
| `sizeof_typename` | `sizeof(型名)`（`int` / `char` / ポインタ） | 10 | `size_of_ty_str` |
| `pointer_arith` | ポインタ ± int（尺度は指し先型） | 10 | `elem_ty_str`, `size_of_ty_str` |
| `subscript` | 添字 `p[i]`（`*(p + i)` の略記） | 10 | `pointer_arith`, `deref` |
| `load_store_by_type` | 型に応じたロード / ストア（`_load_ty` / `_store_ty`） | 10 | `type_sizes`, `deref` |
| `char_promotion` | `char` の昇格と縮小（`lb` / `sb`） | 10 | `load_store_by_type`, `char_type` |
| `multi_level_pointer` | 多段ポインタ `int **` | 10 | `elem_ty_str` |
| `malloc_call` | `malloc` によるヒープ確保 | 10 | `func_call`, `pointer_type` |
| `prefix_incr_pointer` | 前置 `++`（ポインタ、型対応） | 10 | `prefix_incr_decr_int`, `pointer_arith` |
| `main_argv` | `int main(int argc, char **argv)` | 10 | `multi_level_pointer`, `func_params` |
| `string_literal` | 文字列リテラルとエスケープ | 11 | `char_type` |
| `data_section` | `.data` セクションと `.text` の分離 | 11 | `rv64_asm_handwritten` |
| `string_label` | 文字列ラベルの採番と参照 | 11 | `data_section`, `label_generation` |
| `codegen_str` | `ND_STR` のコード生成（先頭アドレスを `a0` に） | 11 | `string_label` |
| `varargs_call` | 可変長引数の外部プロトタイプと呼出し | 11 | `rv64_calling_convention` |
| `printf_call` | `printf` 呼び出し | 11 | `varargs_call`, `string_literal` |
| `include_libh` | `#include "lib.h"` による外部宣言の取り込み | 11 | `func_prototype` |
| `opaque_struct_pointer` | 不透明ポインタ `struct FILE *` | 11 | `pointer_type`, `include_libh` |
| `stream_api` | `fdopen` / `fprintf` / `fopen` / `fread` / `fclose` | 11 | `opaque_struct_pointer`, `include_libh` |
| `exit_call` | `exit` | 11 | `include_libh`, `func_call` |
| `stdout_test` | 標準出力テスト（`tests/foo.stdout`） | 11 | `printf_call` |
| `struct_definition` | `struct タグ { ... };` の定義と構造体変数 | 12 | `int_type`, `char_type`, `pointer_type` |
| `struct_layout_padding` | 構造体のレイアウトとパディング | 12 | `struct_definition`, `type_sizes` |
| `struct_defs_table` | 構造体情報表（サイズ・フィールドオフセット） | 12 | `struct_definition` |
| `size_of_ty_str_struct` | `size_of_ty_str()` の struct 対応（引数追加） | 12 | `struct_defs_table`, `size_of_ty_str` |
| `member_access_dot` | 直接メンバアクセス `.` | 12 | `struct_defs_table`, `codegen_lval_split` |
| `member_access_arrow` | ポインタ経由メンバアクセス `->` | 12 | `member_access_dot`, `deref` |
| `struct_pointer_param` | 構造体ポインタ引数 | 12 | `member_access_arrow`, `pointer_param` |
| `sizeof_struct` | `sizeof(struct タグ)` | 13 | `sizeof_typename`, `size_of_ty_str_struct` |
| `malloc_struct` | 構造体のヒープ確保 | 13 | `malloc_call`, `sizeof_struct` |
| `void_ptr_conversion` | `void *` と `T *` の暗黙変換 | 13 | `malloc_call`, `pointer_type` |
| `self_referential_struct` | 自己参照構造体と前方宣言 | 13 | `struct_definition`, `pointer_type` |
| `struct_tag_scope` | struct タグ名の扱い | 13 | `struct_definition` |
| `null_macro` | `NULL`（`lib.h` の `#define NULL 0`） | 13 | `include_libh`, `pointer_type` |
| `linked_list_traversal` | 連結リストの構築と走査 | 13 | `self_referential_struct`, `member_access_arrow`, `while_stmt`, `null_macro` |
| `global_var` | グローバル変数 | 14 | `local_var_decl`, `data_section` |
| `bss_section` | `.bss` セクションへの出力 | 14 | `global_var` |
| `global_zero_init` | グローバル変数の 0 初期化保証 | 14 | `bss_section` |
| `global_address_la` | グローバル変数のアドレス取得 | 14 | `global_var`, `codegen_lval_split` |
| `global_struct_var` | グローバル構造体変数 | 14 | `global_var`, `struct_definition` |
| `var_scope_lookup` | 2段階の変数探索（ローカル → グローバル） | 14 | `global_var`, `alloc_local` |
| `local_shadows_global` | ローカル変数によるグローバル変数の隠蔽 | 14 | `var_scope_lookup` |
| `logical_not` | 単項 `!` | 14 | `bool_result_int01` |
| `logical_and_or` | 論理 `&&` `\|\|`（短絡しない） | 14 | `bool_result_int01` |
| `eval_order_no_shortcircuit` | 評価順序（両辺を評価する。例外 E3） | 14 | `logical_and_or` |
| `preprocess_provided` | スキャフォールド提供の前処理 `preprocess()` | 15 | `provided_lexer_parser` |
| `include_user_header` | `#include "自作ヘッダ"`（入れ子を含む） | 15 | `include_libh`, `preprocess_provided` |
| `define_object_macro` | `#define`（1段置換） | 15 | `preprocess_provided` |
| `multifile_compile` | 複数ソースファイルの同時コンパイル | 15 | `func_prototype`, `global_var` |
| `prototype_vs_definition` | プロトタイプと定義の分離 | 15 | `func_prototype`, `multifile_compile` |
| `include_cycle_error` | 循環取込み・マクロ多段参照のエラー | 15 | `include_user_header` |
| `mycc_integration` | `final/mycc.py` への統合 | 16 | `define_object_macro`, `multifile_compile`, `linked_list_traversal`, `local_shadows_global` |
| `final_test_suite` | `final/tests/` の総合判定（`fixed17`） | 16 | `mycc_integration` |
| `code_review_criteria` | コードレビュー観点と仕上げ | 16 | `mycc_integration` |
| `final_demo` | 成果デモの型（設計の説明と質疑） | 17 | `mycc_integration`, `final_test_suite` |
| `asm_readthrough` | 生成アセンブリの読み下し | 17 | `func_prologue_epilogue`, `stack_frame_offsets`, `rv64_calling_convention` |
| `self_review_rubric` | 自己レビューのルーブリック | 17 | `code_review_criteria`, `final_test_suite` |
| `advanced_track_selection` | 発展課題の選び方 | 17 | `final_test_suite` |

### 台帳から読み取れる設計上の判断

- `codegen_lval` はコマ4 で `'Var'` だけの最小形として入れ、コマ9 で `'Deref'` へ
  拡張する。台帳ではこれを `codegen_lval_var`（4）と `codegen_lval_split`（9）に
  分けて表す。「導入は1箇所」の原則を保ちながら段階導入を表現するための書き方である。
- `sizeof` も同様に `sizeof_typename`（10）と `sizeof_struct`（13）に分ける。
  コマ13 は `sizeof` そのものの導入回ではなく、struct への適用の導入回である。
- コマ16 は新しい C 構文を導入しない。導入するのは統合と検証の枠組みだけであり、
  `introduces:` はその3項目になる。
- コマ17 も新しい C 構文を導入しない。導入するのは発表・読解・自己評価・分岐選択という
  非言語の4項目である。台帳は言語機能だけの表ではなく実装上・運用上の概念も含む表なので
  （`toolchain_qemu_link`・`stdout_test`・`code_review_criteria` などが既にそうである）、
  コマ17 もこの枠に収まる。`introduces:` を空にして台帳に載せない案も取れるが、
  「台帳が単一の出典」という原則を保つため、載せる側を採った。
