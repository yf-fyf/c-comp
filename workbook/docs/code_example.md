# コンパイル到達目標コード集

各コマ終了時点で「コンパイルできる最も複雑なプログラム」を示す（コマ1〜16）。
C 版への移植（コマ17〜24）は [`../porting/code_example.md`](../porting/code_example.md) を参照。

## 凡例

| 項目 | 説明 |
|------|------|
| フロントエンド | `mycc.py`（Python 版） |
| 期待する結果 | `qemu-riscv64 ./out; echo $?` の終了コード（標準出力がある場合は別途記載） |
| 検証コマンド | `python3 mycc.py input.c \| riscv64-linux-gnu-gcc -x assembler -static - -o out` |

---

## コマ 1（Phase 0）: 環境構築 + RV64 手書きアセンブリ

コンパイラはまだ存在しない。手書きアセンブリを qemu で動かすことが目標。

```asm
# hello.s — 学生が手で書く
    .global main
main:
    addi    a0, zero, 42    # 戻り値 = 42
    ret
```

```bash
riscv64-linux-gnu-gcc -static hello.s -o hello
qemu-riscv64 ./hello; echo $?   # → 42
```

---

## コマ 2（Phase 0）: AST 理解 + インタープリター

コンパイラはまだ存在しない。教員提供の Lexer/Parser が返す AST を Python で評価する。

```python
# 学生が書くインタープリター
def eval_ast(node):
    if node.kind == 'Num':  return node.val
    if node.kind == 'Add':  return eval_ast(node.lhs) + eval_ast(node.rhs)
    if node.kind == 'Sub':  return eval_ast(node.lhs) - eval_ast(node.rhs)
    if node.kind == 'Mul':  return eval_ast(node.lhs) * eval_ast(node.rhs)
    if node.kind == 'Div':  return eval_ast(node.lhs) // eval_ast(node.rhs)  # 前期は非負数のみ扱うためCと挙動一致
```

評価できる式の例:
```
1 + 2 * 3       → 7
(10 - 3) * 2    → 14
100 / 4 + 1     → 26
```

---

## コマ 3（Phase 1）: コード生成①：算術式

**フロントエンド**: `mycc.py`
**新機能**: 整数定数・四則演算・剰余・カッコ → RV64 アセンブリ出力

```c
int main() {
    return 1 + 2 * 3;
}
```
期待する終了コード: `7`

```c
int main() {
    return (100 - 3 * 7) / 4 + 1;
}
```
期待する終了コード: `20`  （3*7=21, 100-21=79, 79/4=19, 19+1=20）

---

## コマ 4（Phase 1）: コード生成②：変数・代入・シンボルテーブル

**フロントエンド**: `mycc.py`
**新機能**: ローカル変数宣言・代入・複数変数の管理

```c
int main() {
    int a;
    int b;
    int c;
    a = 3;
    b = 5;
    c = a + b;
    return c;
}
```
期待する終了コード: `8`

```c
int main() {
    int x;
    int y;
    x = 10;
    y = x * 2 + 3;
    x = y - x;
    return x;
}
```
期待する終了コード: `13`  （y=23, x=23-10=13）

---

## コマ 5（Phase 1）: 制御構文①：if / else + 三項演算子

**フロントエンド**: `mycc.py`
**新機能**: if / else if / else、比較演算子（`==` `!=` `<` `>` `<=` `>=`）、三項演算子 `?:`

```c
int main() {
    int a;
    int b;
    a = 10;
    b = 3;
    if (a > b) {
        return a - b;
    } else {
        return b - a;
    }
}
```
期待する終了コード: `7`

```c
int main() {
    int score;
    score = 75;
    if (score >= 90) {
        return 4;
    } else if (score >= 70) {
        return 3;
    } else if (score >= 50) {
        return 2;
    } else {
        return 1;
    }
}
```
期待する終了コード: `3`

```c
int main() {
    int a;
    int b;
    a = 3;
    b = 8;
    return a > b ? a : b;
}
```
期待する終了コード: `8`

> **式と文の違い**: `if` は「実行する文」を選ぶ文であり、それ自体は値を持たない。
> 三項演算子 `?:` は「値」を選ぶ式であり、式の中に書ける。
> コード生成はどちらも同じ分岐（`beqz` + ラベル）だが、`?:` は選ばれた腕の値が
> レジスタに残る点だけが異なる。

---

## コマ 6（Phase 1）: 制御構文②：while / for + 前置 `++`/`--`

**フロントエンド**: `mycc.py`
**新機能**: while、for、break、continue、前置 `++`/`--`

```c
int main() {
    int i;
    int sum;
    i = 1;
    sum = 0;
    while (i <= 10) {
        sum = sum + i;
        i = i + 1;
    }
    return sum;
}
```
期待する終了コード: `55`

```c
int main() {
    int i;
    int fib_a;
    int fib_b;
    int tmp;
    fib_a = 0;
    fib_b = 1;
    for (i = 0; i < 10; ++i) {
        tmp   = fib_b;
        fib_b = fib_a + fib_b;
        fib_a = tmp;
    }
    return fib_a;
}
```
期待する終了コード: `55`（フィボナッチ数列の第10項）

> **前置 `++`**: `++i` は `i` の値を 1 増やし、増やした後の値を式の値とする。
> for の更新式の慣用形として使う。実装は「左辺値のアドレスを 1 回だけ求め、
> ロード → +1 → ストア」であり、代入のコード生成の応用で書ける。

---

## コマ 7（Phase 1）: 再帰的な変数宣言収集

**フロントエンド**: `mycc.py`
**新機能**: `collect_decls()` の再帰化（`Block` / `If` / `While` / `For` の内側の宣言も収集）、`_reset_func_state()` への関数状態初期化の統合

このコマは内部整備が主目的。制御構文の内側に変数宣言があっても正しく動くことを確認する。

```c
int main() {
    int x;
    x = 3;
    if (x == 3) {
        int y;     /* 入れ子ブロック内の宣言もフレームに確保する */
        y = 4;
        return x + y;
    }
    return 0;
}
```
期待する終了コード: `7`

```c
int main() {
    int a;
    int b;
    int c;
    int d;
    int e;
    int f;
    a = 1;
    b = 2;
    c = 3;
    d = 4;
    e = 5;
    f = 6;
    return a + b + c + d + e + f;
}
```
期待する終了コード: `21`

> **確認ポイント**: 6変数（48バイト）+ ra/s0（16バイト）= 64バイト（16の倍数 ✓）。
> フレームサイズを `align_to(n, 16)` で16バイト境界に揃え、ローカル変数が0個でも正しく動くこと。

---

## コマ 8（Phase 1）: 関数呼び出し・再帰

**フロントエンド**: `mycc.py`
**新機能**: ユーザー定義関数の宣言・定義・呼び出し、引数（`a0`〜`a7`）、再帰・相互再帰

```c
int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    return fib(10);
}
```
期待する終了コード: `55`

```c
int add(int a, int b) {
    return a + b;
}

int mul(int a, int b) {
    int i;
    int result;
    result = 0;
    for (i = 0; i < b; i = i + 1) {
        result = add(result, a);
    }
    return result;
}

int main() {
    return mul(6, 7);
}
```
期待する終了コード: `42`

---

## コマ 9（Phase 1）: lvalue / rvalue + ポインタ

**フロントエンド**: `mycc.py`
**新機能**: `codegen` / `codegen_lval` の2関数設計、アドレス取得（`&`）、間接参照（`*`）

```c
int main() {
    int x;
    int *p;
    x = 42;
    p = &x;
    return *p;
}
```
期待する終了コード: `42`

```c
int main() {
    int a;
    int *p;
    a = 10;
    p = &a;
    *p = 20;
    return a;
}
```
期待する終了コード: `20`（`*p = 20` が `a` に書き込まれる）

---

## コマ 10（Phase 1）: Type + ポインタ演算

**フロントエンド**: `mycc.py`
**新機能**: `ty_str` 文字列による型サイズ管理、ポインタ演算（`p + n`）、`sizeof(型名)`、`malloc` による連続領域の確保、添字 `p[i]`

> **実装ポイント**: このコマから型サイズの管理をコード生成器に導入する。
> スキャフォールドでは `Type` クラスは使わず、`ty_str` 文字列と
> `size_of_ty_str()` / `elem_ty_str()` ヘルパーで型を扱う。
> ポインタ算術（`p + 1` が `sizeof(*p)` 分だけ加算される）に必要になり、
> 後半の C 移植では `struct Type` に対応させる。
>
> | Cコード | `ty_str` | サイズ |
> |---------|----------|--------|
> | `int a;` | `int` | 4 |
> | `char c;` | `char` | 1 |
> | `int *p;` | `int*` | 8 |
>
> 連続した int の並びは、配列ではなく `malloc(sizeof(int) * N)` で確保した
> 領域として作る。`p[i]` は `*(p + i)` の略記であり、どちらも同じコードになる。
> `sizeof(型名)` は翻訳時に値が決まる定数で、`li` 1 命令に落ちる。

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
期待する終了コード: `15`

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
期待する終了コード: `70`（`p + 2` は `2 * sizeof(int)` バイト進む）

---

## コマ 11（Phase 1）: 文字列リテラル + `printf`

**フロントエンド**: `mycc.py`
**新機能**: 文字列リテラル、`printf`、`#include "lib.h"`

```c
#include "lib.h"

int main() {
    printf("Hello, World!\n");
    printf("%d\n", 42);
    return 0;
}
```
期待する標準出力:
```
Hello, World!
42
```

---

## コマ 12（Phase 2）: 構造体（struct / `.` / `->`）

**フロントエンド**: `mycc.py`
**新機能**: `struct` 定義（タグ必須）、メンバアクセス（`.`）、`->` 演算子

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
期待する終了コード: `25`（3² + 4² = 25）

---

## コマ 13（Phase 2）: `sizeof` + `malloc` + 連結リスト

**フロントエンド**: `mycc.py`
**新機能**: 構造体を組み合わせた `sizeof(struct Tag)` + `malloc` による連結リストの構築・走査

```c
#include "lib.h"

struct Node {
    int val;
    struct Node *next;
};

int list_sum(struct Node *head) {
    int sum;
    sum = 0;
    while (head != NULL) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}

struct Node *new_node(int v) {
    struct Node *n;
    n = malloc(sizeof(struct Node));   // struct のサイズを sizeof で求める
    n->val = v;
    n->next = NULL;
    return n;
}

int main() {
    struct Node *a;
    struct Node *b;
    struct Node *c;
    a = new_node(10);
    b = new_node(20);
    c = new_node(30);
    a->next = b;
    b->next = c;
    return list_sum(a);
}
```
期待する終了コード: `60`

---

## コマ 14（Phase 2）: グローバル変数・スコープ管理

**フロントエンド**: `mycc.py`
**新機能**: グローバル変数（`.bss` セクション。0 初期化が保証される）

```c
#include "lib.h"

int call_count;
int total;

int add_and_count(int x) {
    total = total + x;
    call_count = call_count + 1;
    return total;
}

int main() {
    add_and_count(10);
    add_and_count(20);
    add_and_count(30);
    printf("%d\n", total);
    return call_count;
}
```

> **0 初期化の保証**: グローバル変数は明示的に代入しなくても 0 で始まる
> （ポインタなら null）。`.bss` セクションに `.zero` で配置することで、
> OS がプログラム開始時に 0 埋めしてくれる仕組みをそのまま使っている。
期待する標準出力: `60`
期待する終了コード: `3`

---

## コマ 15（Phase 2）: 複数ファイル・前処理の概念

**フロントエンド**: `mycc.py`
**新機能**: `#include "file.h"`、オブジェクト形式 `#define`

```c
/* math_util.h */
int my_abs(int x);
int my_max(int a, int b);
int my_pow(int base, int exp);
```

```c
/* math_util.c */
int my_abs(int x) {
    if (x < 0) return -x;
    return x;
}

int my_max(int a, int b) {
    if (a > b) return a;
    return b;
}

int my_pow(int base, int exp) {
    int result;
    int i;
    result = 1;
    for (i = 0; i < exp; i = i + 1) {
        result = result * base;
    }
    return result;
}
```

```c
/* main.c */
#include "math_util.h"
#define BASE 2
#define EXP  6

int main() {
    int a;
    int b;
    a = my_abs(-7);
    b = my_pow(BASE, EXP);
    return my_max(a, b);
}
```
期待する終了コード: `64`（max(7, 64) = 64）

---

## コマ 16（Phase 2）: Python 版総合演習・`mycc.py` 統合 ← **標準トラック達成**

**フロントエンド**: `mycc.py`
**確認**: コマ 16 時点で `python3 scaffold/test_runner.py`（`final/mycc.py` + `final/tests/`）を実行し、`fixed17` 全17問の通過を標準トラック完成の目安とする。

### fixed17 テスト一覧（全17問）

| # | ファイル | 出題意図 | 使用機能 |
|---|----------|---------|---------|
| 1 | f01_arith.c | 四則演算の優先順位 | 加減乗除・カッコ |
| 2 | f02_vars.c | 複数ローカル変数の宣言・代入・演算 | ローカル変数・代入 |
| 3 | f03_if.c | if/else if/else チェーン + 関数呼び出し | if/else if/else・比較演算子・関数定義 |
| 4 | f04_while.c | while ループで累積和 | while・変数更新 |
| 5 | f05_for.c | for ループで階乗計算 | for・複数変数同時更新 |
| 6 | f06_break.c | break によるループ脱出 | break・for・if |
| 7 | f07_continue.c | continue によるスキップ | continue・for・if |
| 8 | f08_func.c | 多引数関数の合成呼び出し | 関数定義・引数・戻り値 |
| 9 | f09_recur.c | 再帰呼び出し（フィボナッチ） | 再帰・スタックフレーム |
| 10 | f10_ptr.c | ポインタ渡し swap | &・*・間接代入・void 関数 |
| 11 | f11_ptr_arith.c | malloc 領域の添字・ポインタ走査 | malloc・sizeof・添字・ポインタ引数 |
| 12 | f12_struct.c | 構造体 + ドット・アロー両方 | struct 定義・. / -> 演算子 |
| 13 | f13_global.c | グローバル変数 | .bss セクション・0 初期化・スコープ |
| 14 | f14_string.c | printf 文字列出力 | 文字列リテラル・可変長引数関数呼出 |
| 15 | f15_define.c | #define マクロ + for ループ | #define・for |
| 16 | f16_ternary.c | 三項演算子（値を持つ分岐） | `?:`・入れ子・関数引数 |
| 17 | f17_incr.c | 前置インクリメント | 前置 `++`（int とポインタ） |

> 標準判定用テストは `final/tests/` に配置されている。`python3 scaffold/test_runner.py` で一括実行できる。

固定テストセットの代表例（malloc + ポインタ + 関数の複合）:

```c
// f11: ポインタ演算 — malloc した領域を sizeof と添字・ポインタ走査で使う
#include "lib.h"

int sum(int *a, int n) {
    int i;
    int s;
    s = 0;
    for (i = 0; i < n; ++i) {
        s = s + *(a + i);
    }
    return s;
}

int main() {
    int *a;
    a = malloc(sizeof(int) * 5);
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    a[3] = 5;
    a[4] = 7;
    return sum(a, 5);
}
```
期待する終了コード: `72`

---

## 付録: コマ別機能追加サマリー

| コマ | 追加機能 | 代表的な新出構文 |
|------|---------|----------------|
| 3 | 算術式 | `1 + 2 * 3` |
| 4 | ローカル変数 | `int a; a = 3;` |
| 5 | 条件分岐・三項演算子 | `if (a > b) { ... } else { ... }` / `a > b ? a : b` |
| 6 | ループ・前置 `++` | `while (i < 10) { ... }` / `for (i = 0; i < n; ++i)` |
| 7 | スタックフレーム整備 | 多変数プログラムの安定動作 |
| 8 | 関数定義・再帰 | `int fib(int n) { return fib(n-1) + ...; }` |
| 9 | lvalue/rvalue 設計 | `int *p; p = &x; return *p;` |
| 10 | ポインタ操作 + 型サイズ管理 | `*p = *p + 5;` / `p[i]` / `malloc(sizeof(int) * 5)` |
| 11 | 文字列リテラル・printf | `printf("hello\n")` / `#include "lib.h"` |
| 12 | 構造体 | `struct Point { ... }; struct Point p;` |
| 13 | sizeof + malloc + 連結リスト | `n = malloc(sizeof(struct Node));` |
| 14 | グローバル変数 | `int count;`（関数外） |
| 15 | 複数ファイル・前処理 | `#include "f.h"` / `#define N 10` |
| 16 | 統合確認 | 標準トラック完成（`fixed17` 全通が目安） |

コマ17 以降（C 版への移植）のコード例は [`../porting/code_example.md`](../porting/code_example.md) にある。
