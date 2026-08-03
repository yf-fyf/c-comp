# Core プロファイル — 言語仕様

**第 2 版(2026 年改訂)**。C サブセットコンパイラが対象とする言語仕様であり、
この教材では凍結された仕様として扱う。この文書がこの言語の唯一の規範で、
教材・雛形・テスト・発展課題はすべてこの版に従う。

設計原則:

- **ISO C11(N1570)の真部分集合。** この仕様で受理されるプログラムは、
  3 件の例外(後述)を除き、そのまま ISO C としても正しく、意味も一致する。
  gcc 等の通常の C コンパイラでもコンパイルできる。
- **セルフホスト可能。** この仕様で書かれたコンパイラが、この仕様自体を
  コンパイルできる(malloc したノードの連結リスト+再帰下降+テキスト出力)。
- **C の核だけを残す。** 配列・typedef・ビット演算などを除外する代わりに、
  `for`・三項演算子・前置 `++`/`--` など C の慣用は保つ。

## 目次（知りたいこと → 節）

この文書は通読用ではなく引くための文書である。左の列で当たりをつけて飛ぶ。

| 節 | 引きたいとき |
|----|-------------|
| [字句](#lex) | キーワードは何語か、コメントの書き方、`a+++b` のような切り出し |
| [型](#types) | 使える型、ポインタ、`struct`、型変換の可否 |
| [リテラル](#literals) | 整数リテラルの上限、文字・文字列リテラル、使えるエスケープ |
| [演算子](#operators) | 使える演算子と優先順位、無い演算子（ビット演算・後置 `++` など） |
| [宣言](#declarations) | 宣言できる場所、初期化子、スコープ、再宣言・再定義 |
| [文・制御構造](#statements) | `if` / `while` / `for` / `break` / `continue` の形、空文・ブロック |
| [関数](#functions) | 引数の個数、プロトタイプ、`main` の扱い、再帰 |
| [プリプロセッサ](#preprocessor) | `#include` / `#define` でどこまで書けるか |
| [標準ライブラリ（`lib.h`）](#stdlib) | 呼べる関数（`printf` / `malloc` など）とその宣言 |
| [到達範囲: 機能 → 導入コマ → 検証テスト](#feature-map) | 「この機能はどのコマで書けるようになるか」「どのテストで確かめるか」 |
| [除外機能の一覧](#excluded) | 「なぜこれが通らないのか」「配列・`switch` は書けるのか」 |
| [ISO C との関係と移行上の注意](#isoc) | gcc で通るのか、本物の C と違うのはどこか |
| [実行時の意味](#semantics) | サイズ・整列、評価順序、未定義動作 |
| [形式文法（EBNF）](#grammar) | パーサを自作するとき、構文エラーの原因を突き止めるとき |

コンパイルが通らない理由を探しているなら、まず [除外機能の一覧](#excluded) を見る。
実装が動かない理由を探しているなら [`testing.md`](./testing.md) の症状表を見る。

---

<a id="lex"></a>

## 字句

- 文字集合は ASCII、行終端は LF。空白(スペース・タブ・改行)はトークンの区切り。
- コメントは `//` から行末まで。**ブロックコメント `/* */` はない。**
- キーワードは次の **12 語のみ**:

  ```
  int  char  void  struct  if  else  while  for  break  continue  return  sizeof
  ```

  これ以外の C のキーワード(`typedef`、`switch`、`unsigned` など)は予約されず、
  識別子として使える(例外 E2。ただし「移行上の注意」の命名規約を参照)。
- 識別子: `(英字 | _)(英字 | 数字 | _)*`。先頭 `_` 可。キーワード 12 語を除く。
- 字句解析は最長一致。例: `a+++b` は `a` `++` `+` `b` と切り出され、
  後置 `++` がないため構文エラーになる。

---

<a id="types"></a>

## 型

```
int          4 バイト符号付き整数（32 ビット 2 の補数）
char         1 バイト文字 / 整数（signed）
T *          ポインタ（多段可: int **pp）。サイズ = 8 バイト
void *       汎用ポインタ。任意の T * と相互に暗黙変換（キャスト不要）
void         関数の戻り値型としてのみ使用
struct Tag   複合型（タグ必須）
```

- struct の定義・前方宣言は**ファイルスコープのみ**。フィールドは
  int・char・ポインタに限り(struct 値の入れ子なし)、1 フィールド 1 宣言子。
- 自己参照・相互参照は前方宣言+ポインタで書ける:

  ```c
  struct Node;                      // 前方宣言（なくてもよい: 定義中の自己参照は可）
  struct Node { int val; struct Node *next; };
  ```

- **struct 変数は宣言できるが、struct 値の代入・実引数・戻り値は不可**
  (`.` によるフィールドアクセスと `&s` は可)。struct の受け渡しはポインタで行う。
- 除外: `float` `double` `long` `short` `unsigned` `union` `enum`、配列、`typedef`

---

<a id="literals"></a>

## リテラル

```
42           整数リテラル（10 進のみ。上限 2147483647、超過はコンパイルエラー）
'a'          文字リテラル（int として扱う。1 文字ちょうど）
"hello"     文字列リテラル（静的領域に配置、char * として参照。内容の変更は未定義）
```

- 整数リテラルは `0` または先頭が非 0 の数字列。8 進・16 進・2 進表記、接尾辞はない。
- エスケープは 6 種のみ: `\n` `\t` `\\` `\'` `\"` `\0`

---

<a id="operators"></a>

## 演算子

優先順位が高い順に示す。

```
一次:   リテラル  識別子  ( 式 )
後置:   p[i]  s.field  p->field  f(args)
単項:   - （負号）  ! （論理否定）  * （間接参照）  & （アドレス取得）
        ++ -- （前置のみ）  sizeof(型名)
乗除:   *  /  %
加減:   +  -   （ポインタ ± int を含む。尺度は指し先型のサイズ）
関係:   <  >  <=  >=   （int/char のみ。ポインタの関係比較はない）
等値:   ==  !=  （int/char 同士、ポインタ同士、ポインタと 0）
論理積: &&   （両辺を必ず評価する。短絡しない）
論理和: ||   （両辺を必ず評価する。短絡しない）
条件:   a ? b : c   （右結合）
代入:   =   （右結合。左辺は単項式で lvalue）
```

- 算術は int で行われ、char は int へ昇格される(値保存)。int から char への
  縮小は代入時のみ(下位 8 ビット)。
- 整数除算 `/` と剰余 `%` は**0 方向へ切り捨てる**(商の絶対値を切り捨てる。
  C99 以降の ISO C、および RV64 の `div`/`rem` 命令と一致する)。剰余の符号は
  被除数と同じになる(例: `-7 / 2` は `-3`、`-7 % 2` は `-1`)。
- 関係(`< > <= >=`)・等値(`== !=`)・論理(`&& ||`)演算子、および単項 `!` の
  結果は int 型の `0` または `1` である(RV64 の `slt`/`seqz` が自然に返す値
  であり、C と同じ)。
- `p[i]` は `*(p + i)` の略記。`sizeof` は型名形式のみで、結果型は int(例外 E1)。
- ポインタ演算は「ポインタ ± int」のみ。ポインタ同士の減算と `void *` への
  算術はない。
- **`&&` `||` は短絡しない**(例外 E3)。左辺の値にかかわらず右辺も評価される。
  ISO C との重要な差異であり、`p != 0 && p->val > 0` のように
  「左辺が偽なら右辺は評価されない」ことに頼った書き方は本仕様ではできない
  (条件は 2 つの `if` に分ける)。短絡する `&&` / `||` の実装は発展 S1 で扱う。
- 前置 `++`/`--` の左辺は 1 回だけ評価される。
- 除外: 複合代入(`+=` `-=` `*=` `/=` `%=`。発展 L2 で追加する)、
  ビット演算・シフト(`~` `&` `^` `|` `<<` `>>`)、後置 `++`/`--`、
  `(type)expr` キャスト、カンマ演算子、`sizeof 式`、関数ポインタ経由の呼出し

---

<a id="declarations"></a>

## 宣言

```c
int x;              // 局所変数。初期化子は書けない（値は不定）
int *p;             // ポインタ変数
struct Node *q;     // struct へのポインタ
struct Point pt;    // struct 変数
int g;              // グローバル変数（0 に初期化される）
```

- **1 宣言 1 宣言子。初期化子はない**(`int x = 42;` は書けない)。
  初期値は代入文で設定する。グローバル変数は 0 初期化が保証される
  (ポインタは null になる)。
- 宣言位置は**ファイルスコープと関数本体の先頭のみ**(2 層スコープ)。
  入れ子ブロックには文だけを書く。`for` 内の宣言もない。
- **入れ子ブロック `{ ... }` は新しいスコープを作らない。**
  関数本体の先頭で宣言した名前は、その関数のどのブロックからも同じ変数を指す。
  宣言できる場所が 2 層に限られるため、ブロック単位の隠蔽(シャドーイング)は
  起きない。隠蔽は「局所変数・仮引数が同名のグローバル変数を隠す」1 種類だけで、
  **同名のローカル(仮引数を含む)は常にグローバルを隠す**(標準的な C の挙動)。
  名前の解決は局所 → 大域の順に行う。
- 仮引数とローカル変数の名前が衝突する場合(同じ関数スコープ内の重複宣言)は
  **コンパイルエラー**とする。仮引数とローカルは同一スコープの名前として扱われる。
- **再宣言・再定義規則は標準的な C の規則に従う**: 同一スコープでの同じ名前の
  再定義(変数の二重定義、struct タグの再定義)はコンパイルエラー。ただし
  関数は、戻り値型・引数型列・可変長性がすべて一致する再宣言(プロトタイプの
  繰返し)を許す(定義できるのは 1 回まで)。struct の前方宣言の繰返しも許す。
- `static` / `extern` / `const` などの記憶クラス・修飾子はない。

---

<a id="statements"></a>

## 文・制御構造

```c
if (cond) { ... }
if (cond) { ... } else { ... }   // else は最も内側の if に結合

while (cond) { ... }

for (init; cond; step) { ... }   // 3 式は各省略可。宣言は不可

return expr;
return;            // void 関数
break;             // ループ内のみ
continue;          // ループ内のみ。step へ合流
```

- 条件式はスカラー型(int・char・ポインタ)。真偽は「0(ポインタなら null)と
  等しくないこと」。
- 除外: `switch`, `goto`, `do-while`, ラベル文

---

<a id="functions"></a>

## 関数

```c
// プロトタイプ（引数名必須）
int add(int a, int b);

// 定義
int add(int a, int b) {
    return a + b;
}

// 可変長引数（外部プロトタイプ限定。固定引数 1 個以上の後にのみ書ける）
int printf(char *fmt, ...);
```

- 引数なしは `()` と書く(`(void)` は受理しない)。`()` は「0 引数」の意味で、
  個数・型が合わない呼出しはコンパイルエラー。
- 呼出しには事前の宣言(プロトタイプまたは定義)が必要。再帰可。
- 引数型は int / char / ポインタ。戻り値型はそれに `void` を加えた 4 種
  (struct 値の引数・戻り値はない)。
- 可変長 `...` の定義は書けない(宣言のみ)。可変部の実引数はスカラー型に限り、
  char は int へ昇格して渡される。
- エントリポイントは `int main()` または `int main(int argc, char **argv)`。

---

<a id="preprocessor"></a>

## プリプロセッサ

```c
#include "file.h"      // "..." 形式のみ。<...> はない
#define NAME value     // オブジェクト形式マクロのみ（定数置換）
```

- 指令は行単位(行頭の `#` から改行まで)で、この 2 種のみ。
- `#include` は入れ子可。**循環取込みはエラー**。同一ファイルの(非循環な)
  再取込みは特別扱いせず、通常の再宣言・再定義規則に従う
  (struct タグの再定義はエラーになるため、共有ヘッダはルートから 1 回だけ
  取り込む構成を推奨)。
- `#define` の**置換は 1 段のみ**。置換結果にマクロ名が含まれる場合はエラー
  (マクロからマクロを参照する書き方は使えない)。実装はこのエラーの診断で
  「マクロの多段参照は使えない」ことを利用者に示すことが望ましい。
- マクロの再定義は、本体のトークン列が同一の場合に限り許す。
- 除外: 関数形式マクロ `#define F(x)`、条件コンパイル `#ifdef` など

---

<a id="stdlib"></a>

## 標準ライブラリ（`lib.h`）

宣言のみ提供する。Linux/RV64(LP64)では全シンボルをそのまま libc に
リンクして解決できる(追加実装なしで動く)。

```c
struct FILE;                                    // 不透明型。前方宣言のみで完全化しない

int  printf(char *fmt, ...);                    // stdout へ書式出力
int  fprintf(struct FILE *f, char *fmt, ...);   // ストリームへ書式出力
struct FILE *fdopen(int fd, char *mode);        // fd をストリーム化（fd 2 = 標準エラー）
struct FILE *fopen(char *path, char *mode);     // ファイルを開く。失敗時 NULL
int  fread(void *buf, int size, int n, struct FILE *f);
int  fclose(struct FILE *f);
void *malloc(int size);                         // 失敗時 NULL
void exit(int code);

#define NULL 0
```

- タグ `FILE` はこの仕様の名前であり(リンクは関数シンボル名だけで行われる)、
  libc 内部の型名には依存しない。
- 標準エラーへの出力は `fdopen(2, "w")` で得たストリームへの `fprintf` で行う。
- `strcmp` / `strlen` 相当は提供しない(純粋な文字列走査は言語内で書けるため、
  必要なら自作する)。
- 書式文字列の意味は ISO C(7.21.6)に従う。

---

<a id="feature-map"></a>

## 到達範囲: 機能 → 導入コマ → 検証テスト

| 区分 | 範囲 |
|------|------|
| 標準トラック(コマ1〜15。final テストの判定範囲) | **本仕様の全機能** |
| 発展トピック | 本仕様の外側の機能・意味論(例: L2 複合代入、S1 短絡評価) |

- 標準トラックのコンパイラは本仕様のすべてを実装する。仕様にあって標準トラックが
  実装しない機能はない。
- 発展トピックは本仕様を**超える**題材である。複合代入 `+= -= *= /= %=` は
  発展 L2 が追加する構文であり(意味論は L2 の資料が定義する)、
  短絡する `&&` / `||` は発展 S1 が本仕様の意味論を C のそれへ寄せる題材である。
- セルフホスト(発展課題 P1)の自己記述ソースは本仕様の機能だけで書く。
  L2 を実装した場合にかぎり、自分のソースで複合代入を使ってもよい。

そのうえで、本仕様の各機能を「どのコマで導入し、どのテストで検証するか」に
1 対 1 で対応させたのが以下の表である。**この表がこの対応の唯一の出典**であり、
`getting_started.md` の全体の流れと `code_example.md` の付録は、
コマ単位の要約としてこの表を参照する。

読み方:

- **導入コマ**は、その機能を原稿が初めて説明する回である。
- **代表テスト**のパスは `workbook/` からの相対パス。
  `python3 scaffold/test_runner.py sessions/NN_xxx` で回の分をまとめて実行できる。
- `final/tests/` の 17 本(`fixed17`)はコマ15 の総合判定であり、
  個々の機能の代表テストとしては挙げない(型対応の前置 `++` だけは例外)。
- **区分**が「発展」の行は本仕様の外側であり、標準トラックの実装対象ではない。

### 字句とリテラル

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| 行コメント `//` | コマ1 | `sessions/02_arithmetic_codegen/tests/div_round.c` | 標準 | Lexer は提供済み |
| 識別子・キーワード 12 語 | コマ1 | 全テスト | 標準 | Lexer は提供済み。例外 E2 |
| 整数リテラル | コマ2 | `sessions/02_arithmetic_codegen/tests/add.c` | 標準 | 10 進のみ |
| 文字リテラル `'a'` | コマ8 | `sessions/08_types/tests/char_var.c` | 標準 | `'\0'` は `sessions/11_expr_walk_libc/tests/strlen_literal.c` |
| 文字列リテラルとエスケープ | コマ10 | `sessions/10_strings_data_section/tests/printf_hello.c` | 標準 | 静的領域に置く |

### 型

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| `int` | コマ2 | `sessions/02_arithmetic_codegen/tests/add.c` | 標準 | |
| `char`(昇格と縮小を含む) | コマ8 | `sessions/08_types/tests/char_var.c` | 標準 | `lb` / `sb`。型別のロード / ストアは `load_store_ty.c` |
| `T *`(単段) | コマ7 | `sessions/07_lvalue_rvalue/tests/deref_read.c` | 標準 | |
| 多段ポインタ `int **` | コマ9 | `sessions/09_pointer_arith/tests/ptr_to_ptr.c` | 標準 | `elem_ty_str` を重ねるだけ |
| `void *` と `T *` の暗黙変換 | コマ12 | `sessions/12_struct_malloc_list/tests/void_ptr.c` | 標準 | キャストが無いのでこれが唯一の手段 |
| 戻り値型 `void` | コマ7 | `sessions/07_lvalue_rvalue/tests/void_func.c` | 標準 | `return;` と末尾到達 |
| `struct Tag` の定義・変数・フィールド | コマ12 | `sessions/12_struct_malloc_list/tests/dot_access.c` | 標準 | ファイルスコープのみ |
| struct の自己参照・前方宣言 | コマ12 | `sessions/12_struct_malloc_list/tests/list_sum.c` | 標準 | 不完全型 `struct FILE` はコマ11 の `file_stream.c` |
| struct 値の代入・実引数・戻り値 | — | — | 仕様外 | 本仕様が禁止。ポインタで受け渡す |

### 演算子

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| 算術 `+ - * / %`・単項 `-`・括弧 | コマ2 | `sessions/02_arithmetic_codegen/tests/prec.c` | 標準 | |
| `/` `%` の丸め(0 方向へ切り捨て) | コマ2 | `sessions/02_arithmetic_codegen/tests/div_round.c` | 標準 | 剰余の符号は被除数と同じ |
| 関係 `< > <= >=` | コマ4 | `sessions/04_if_else/tests/compare.c` | 標準 | `>` `>=` は Parser が正規化 |
| 等値 `== !=` | コマ4 | `sessions/04_if_else/tests/compare.c` | 標準 | ポインタと `0` の比較は `sessions/12_struct_malloc_list/tests/list_sum.c` |
| 比較・論理演算の結果が int の `0` / `1` | コマ4 | `sessions/04_if_else/tests/rel_value.c` | 標準 | |
| 論理 `&&` `\|\|`(短絡しない) | コマ13 | `sessions/13_globals_scope/tests/logical_ops.c` | 標準 | 例外 E3 |
| 単項 `!` | コマ13 | `sessions/13_globals_scope/tests/logical_ops.c` | 標準 | |
| 条件 `? :` | コマ4 | `sessions/04_if_else/tests/ternary.c` | 標準 | 選ばれた腕だけを評価する |
| 代入 `=` | コマ3 | `sessions/03_variables/tests/chain_assign.c` | 標準 | 右結合。左辺は lvalue |
| 前置 `++` `--`(int) | コマ5 | `sessions/05_loops/tests/incr_loop.c` | 標準 | |
| 前置 `++`(ポインタ、型対応) | コマ9 | `sessions/09_pointer_arith/tests/ptr_incdec.c` | 標準 | 指し先型のサイズだけ進む |
| `&`(アドレス取得)・`*`(間接参照) | コマ7 | `sessions/07_lvalue_rvalue/tests/deref_write.c` | 標準 | |
| ポインタ ± int(尺度は指し先型) | コマ9 | `sessions/09_pointer_arith/tests/ptr_arith.c` | 標準 | |
| 添字 `p[i]` | コマ9 | `sessions/09_pointer_arith/tests/ptr_sum.c` | 標準 | `*(p + i)` の略記 |
| `.` と `->` | コマ12 | `sessions/12_struct_malloc_list/tests/arrow_access.c` | 標準 | |
| 関数呼出し `f(args)` | コマ6 | `sessions/06_functions_recursion/tests/call_add.c` | 標準 | 識別子直呼びのみ |
| `sizeof(型名)` | コマ9 | `sessions/09_pointer_arith/tests/sizeof_type.c` | 標準 | struct への適用はコマ12 の `sizeof_test.c`。例外 E1 |
| 複合代入 `+= -= *= /= %=` | 発展 L2 | `advanced/L2_compound_assign/tests/` | 発展 | 本仕様の外 |
| 短絡する `&&` `\|\|` | 発展 S1 | `advanced/S1_shortcircuit/tests/` | 発展 | 本仕様の外 |

### 宣言とスコープ

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| ローカル変数宣言(初期化子なし) | コマ3 | `sessions/03_variables/tests/single.c` | 標準 | 関数本体の先頭のみ |
| 入れ子ブロックが新しいスコープを作らない | コマ4 | `sessions/04_if_else/tests/nested_block.c` | 標準 | 2 層スコープ |
| グローバル変数(0 初期化) | コマ13 | `sessions/13_globals_scope/tests/global_init.c` | 標準 | |
| ローカルによるグローバルの隠蔽 | コマ13 | `sessions/13_globals_scope/tests/global_local_shadow.c` | 標準 | 隠蔽はこの 1 種類だけ |
| 再宣言・再定義規則、仮引数との名前衝突 | コマ13 | — | 標準 | コンパイルエラーの診断。下の「テストを持たない項目」を参照 |

### 文と制御構造

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| `if` / `else` / `else if` | コマ4 | `sessions/04_if_else/tests/if_elseif.c` | 標準 | `else` は最も内側の `if` に結合 |
| ブロック `{ }` | コマ4 | `sessions/04_if_else/tests/nested.c` | 標準 | |
| `while` | コマ5 | `sessions/05_loops/tests/while_sum.c` | 標準 | |
| `for` | コマ5 | `sessions/05_loops/tests/for_count.c` | 標準 | 宣言は書けない |
| `break` | コマ5 | `sessions/05_loops/tests/break_loop.c` | 標準 | |
| `continue` | コマ5 | `sessions/05_loops/tests/continue_odd.c` | 標準 | step へ合流 |
| `return expr;` | コマ2 | `sessions/02_arithmetic_codegen/tests/add.c` | 標準 | 共通エピローグはコマ4 |
| `return;`(void 関数) | コマ7 | `sessions/07_lvalue_rvalue/tests/void_func.c` | 標準 | |
| 空文 `;`・`for` の 3 式の省略 | コマ5 | — | 標準 | 文法上は書けるが単独のテストは無い |

### 関数

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| 関数定義・仮引数・戻り値 | コマ6 | `sessions/06_functions_recursion/tests/call_add.c` | 標準 | 引数なしは `()` |
| プロトタイプ宣言・相互再帰 | コマ6 | `sessions/06_functions_recursion/tests/mutual_rec.c` | 標準 | |
| 再帰 | コマ6 | `sessions/06_functions_recursion/tests/fib_rec.c` | 標準 | |
| 可変長引数の外部プロトタイプと呼出し | コマ10 | `sessions/10_strings_data_section/tests/printf_number.c` | 標準 | 定義は書けない |
| `int main()` | コマ2 | 全テスト | 標準 | |
| `int main(int argc, char **argv)` | コマ9 | `sessions/09_pointer_arith/tests/main_argv.c` | 標準 | |

### プリプロセッサ

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| `#include "..."` | コマ10(`lib.h`)・コマ14(自作ヘッダ・入れ子) | `sessions/14_preprocess_multifile/tests/multifile_math.c` | 標準 | 前処理はスキャフォールド提供 |
| `#define`(1 段置換) | コマ14 | `sessions/14_preprocess_multifile/tests/define_min.c` | 標準 | |
| 複数ソースファイルの同時コンパイル | コマ14 | `sessions/14_preprocess_multifile/tests/multifile_global.c` | 標準 | |
| 循環取込み・マクロ多段参照のエラー | コマ14 | — | 標準 | 診断。下の「テストを持たない項目」を参照 |

### 標準ライブラリ（`lib.h`）

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| `printf` | コマ10 | `sessions/10_strings_data_section/tests/printf_number.c` | 標準 | |
| `fprintf` / `fdopen` / `fopen` / `fread` / `fclose` | コマ11 | `sessions/11_expr_walk_libc/tests/file_stream.c` | 標準 | `struct FILE *` は不透明ポインタ |
| `malloc` | コマ9 | `sessions/09_pointer_arith/tests/ptr_sum.c` | 標準 | |
| `exit` | コマ11 | `sessions/11_expr_walk_libc/tests/lib_exit.c` | 標準 | |
| `NULL` | コマ12 | `sessions/12_struct_malloc_list/tests/list_sum.c` | 標準 | `#define NULL 0` |
| `strcmp` / `strlen` 相当 | — | `sessions/11_expr_walk_libc/tests/strlen_literal.c` | 標準 | 提供しない。必要なら自作する |

### 実行時の意味

| 機能 | 導入コマ | 代表テスト | 区分 | 備考 |
|------|---------|-----------|------|------|
| 型のサイズと整列・struct レイアウト | コマ12 | `sessions/12_struct_malloc_list/tests/malloc_struct.c` | 標準 | サイズは `sizeof_test.c` |
| グローバルの 0 初期化 | コマ13 | `sessions/13_globals_scope/tests/global_init.c` | 標準 | |
| 文字列リテラルの静的配置 | コマ10 | `sessions/10_strings_data_section/tests/printf_hello.c` | 標準 | 内容の変更は未定義 |
| 評価順序(`&&` `\|\|` が両辺を評価する) | コマ13 | `sessions/13_globals_scope/tests/logical_ops.c` | 標準 | 例外 E3 |
| 未定義動作 8 種 | — | — | 対象外 | 「動作を定めない」ことを定めた項目なので、動作を確かめるテストは置かない |

### テストを持たない項目

上の表で代表テストが `—` の行は、次のいずれかの理由による。
標準トラックの実装対象からは外れない。

| 項目 | 理由 |
|------|------|
| 再宣言・再定義規則、仮引数との名前衝突、循環取込み、マクロ多段参照 | いずれも**コンパイルエラーの診断**である。テストランナーの判定手段は「終了コード」と「標準出力」の 2 つで、コンパイルが失敗すること自体を期待値にする仕組みを持たない |
| 空文 `;`・`for` の 3 式の省略 | 文法上は書けるが、他の機能と独立に観測できる振舞いがないため単独のテストを置いていない |
| 未定義動作 8 種 | 動作を定めない項目であり、どの結果になっても仕様違反にならない |
| struct 値の代入・実引数・戻り値 | 仕様が受理しない書き方であり、機能として存在しない |

---

<a id="excluded"></a>

## 除外機能の一覧

| 機能 | 代替 |
|------|------|
| 配列(VLA 含む) | `malloc` +ポインタ・添字 `p[i]`、連結リスト |
| `typedef` | `struct Tag` 直書き |
| `enum` | `#define` 定数 |
| `union` | なし |
| `float` `double` `long` `short` `unsigned` | なし(int / char で完結) |
| `switch` | `if/else` 連鎖 |
| `do-while` / `goto` | `while` / なし |
| 後置 `++` / `--` | 前置形 |
| 複合代入 `+= -= *= /= %=` | `x = x + 3` の形（発展 L2 で追加する） |
| ビット演算・シフト | 整列は `/` と `*`、ハッシュは `%`、フラグは個別の int フィールド |
| `(type)expr` キャスト | `void *` 暗黙変換 |
| カンマ演算子 | 文の列 |
| `sizeof 式` | `sizeof(型名)` |
| 関数ポインタ | 直接呼出し+分岐 |
| 可変長引数関数の定義 | 外部プロトタイプのみ許可 |
| 初期化子(大域・局所) | 代入文(大域は 0 初期化) |
| 複数宣言子(`int a, b;`) | 分割宣言 |
| `(void)` 引数表記 | `()` |
| 関数形式マクロ / `#ifdef` | なし |

---

<a id="isoc"></a>

## ISO C との関係と移行上の注意

基準は ISO C11(N1570)。本仕様の受理するプログラムは、次の 3 件を除き
ISO C の真部分集合である(C23 を基準にしても採用・除外の判断は変わらない)。

**例外 E1 — `sizeof` の結果型は int。**
ISO では符号なしの `size_t`。本仕様は符号なし整数型を持たないため int とする。
このサブセットの範囲では観測できる差はないが、通常の C では比較や
書式指定(`%zu`)で差が出る。

**例外 E2 — 予約語は使用 12 語のみ。**
ISO では全キーワードが識別子として使えないが、本仕様では `typedef` や
`switch` を識別子に使える。ただし次の命名規約に従うこと:

> **命名規約: C のキーワードを識別子に使わない。**
> 予約されていない C キーワード(C23 の `bool` `true` `false` `nullptr` を含む)を
> 識別子に使ったプログラムは、本仕様では合法でも通常の C コンパイラでは
> コンパイルできない。セルフホストでは第 1 段(Stage 0)を gcc でビルドするため、
> この規約を破るとビルドが壊れる。

**例外 E3 — `&&` `||` が短絡しない。**
ISO では左辺だけで結果が定まる場合、右辺は評価されない。本仕様では両辺を必ず
評価する(演算子表・「評価順序」節を参照)。構文は ISO C と同じだが**意味が違う**
ため、`p != 0 && p->val > 0` のような ISO C では安全なイディオムが、本仕様では
NULL 参照になる。この差を埋めるのが発展 S1 である。

このほか、通常の C から見ると次の点が狭い(いずれも「ISO で合法な書き方の
一部だけを受理する」制限であり、例外ではない):

- マクロからマクロを参照する `#define` は書けない(1 段置換)。
- include guard(`#ifdef`)がないため、共有ヘッダはルートから 1 回だけ取り込む。
- 文字列リテラルは `char *` として型付けされる(配列型がないため。
  観測できる差はない)。

---

<a id="semantics"></a>

## 実行時の意味

### サイズ・整列・レイアウト

| 型 | サイズ | 整列 |
|----|--------|------|
| `char` | 1 | 1 |
| `int` | 4 | 4 |
| ポインタ | 8 | 8 |
| `struct` | 下記 | 最大フィールドの整列 |

struct のフィールドは宣言順に配置し、各フィールドのオフセットはその整列へ
切り上げる。struct 全体のサイズは struct の整列の倍数へ切り上げる。
`sizeof` はこの規則で定まる値を返す。null ポインタの表現は全ビット 0。

### 初期化と記憶域

- グローバル変数は 0 に初期化される(ポインタは null)。
- 局所変数・仮引数は自動記憶域。局所変数の初期値は不定。
- 文字列リテラルは静的記憶域に置かれ、内容の変更は未定義。

### 評価順序

- `&&` `||` は左から**両辺を評価する（短絡しない）**。左辺の値が結果を決める場合
  (`0 && e`、`1 || e`)でも右辺 `e` は評価され、その副作用は起こる。
  ISO C との差異である(例外 E3)。短絡する版は発展 S1 で実装する。
- `?:` は条件を評価してから選ばれた腕だけを評価する(こちらは ISO C と同じ)。
- 代入は右辺の評価と左辺の lvalue 決定の後に格納する。
- それ以外の二項演算のオペランド間、および実引数間の評価順序は未規定。

### 未定義動作

次はコンパイルエラーにならず、実行時の動作が未定義である:

1. 符号付き整数のオーバーフロー
2. 0 による除算・剰余(`INT_MIN` はこの仕様の整数リテラル上限
   (2147483647)により単項 `-` とリテラルの組合せで書けないため、
   `INT_MIN / -1` は本仕様の範囲では到達不能である)
3. 不正なポインタ参照(null・未確保領域・確保領域外、ポインタ演算の範囲逸脱)
4. 文字列リテラルの内容の変更
5. 未初期化の局所変数の値の使用
6. 非 void 関数が `return` なしで終端に達した後、呼出し側が戻り値を使うこと
7. 可変長部の実引数と `printf` 系書式の不一致
8. 不完全型(定義のない前方宣言のみの struct。例: `struct FILE`)への `sizeof`
   の適用。診断必須エラーにはしない(実装が検出してエラーにするかは処理系
   定義)。

これに対し、型規則違反・構文違反・整数リテラルの範囲超過・`#define` の
置換規則違反・循環取込みはコンパイル時エラー(診断必須)である。

---

<a id="grammar"></a>

## 形式文法（EBNF）

再帰下降パーサー実装の参照用。文法は文脈自由であり(`typedef` がないため)、
字句解析がシンボルテーブルを参照する必要はない。

この節は最終形である。各コマの時点で書ける範囲だけを抜き出した累積スナップショットは、
コマ1〜14 の各資料の「この回までの言語仕様（EBNF）」節にある。

```
記法:
  rule ::= ...    定義
  A | B           選択（A または B）
  { A }           A の 0 回以上の繰り返し
  [ A ]           省略可能（0 または 1 回）
  ( A )           グループ化
  'token'         終端記号（キーワード・記号）
  UPPER           字句トークン（下部に定義）
```

反復 `{ ... }` で表した二項演算子列の構文木は左結合として構成する。
右結合の規則は再帰で直接表している。

### 前処理

指令行(行頭の `#` から改行まで)は構文解析より前に処理され、
以下の構文には現れない。

```ebnf
include_dir ::= '#' 'include' '"' FILENAME '"' NEWLINE
define_dir  ::= '#' 'define' IDENT { TOKEN } NEWLINE
```

`FILENAME` は `"` と改行を除く 1 文字以上の文字列。`{ TOKEN }` は改行までの
トークン列(0 個以上)。

### 型

型は、書ける位置ごとに 4 つの非終端記号で表す。

```ebnf
stars       ::= '*' { '*' }

scalar_type ::= 'int'  [ stars ]
              | 'char' [ stars ]
              | 'void' stars
              | 'struct' IDENT stars

obj_type    ::= scalar_type
              | 'struct' IDENT

ret_type    ::= scalar_type
              | 'void'

type_name   ::= obj_type
```

この構成により次の制約が構文レベルで決まる:
`void` 単独の変数・引数・フィールドは書けない(`void` は `*` を伴うか
戻り値型のみ)、struct 値の引数・戻り値・フィールドは書けない、
`sizeof(void)` は書けない。

### トップレベル

```ebnf
program       ::= external_decl { external_decl }

external_decl ::= struct_decl
                | var_decl
                | func_proto
                | func_def

struct_decl   ::= 'struct' IDENT '{' field_decl { field_decl } '}' ';'
                | 'struct' IDENT ';'                /* 前方宣言 */

field_decl    ::= scalar_type IDENT ';'

var_decl      ::= obj_type IDENT ';'
```

プログラムは 1 個以上の外部宣言からなる(空プログラムは不可)。
struct 定義はファイルスコープのみ、タグ必須、フィールドは 1 個以上。
初期化子は存在しない。

### 関数

```ebnf
param       ::= scalar_type IDENT
param_list  ::= param { ',' param }

func_proto  ::= ret_type IDENT '(' [ param_list [ ',' '...' ] ] ')' ';'
func_def    ::= ret_type IDENT '(' [ param_list ] ')' func_body

func_body   ::= '{' { var_decl } { stmt } '}'
```

引数なしは `()`(`(void)` は受理しない)。仮引数は名前必須。
`...` はプロトタイプ限定で、1 個以上の固定引数の後にのみ書ける
(`(...)` 単独形は導出できない)。局所変数の宣言は関数本体の先頭のみで、
入れ子ブロックは宣言を含まない。

### 文

```ebnf
stmt        ::= expr_stmt
              | block
              | if_stmt
              | while_stmt
              | for_stmt
              | 'break' ';'
              | 'continue' ';'
              | 'return' [ expr ] ';'

expr_stmt   ::= [ expr ] ';'

block       ::= '{' { stmt } '}'

if_stmt     ::= 'if' '(' expr ')' stmt [ 'else' stmt ]

while_stmt  ::= 'while' '(' expr ')' stmt

for_stmt    ::= 'for' '(' [ expr ] ';' [ expr ] ';' [ expr ] ')' stmt
```

`else` は最も内側の未対応 `if` へ結合する(dangling-else は最近傍優先)。

### 式（優先順位: 低い順に列挙）

```ebnf
expr        ::= assign_expr     /* カンマ演算子はない */

assign_expr ::= unary_expr '=' assign_expr   /* 右結合。複合代入はない */
              | cond_expr

cond_expr   ::= lor_expr [ '?' expr ':' cond_expr ]   /* 右結合 */

lor_expr    ::= land_expr { '||' land_expr }
land_expr   ::= eq_expr   { '&&' eq_expr }
eq_expr     ::= rel_expr  { ( '==' | '!=' ) rel_expr }
rel_expr    ::= add_expr  { ( '<' | '>' | '<=' | '>=' ) add_expr }
add_expr    ::= mul_expr  { ( '+' | '-' ) mul_expr }
mul_expr    ::= unary_expr { ( '*' | '/' | '%' ) unary_expr }

unary_expr  ::= postfix_expr
              | '-'  unary_expr          /* 負号 */
              | '!'  unary_expr          /* 論理否定 */
              | '*'  unary_expr          /* 間接参照 */
              | '&'  unary_expr          /* アドレス取得 */
              | '++' unary_expr          /* 前置インクリメント */
              | '--' unary_expr          /* 前置デクリメント */
              | 'sizeof' '(' type_name ')'

postfix_expr   ::= primary_expr { postfix_suffix }
postfix_suffix ::= '[' expr ']'          /* 添字 */
                 | '.'  IDENT            /* フィールドアクセス */
                 | '->' IDENT            /* ポインタ経由フィールドアクセス */

primary_expr ::= INT_LITERAL
               | CHAR_LITERAL
               | STRING_LITERAL
               | IDENT '(' [ arg_list ] ')'   /* 関数呼び出し（識別子直呼びのみ） */
               | IDENT
               | '(' expr ')'

arg_list    ::= assign_expr { ',' assign_expr }
```

- 代入の左辺の文法カテゴリは `unary_expr`(N1570 6.5.16 と同じ)。
  lvalue 制約は意味解析で検査する。
- `++`/`--` は前置のみ。後置形は `postfix_suffix` に含まれない。
- `sizeof` は型名形式のみ。`type_name` は型キーワード(`int` `char` `void`
  `struct`)で始まるため `sizeof(式)` との構文衝突はなく、`sizeof(x)` は
  構文エラーになる。
- キャストは導出できない(`( expr )` の中に型は書けない)。

### 字句トークン

```ebnf
INT_LITERAL    ::= '0' | NONZERO { DIGIT }
CHAR_LITERAL   ::= "'" ( char_ch | escape ) "'"
STRING_LITERAL ::= '"' { str_ch | escape } '"'
escape         ::= '\n' | '\t' | '\\' | "\'" | '\"' | '\0'

IDENT          ::= ( ALPHA | '_' ) { ALPHA | DIGIT | '_' }
                   /* ただしキーワード 12 語を除く */

ALPHA   = [a-zA-Z]
DIGIT   = [0-9]
NONZERO = [1-9]
```

`char_ch` は `'`・`\`・改行を除く任意の文字、`str_ch` は `"`・`\`・改行を
除く任意の文字。

### 実装の注記（再帰下降）

- `external_decl` の判別: 先頭が `struct` のとき、識別子の次のトークン
  (`{` / `;` / `*` / 識別子)で分岐する。それ以外は `ret_type` を読み、
  識別子の次が `(` なら関数、`;` なら変数。
- `assign_expr` は、まず `cond_expr` として読み、直後が `=` の
  ときに左辺が `unary_expr` 由来であることを検査する方式でよい。
