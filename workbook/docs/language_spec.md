# Core プロファイル — 言語仕様

C サブセットコンパイラが対象とする言語仕様。この教材では凍結された仕様として扱う。

設計原則: **C の核だけ残し、曖昧さと実装コストの高い機能を除外する。**
この仕様で書かれたコンパイラが、この仕様自体をコンパイルできる（セルフホスト可能）。

---

## 型

```
int          4 バイト符号付き整数（LP64）
char         1 バイト文字 / 整数
T *          ポインタ（任意の T、多段ポインタ含む）。サイズ = 8 バイト
void *       汎用ポインタ。任意の T * へ暗黙変換可（キャスト不要）
void         関数の戻り値型としてのみ使用
struct       複合型（ネスト・自己参照ポインタ含む）
typedef      型の別名
```

除外: `float`, `double`, `long`, `short`, `unsigned`, `union`, `enum`

---

## リテラル

```
42           整数リテラル
'a'          文字リテラル（int として扱う）
"hello"      文字列リテラル（.data セクションに配置、char * として参照）
```

---

## 演算子

優先順位が高い順に示す。

```
単項:   - （負号）  ! （論理否定）  ~ （ビット否定）
        * （間接参照）  & （アドレス取得）
        sizeof(型)  sizeof 式
ポインタ: p[i]  p->field  p.field
乗除:   *  /  %
加減:   +  -   （ポインタ ± int を含む）
シフト: <<  >>
比較:   <  >  <=  >=
等値:   ==  !=
ビット: &  ^  |  （この順に優先順位）
論理:   &&  ||
代入:   =           （右辺値を左辺の lvalue に書き込む）
```

除外: `+=` `-=` 等の複合代入、`++`/`--`、`(type)expr` キャスト、三項 `a?b:c`、カンマ演算子

---

## 宣言

```c
int x;                  // ローカル変数（未初期化）
int x = 42;             // ローカル変数（初期化子付き）
int *p = malloc(N);     // ポインタ変数（void* の暗黙変換）
int a[10];              // 固定長配列（定数サイズのみ）
int g;                  // グローバル変数（関数外）
```

宣言は文の先頭で行う（C89 スタイル）。スコープは宣言した関数内。

---

## 文・制御構造

```c
if (cond) { ... }
if (cond) { ... } else { ... }

while (cond) { ... }

for (init; cond; step) { ... }   // init は式のみ（宣言不可）

return expr;
return;            // void 関数
break;
continue;
```

除外: `switch`, `goto`, `do-while`

---

## 関数

```c
// 宣言
int add(int a, int b);

// 定義
int add(int a, int b) {
    return a + b;
}

// 呼び出し
int r = add(1, 2);
```

- ユーザー定義関数（`func_def`）の引数は固定個数のみ（可変長定義は不可）
- 外部関数宣言（`func_proto`）に限り `...` を許可する（例: `int printf(char *fmt, ...);`）
- 可変長宣言関数の呼び出しは、宣言の存在のみ確認し、引数個数・型の厳密検査は行わない
- 戻り値型は任意の型（`void` 含む）
- 再帰呼び出し可

---

## プリプロセッサ

```c
#include "file.h"      // ファイル結合のみ。<...> 形式は不要
#define NAME value     // オブジェクト形式マクロのみ（定数置換）
```

除外: 関数形式マクロ `#define F(x) ...`、条件コンパイル `#ifdef` 等

`#include "file.h"` を自前実装する。
Fullセルフホストを目指す上位トラックでは、仕上げとして `#define` を自前実装へ移行する。

---

## 標準ライブラリ（`lib.h`）

宣言のみ提供。実体はリンク時に libc から解決する。

```c
/* 出力 */
int printf(char *fmt, ...);
int fprintf(FILE *f, char *fmt, ...);

/* ファイル入力 */
typedef struct _IO_FILE FILE;   /* 不完全型。FILE * としてのみ使用 */
FILE *fopen(char *path, char *mode);
int   fread(void *buf, int size, int n, FILE *f);
int   fclose(FILE *f);

/* メモリ */
void *malloc(int size);         /* 戻り値は任意の T * へ暗黙変換 */

/* プロセス */
void exit(int code);

/* 文字列 */
int   strcmp(char *a, char *b);
int   strlen(char *s);
char *strchr(char *s, int c);
```

`NULL` は `#define NULL 0` として `lib.h` に定義する。

---

## 除外機能の一覧

| 機能 | 除外理由 |
|------|---------|
| `float`, `double` | 実装コスト大・教育目的外 |
| `long`, `short`, `unsigned` | `int` 4B で十分 |
| `union`, `enum` | 不要（`#define` で代替） |
| `switch` | 除外（`if/else` で代替） |
| `goto`, `do-while` | 不要 |
| `++` / `--` | 除外（`i = i + 1` スタイルで統一） |
| `+=` `-=` 等の複合代入 | 除外（`=` のみで統一） |
| `(type)expr` キャスト | 不要（`void *` 暗黙変換で代替） |
| `a ? b : c` 三項演算子 | 除外（`if/else` で代替） |
| カンマ演算子 | 不要 |
| ユーザー定義の可変長引数関数（定義） | 実装コスト大 |
| 関数形式マクロ / `#ifdef` | 不要 |
| VLA（可変長配列） | 不要 |

---

## 形式文法（EBNF）

再帰下降パーサー・パーサージェネレーター実装の参照用。

```
記法:
  rule ::= ...    定義
  A | B           選択（A または B）
  { A }           A の 0 回以上の繰り返し
  [ A ]           省略可能（0 または 1 回）
  ( A )           グループ化
  'token'         終端記号（キーワード・記号）
  UPPER           字句トークン（下部に定義）
  /* ... */       注釈
```

### トップレベル

```ebnf
program     ::= { top_decl }

top_decl    ::= prep_dir
              | typedef_decl ';'
              | struct_def ';'
              | func_proto ';'
              | func_def
              | var_decl
```

### プリプロセッサ

```ebnf
prep_dir    ::= '#include' '"' FILENAME '"'
              | '#define'  IDENT { TOKEN } NEWLINE
```

`{ TOKEN }` は改行までの任意のトークン列（オブジェクト形式マクロの値）。

### 型

```ebnf
type        ::= base_type { '*' }

base_type   ::= 'int'
              | 'char'
              | 'void'
              | 'struct' IDENT
              | 'struct' [ IDENT ] '{' { field_decl } '}'
              | TYPEDEF_NAME               /* シンボルテーブルで解決 */

field_decl  ::= type declarator ';'
```

`TYPEDEF_NAME` は `typedef` で登録済みの識別子。字句解析時にシンボルテーブルを参照して
`IDENT` と区別する（文脈依存トークン分類）。

### typedef / struct 定義

```ebnf
typedef_decl ::= 'typedef' type IDENT
               | 'typedef' 'struct' [ IDENT ] '{' { field_decl } '}' IDENT

struct_def   ::= 'struct' IDENT '{' { field_decl } '}'
```

### 宣言子

```ebnf
declarator  ::= IDENT [ '[' INT_LITERAL ']' ]
```

ポインタの `*` は `type` 側に含める（`int *p` は型 `int *`、宣言子 `p`）。

### グローバル変数宣言

```ebnf
var_decl    ::= type declarator [ '=' expr ] ';'
```

### 関数

```ebnf
param       ::= type declarator
param_list  ::= param { ',' param }

func_proto  ::= type declarator '(' ')'
              | type declarator '(' param_list ')'
              | type declarator '(' param_list ',' '...' ')'
              | type declarator '(' '...' ')'
func_def    ::= type declarator '(' [ param_list ] ')' block
```

引数なし関数は `( )` または `( void )` と記述できる（意味は同じ）。
`...` は `func_proto` のみ許可し、`func_def` では禁止する。

### ブロックと文

```ebnf
block       ::= '{' { local_decl } { stmt } '}'
                /* C89 スタイル: 宣言は文より前 */

local_decl  ::= type declarator [ '=' expr ] ';'

stmt        ::= expr_stmt
              | if_stmt
              | while_stmt
              | for_stmt
              | 'return' [ expr ] ';'
              | 'break' ';'
              | 'continue' ';'
              | block

expr_stmt   ::= [ expr ] ';'

if_stmt     ::= 'if' '(' expr ')' stmt [ 'else' stmt ]

while_stmt  ::= 'while' '(' expr ')' stmt

for_stmt    ::= 'for' '(' [ expr ] ';' [ expr ] ';' [ expr ] ')' stmt
                /* init は式のみ。宣言不可 */
```

`else` は最も内側の `if` に結合する（dangling-else は最近傍優先）。

### 式（優先順位：低い順に列挙）

```ebnf
expr        ::= assign_expr

assign_expr ::= unary_expr '=' assign_expr   /* 右結合 */
              | lor_expr
              /* lvalue 制約は意味解析フェーズで検査 */

lor_expr    ::= land_expr    { '||' land_expr }
land_expr   ::= bitor_expr   { '&&' bitor_expr }
bitor_expr  ::= bitxor_expr  { '|'  bitxor_expr }
bitxor_expr ::= bitand_expr  { '^'  bitand_expr }
bitand_expr ::= eq_expr      { '&'  eq_expr }
eq_expr     ::= rel_expr     { ( '==' | '!=' ) rel_expr }
rel_expr    ::= shift_expr   { ( '<' | '>' | '<=' | '>=' ) shift_expr }
shift_expr  ::= add_expr     { ( '<<' | '>>' ) add_expr }
add_expr    ::= mul_expr     { ( '+' | '-' ) mul_expr }
mul_expr    ::= unary_expr   { ( '*' | '/' | '%' ) unary_expr }

unary_expr  ::= '-'      unary_expr          /* 単項負号 */
              | '!'      unary_expr          /* 論理否定 */
              | '~'      unary_expr          /* ビット否定 */
              | '*'      unary_expr          /* 間接参照 */
              | '&'      unary_expr          /* アドレス取得 */
              | 'sizeof' '(' type ')'        /* 型サイズ */
              | 'sizeof' unary_expr          /* 式サイズ */
              | postfix_expr

postfix_expr ::= primary_expr { '[' expr ']'  /* 添字 */
                              | '->' IDENT    /* ポインタ経由フィールドアクセス */
                              | '.'  IDENT    /* 直接フィールドアクセス */
                              }

primary_expr ::= INT_LITERAL
               | CHAR_LITERAL
               | STRING_LITERAL
               | IDENT '(' [ arg_list ] ')'  /* 関数呼び出し */
               | IDENT
               | '(' expr ')'

arg_list    ::= expr { ',' expr }
```

`'&'` と `'*'` の単項／二項の区別はパーサーレベルで解決済み
（単項は `unary_expr`、二項は `mul_expr` / `bitand_expr`）。

### 字句トークン

```ebnf
INT_LITERAL    ::= DIGIT { DIGIT }
CHAR_LITERAL   ::= "'" ( char_ch | escape_seq ) "'"
STRING_LITERAL ::= '"' { str_ch | escape_seq } '"'
escape_seq     ::= '\n' | '\t' | '\\' | "\'" | '\"' | '\0'

IDENT          ::= ( ALPHA | '_' ) { ALPHA | DIGIT | '_' }
                   /* ただしキーワードを除く */

ALPHA  = [a-zA-Z]
DIGIT  = [0-9]
```

キーワード一覧: `int char void struct typedef if else while for return break continue sizeof`
