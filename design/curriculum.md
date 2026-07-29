# Cサブセットコンパイラ教材 設計書

> 対象: C言語既習・コンパイラ理論未習の学習者
> 到達目標: 標準トラックは Python 版 C サブセットコンパイラ完遂、上位トラックは C 移植・セルフホスト挑戦
> ターゲット: RISC-V RV64IM（C拡張なし）、代替候補 x86-64
> 構成: 全24コマ（Phase 0〜3 + 最終デモ）

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

Step 3（後半）: C 実装が動いたら、それ自体がコンパイル対象
               → 自然にセルフホストへ
```

### 提供物（前半の黒箱）

前半では、以下をあらかじめ提供する。
学習者が最初に取り組むのは「AST を受け取ってアセンブリを出力するコード生成器」だけでよい。

- Python 版 Lexer（C サブセットを字句解析してトークン列を返す）
- Python 版 Parser（トークン列を受け取って AST を返す）
- AST ノードの型定義
- テストランナー
- `lib.h`（`printf`・`malloc`・`strcmp` 等の宣言を含む。コマ 11 以降のサンプルで使用する）

標準トラックでは Lexer/Parser を黒箱として扱う。
早く到達した学習者は、これらのコードを読解・移植し、C 版コンパイラやセルフホストへ挑戦する。

### フェーズ構成

```
Phase 0 [ 2コマ]  環境 + AST 理解
Phase 1 [ 9コマ]  Python 版ミニコンパイラを完成させる
Phase 2 [ 5コマ]  Python 版標準機能を完成させる
Phase 3 [ 7コマ]  上位者向け C 移植チャレンジ（任意）
最終デモ [ 1コマ]  成果のデモ・振り返り
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

| トラック | 条件 |
|---------|------|
| **標準** | Python 版 C サブセットコンパイラを完成させる（`fixed15` 全通が目安） |
| **上位**（C 移植・セルフホスト挑戦） | Python 版完成後、C 移植・Lexer/Parser 読解/自作・セルフホストへ任意挑戦する |

標準トラックの最低目標は「Python で C 言語サブセットの簡易コンパイラを作る」ことに置く。
C 版への移植や Full セルフホストは必修ではなく、かなりやる気のある学習者向けの発展課題として扱う。
上位トラックの参考達成条件は、`mycc_stage1` 生成成功、`fixed15` 全通、`preproc2`（`#define` 自前実装検証用）通過とする。

---

## 3. 言語仕様（Core プロファイル）

言語仕様の詳細は [`workbook/docs/language_spec.md`](../workbook/docs/language_spec.md) を参照。

設計基準: **この仕様で書かれたコンパイラが、この仕様自体をコンパイルできる（セルフホスト可能）。**

---

## 4. フェーズ別の設計意図

各コマのテーマと到達目標の一覧は [`workbook/docs/getting_started.md`](../workbook/docs/getting_started.md)、
到達目標コード例は [`workbook/docs/code_example.md`](../workbook/docs/code_example.md) にある。
ここでは**なぜその順序なのか、なぜその設計を要求するのか**だけを書く。

### Phase 0: 環境 + AST 理解（コマ 1〜2）

各コマの形式: 20分講義 + 70分実装 + 10分デモ

**コマ 2 の意図**:
インタープリターを先に書かせることで「AST の各ノードが何を意味するか」を体で理解させる。
コード生成はインタープリターの `return value` を `emit assembly` に置き換えるだけという構造的類似性を体感させる。

```python
# コマ 2: インタープリター（学習者が書く）
def eval_ast(node):
    if node.kind == 'Num':   return node.val
    if node.kind == 'Add':   return eval_ast(node.lhs) + eval_ast(node.rhs)

# コマ 3 以降: コード生成（同じ構造を維持）
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

### Phase 1: Python 版ミニコンパイラを完成させる（コマ 3〜11）

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
| 4 | ローカル変数のスタックオフセット管理 |
| 5 | ラベル生成。Python の `str` でラベルを管理する |
| 6 | ループ開始/終了ラベル、`break` / `continue` のジャンプ先管理（ラベルスタック） |
| 7 | `collect_decls()` を `Block` / `If` / `While` / `For` へ再帰させ、関数状態の初期化を `_reset_func_state()` に統合する |
| 8 | `a0`〜`a7` での引数受け渡し、引数のスタック退避、`call` 前の16バイトアラインメント（奇数個引数の padding） |
| 9 | **`codegen()` / `codegen_lval()` の分離**。全ポインタ操作の根幹で、この設計なしに先へ進めない |
| 10 | `ty_str` 文字列による型サイズ管理（`size_of_ty_str` / `elem_ty_str`）。ポインタ演算に型サイズが要るため |
| 11 | `.data` セクションへの出力とラベル参照。`#include "lib.h"` を使い始める |

> **アラインメントの注意点（コマ 4 以降）**: 16バイトアラインメント違反は無音クラッシュを招く。
> `align_to(n, 16)` ヘルパーをスケルトンで提供し、アラインメント計算を自動化する
> （コマ 4 でフレームサイズ、コマ 8 で `call` 前のスタックに適用する）。
>
> **デバッグ演習**: 意図的にアラインメントを1バイトずらしたコードを生成し、
> `gdb-multiarch` で `Illegal instruction` の発生箇所を特定する演習を行う。

```python
# コマ 9 で設計させる2関数の構造
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

### Phase 2: Python 版標準機能を完成させる（コマ 12〜16）

| コマ | 導入する設計 |
|------|-------------|
| 12 | 構造体情報（サイズ・フィールドオフセット）を `self._struct_defs` の `dict` で管理する |
| 13 | `sizeof(type)` は `size_of_ty_str()` でコンパイル時に定数化する |
| 14 | `self._locals` → `self._globals` の2段階探索で隠蔽を実現する |
| 15 | スキャフォールドの `preprocess()` で展開する。`#define` の自前実装は上位トラック扱い |
| 16 | 新しい機能は入れない。統合と可読性の作り込みに充てる |

> **コマ 16 の重要性**: 標準トラックの主目標はここで完了させる。
> 変数名・関数の役割・コメントを整理し、「自分が書いたが読める Python 版コンパイラ」にする。

### Phase 3: 上位者向け C 移植チャレンジ（コマ 17〜23）

**形式**: 講義は最小限（5分）、実装中心（85分）、デモ（10分）。

Python 版完成後は進度別に分岐する。
標準トラックの学習者は Python 版の補修・仕上げを行う。
上位トラックの学習者は、動く Python コンパイラを参照実装として C 移植・Lexer/Parser 読解・セルフホストに挑戦する。

段階の一覧は [`workbook/porting/README.md`](../workbook/porting/README.md) にある。
ここで設計上重要なのは、**移植を「アルゴリズムの再発明」にしないこと**である。
Python の `dict` → C の連結リスト、Python のクラス → C の `struct` という変換パターンだけを
体得させ、コンパイラの論理そのものは前半で完成させたものを流用させる。

この分岐を任意にしているのは、C 移植とセルフホストが「時間さえあれば誰でも到達できる」種類の
課題ではないためである。標準トラックの到達（Python 版の完成）を単独で完結した成果として扱う。

> **Fullセルフホストについて**: 必達目標ではなく、自主課題として扱う。
> `./mycc mycc.c -o mycc_stage1` に加え、`fixed15` 全通と前処理専用2本の通過を参考達成条件とする。

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

### コマ 1 でのアセンブリ手書き体験

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
そこに対して次の3つを用意している。使い方は
[`workbook/docs/testing.md`](../workbook/docs/testing.md) と
[`workbook/docs/debugging.md`](../workbook/docs/debugging.md) に書いてある。

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
├── final/tests/            # fixed15。コマ1〜15 の全機能をまとめて確認
└── porting/tests/          # C移植・セルフホスト用（前処理の自前実装）
```

**なぜこの3層か**: 各回の小テストは「今日追加した機能が動くか」を、
`fixed15` は「**前に動いていたものを壊していないか**」を見る。
発展課題では後者が安全網として決定的に効く。回帰を検出できない状態で
最適化や意味論の変更を入れさせるのは無理がある。

### 補助ツール③: ブートストラップ検証スクリプト（C 移植トラック用）

`porting/verify_selfhost.sh` に雛形として置いてある。
Stage 0（gcc でビルド）→ Stage 1（自分でビルド）→ テストという段階を機械的に確認させる。

**なぜスクリプトにするか**: セルフホストは「動いた気がする」状態になりやすい。
どの stage の成果物でテストを通したのかを明示的に踏ませる必要がある。

### アラインメント違反の対処（コマ 4 で導入）

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

Rui Ueyama の本を Phase 3 以降に置いているのは、x86-64 で書かれているものを RV64 に読み替える
作業が、自分の実装を持っていない段階では負荷が高すぎるためである。

---

## 8. 進捗の作り方（脱落防止）

各コマ末に「今日の動いたもの」を 5 分デモすることを推奨する。
動かなくても「詰まっているポイント」の言語化を必須とする。

- 詰まりパターンを早期発見できる
- 学習者同士の知識共有が生まれる
- 「動かなくて恥ずかしい」ではなく「詰まりを共有する文化」をつくる
