# C 版コンパイル到達目標コード集

C 移植トラック（コマ17〜24）で「コンパイルできる最も複雑なプログラム」を段階ごとに示す。
Python 版（コマ1〜16）のコード例は [`../docs/code_example.md`](../docs/code_example.md) を参照。

## 凡例

| 項目 | 説明 |
|------|------|
| フロントエンド | `mycc`（C 版） |
| 期待する結果 | `qemu-riscv64 ./out; echo $?` の終了コード（標準出力がある場合は別途記載） |
| 検証コマンド | `./mycc input.c > out.s && riscv64-linux-gnu-gcc -static out.s -o out` |

---

## コマ 17（Phase 3）: C移植導入・インフラ移植

**フロントエンド**: `mycc`（C版・算術と変数のみ）
**作業**: Python の `dict` / クラス → C の `struct` + 連結リストへ移植

移植の核となる C 側の基本構造（この回で定義する）:

```c
// type.h — Python 版の ty_str による型管理に対応
typedef struct Type Type;
struct Type {
    int kind;   // TY_INT / TY_CHAR / TY_PTR / TY_ARRAY / TY_STRUCT
    int size;   // sizeof 値
    Type *base; // ptr / array の指す先の型
};

// ast.h の Node（抜粋）
typedef struct Node Node;
struct Node {
    int kind;       // ND_ADD / ND_NUM / ND_VAR / ...
    Node *lhs;
    Node *rhs;
    int val;        // ND_NUM の値
    Type *ty;       // この式の型
    char *name;     // ND_VAR の変数名
};
```

C版コンパイラが最初にコンパイルできるプログラム:

```c
int main() {
    int a;
    int b;
    int c;
    a = 3 + 4 * 2;
    b = a - 1;
    c = b * b;
    return c;
}
```
期待する終了コード: `100`（a=11, b=10, c=100）

---

## コマ 19（Phase 3）: Cコード生成移植①（算術・変数・制御構文）

**フロントエンド**: `mycc`（C版・制御構文まで）
**作業**: Python の `if` / `while` / `for` 生成関数を C に移植

```c
int main() {
    int sum;
    int i;
    sum = 0;
    for (i = 1; i <= 10; i = i + 1) {
        if (i % 2 == 0) {
            sum = sum + i;
        }
    }
    return sum;
}
```
期待する終了コード: `30`（2+4+6+8+10）

```c
int collatz(int n) {
    int steps;
    steps = 0;
    while (n != 1) {
        if (n % 2 == 0) {
            n = n / 2;
        } else {
            n = n * 3 + 1;
        }
        steps = steps + 1;
    }
    return steps;
}

int main() {
    return collatz(27);
}
```
期待する終了コード: `111`（コラッツ数列: 27 → 1 までのステップ数）

---

## コマ 20（Phase 3）: Cコード生成移植②（関数・ポインタ）

**フロントエンド**: `mycc`（C版・関数とポインタまで）
**作業**: プロローグ/エピローグ生成・引数受け渡し・`codegen_lval` を C に移植

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
int swap(int *a, int *b) {
    int tmp;
    tmp = *a;
    *a = *b;
    *b = tmp;
    return 0;
}

int main() {
    int x;
    int y;
    x = 3;
    y = 7;
    swap(&x, &y);
    return x + y * 10;
}
```
期待する終了コード: `37`（swap後 x=7, y=3 → x + y*10 = 7 + 3*10 = 37）

---

## コマ 21（Phase 3）: Cコード生成移植③（配列・構造体・グローバル変数）

**フロントエンド**: `mycc`（C版・Phase 1 全機能）
**作業**: 配列アドレス計算・struct メンバオフセット・`.data` / `.bss` セクション生成を移植

```c
typedef struct Node {
    int val;
    struct Node *next;
} Node;

int list_sum(Node *head) {
    int sum;
    sum = 0;
    while (head != 0) {
        sum = sum + head->val;
        head = head->next;
    }
    return sum;
}

int main() {
    Node a;
    Node b;
    Node c;
    a.val = 10;  a.next = &b;
    b.val = 20;  b.next = &c;
    c.val = 30;  c.next = 0;
    return list_sum(&a);
}
```
期待する終了コード: `60`

このコマ終了時点で **C版 mycc が Phase 1 相当の全テストを通過する**。

```bash
python3 scaffold/test_runner.py --compiler ./mycc --tests final/tests
# [PASS] 01_arithmetic: OK
# [PASS] 02_variables:  OK
# [PASS] 03_control:    OK
# [PASS] 04_functions:  OK
# [PASS] 05_pointers:   OK
# [PASS] 06_structs:    OK
```

---

## コマ 22（Phase 3）: Lexer / Parser 自作導入

**フロントエンド**: `mycc`（C版・自作 Lexer / Parser へ移行中）
**作業**: 教員提供 Lexer/Parser を読み解いた後、C で自前実装に挑戦する

Lexer の核心部:

```c
// lexer.h — トークン種別
#define TK_NUM   0   // 整数リテラル
#define TK_IDENT 1   // 識別子
#define TK_IF    2   // if
#define TK_WHILE 3   // while
#define TK_EOF   100 // 終端

typedef struct Token Token;
struct Token {
    int kind;
    int val;      // TK_NUM の値
    char *str;    // TK_IDENT の文字列先頭
    int len;      // 文字列長
    Token *next;
};
```

Parser の骨格（再帰下降、EBNF の階層に 1:1 対応）:

```c
Node *parse_assign();      // =  （右結合）
Node *parse_lor();         // ||
Node *parse_land();        // &&
// ...（優先順位の低い順に parse_* 関数を定義）
Node *parse_postfix();     // [] -> .
Node *parse_primary();     // 数値 / 文字 / 文字列 / 識別子 / 関数呼び出し / ( expr )
```

自作 Lexer/Parser 完成後、C版 mycc で全テストを再検証する:

```bash
python3 scaffold/test_runner.py --compiler ./mycc --tests final/tests
```

---

## コマ 23（Phase 3）: 総仕上げ

標準・上位各トラックの仕上げに充てる。標準トラックは Python 版デモを整え、上位トラックは C 版の最終調整を行う。

---

## 最終デモ（コマ 24）

| | Python 版（`mycc.py`） | C 版（`mycc`） |
|--|--|--|
| 対象者 | 全員（標準トラック） | 上位トラック達成者 |
| ライブデモ | 到達プログラムの動作と設計レビュー | Fullセルフホスト達成（`stage1` + `fixed15` + 前処理専用2本） |
| 紹介する内容 | 実装上の工夫・詰まったポイント | Python→C 移植での気づき |

**自主課題としてのFullセルフホスト**: C版コンパイラ完成後に取り組んだ上位者は、
最終デモとしてブートストラップの実演を行う。

```bash
# porting/verify_selfhost.sh は雛形。以下を手動実行する。
gcc -o mycc_stage0 src/*.c
./mycc_stage0 src/*.c -o mycc_stage1
python3 scaffold/test_runner.py --compiler ./mycc_stage1 --tests porting/tests
# === FULL SELFHOSTING ACHIEVED ✓ ===
```

---

---

## 付録: 移植の段階サマリー

| コマ | 追加機能 | 代表的な新出構文 |
|------|---------|----------------|
| 17 | C版: 移植導入・インフラ移植（AST・Type・シンボルテーブル） | C版が算術・変数をコンパイル |
| 19 | C版: コード生成移植①（算術・変数・制御構文） | C版が `for` / `if` を出力 |
| 20 | C版: コード生成移植②（関数・ポインタ） | C版が再帰・ポインタ渡しを処理 |
| 21 | C版: コード生成移植③（配列・構造体・グローバル変数） | C版が Phase 1 全機能をカバー |
| 22 | C版: Lexer / Parser 自作導入 | 自作 Lexer/Parser 完成・全テスト再確認 |
| 23 | 総仕上げ | — |
