%{
open Ast_def

(* menhir 生成パーサでは ocamlyacc の Parsing モジュールは位置を返さない。
   位置は各アクション内の $startpos($i) / $symbolstartpos キーワードで取る。 *)
let ln (pos : Lexing.position) = pos.Lexing.pos_lnum
let span (start_pos : Lexing.position) (end_pos : Lexing.position) =
  Some { start_offset = start_pos.pos_cnum; end_offset = end_pos.pos_cnum }

let rec wrap_ptrs base n =
  if n <= 0 then base else TyPtr (wrap_ptrs base (n - 1))

(* 言語仕様の型文法（scalar_type / obj_type / ret_type）を、
   base + '*' の個数を読んでから位置ごとに検証する形で実現する。 *)

(* 変数宣言・sizeof の型名（obj_type）: void 単独は不可 *)
let mk_obj_ty (base, n) =
  if n = 0 && base = TyVoid then failwith "構文解析エラー: void 型の変数は宣言できない"
  else wrap_ptrs base n

(* 引数・struct フィールド（scalar_type）: void 単独・struct 値は不可 *)
let mk_scalar_ty (base, n) =
  if n = 0 then (
    match base with
    | TyVoid -> failwith "構文解析エラー: void 型は使えない（void * は可）"
    | TyStruct _ -> failwith "構文解析エラー: struct 値はここでは使えない（ポインタにする）"
    | t -> t)
  else wrap_ptrs base n

(* 戻り値型（ret_type）: struct 値は不可。void 単独は可 *)
let mk_ret_ty (base, n) =
  if n = 0 then (
    match base with
    | TyStruct _ -> failwith "構文解析エラー: struct 値の戻り値は使えない（ポインタにする）"
    | t -> t)
  else wrap_ptrs base n
%}

%token <int> NUM CHAR_LIT
%token <string> STR IDENT

%token KW_INT KW_CHAR KW_VOID KW_STRUCT
%token IF ELSE WHILE FOR RETURN BREAK CONTINUE SIZEOF

%token PLUS MINUS STAR SLASH PERCENT
%token AMP BANG
%token PLUSPLUS MINUSMINUS QUESTION COLON
%token LT GT ASSIGN
%token SEMI COMMA DOT
%token LPAREN RPAREN LBRACE RBRACE LBRACKET RBRACKET
%token EQEQ NE LE GE ANDAND OROR ARROW
%token ELLIPSIS
%token EOF

%nonassoc LOWER_THAN_ELSE
%nonassoc ELSE

%start program
%type <Ast_def.program> program

%%

program:
| top_list EOF { List.rev $1 }
;

top_list:
| /* empty */ { [] }
| top_list top_opt {
    match $2 with
    | Some t -> t :: $1
    | None -> $1
  }
;

top_opt:
(* struct 定義。AST には出さず、レイアウトだけ Struct_env に登録する
   （scaffold/parser.py も struct 宣言を AST に出さない）。 *)
| KW_STRUCT IDENT LBRACE field_list RBRACE SEMI {
    Struct_env.define $2 (List.rev $4);
    None
  }
(* struct 前方宣言 *)
| KW_STRUCT IDENT SEMI { None }
| decl_type IDENT LPAREN param_clause RPAREN SEMI {
    let params, _variadic = $4 in
    Some (FuncProto { name = $2; ty = mk_ret_ty $1; params; line = ln $startpos($2); span = span $startpos $endpos })
  }
| decl_type IDENT LPAREN param_clause RPAREN func_body {
    let params, variadic = $4 in
    if variadic then failwith "構文解析エラー: 可変長 '...' はプロトタイプ宣言でのみ使える";
    Some (FuncDef { name = $2; ty = mk_ret_ty $1; params; body = $6; line = ln $startpos($2); span = span $startpos $endpos })
  }
| decl_type IDENT SEMI {
    Some (GlobalDecl { name = $2; ty = mk_obj_ty $1; line = ln $startpos($2); span = span $startpos $endpos })
  }
;

decl_type:
| type_base ptrs { ($1, $2) }
;

type_base:
| KW_INT { TyInt }
| KW_CHAR { TyChar }
| KW_VOID { TyVoid }
| KW_STRUCT IDENT { TyStruct $2 }
;

ptrs:
| /* empty */ { 0 }
| ptrs STAR { $1 + 1 }
;

(* フィールドは 1 個以上（言語仕様「トップレベル」参照） *)
field_list:
| field { [$1] }
| field_list field { $2 :: $1 }
;

field:
| decl_type IDENT SEMI { ($2, mk_scalar_ty $1) }
;

(* 可変長 '...' はプロトタイプ限定・固定引数 1 個以上の後のみ。
   仮引数は名前必須。引数なしは () と書く（(void) は受理しない）。 *)
param_clause:
| /* empty */ { ([], false) }
| param_list { (List.rev $1, false) }
| param_list COMMA ELLIPSIS { (List.rev $1, true) }
;

param_list:
| parameter { [$1] }
| param_list COMMA parameter { $3 :: $1 }
;

parameter:
| decl_type IDENT {
    ({ name = Some $2; ty = mk_scalar_ty $1; line = ln $startpos($2); span = span $startpos $endpos } : param)
  }
;

(* 関数本体。局所宣言は先頭にのみ置ける *)
func_body:
| LBRACE local_decls stmt_list RBRACE {
    Block { stmts = $2 @ $3; line = ln $startpos($1); span = span $startpos $endpos }
  }
;

local_decls:
| /* empty */ { [] }
| local_decls local_decl { $1 @ [$2] }
;

local_decl:
| decl_type IDENT SEMI {
    Decl { name = $2; ty = mk_obj_ty $1; line = ln $startpos($2); span = span $startpos $endpos }
  }
;

(* 入れ子ブロックは文のみを含む（宣言は関数本体の先頭のみ） *)
block:
| LBRACE stmt_list RBRACE {
    Block { stmts = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
;

stmt_list:
| /* empty */ { [] }
| stmt_list stmt { $1 @ [$2] }
;

stmt:
| RETURN SEMI {
    Return { expr = None; line = ln $startpos($1); span = span $startpos $endpos }
  }
| RETURN expr SEMI {
    Return { expr = Some $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| BREAK SEMI {
    Break { line = ln $startpos($1); span = span $startpos $endpos }
  }
| CONTINUE SEMI {
    Continue { line = ln $startpos($1); span = span $startpos $endpos }
  }
| IF LPAREN expr RPAREN stmt ELSE stmt {
    If { cond = $3; then_ = $5; else_ = Some $7; line = ln $startpos($1); span = span $startpos $endpos }
  }
| IF LPAREN expr RPAREN stmt %prec LOWER_THAN_ELSE {
    If { cond = $3; then_ = $5; else_ = None; line = ln $startpos($1); span = span $startpos $endpos }
  }
| WHILE LPAREN expr RPAREN stmt {
    While { cond = $3; body = $5; line = ln $startpos($1); span = span $startpos $endpos }
  }
| FOR LPAREN expr_opt SEMI expr_opt SEMI expr_opt RPAREN stmt {
    For { init = $3; cond = $5; step = $7; body = $9; line = ln $startpos($1); span = span $startpos $endpos }
  }
| block { $1 }
| SEMI {
    ExprStmt { expr = None; line = ln $startpos($1); span = span $startpos $endpos }
  }
| expr SEMI {
    ExprStmt { expr = Some $1; line = line_of_expr $1; span = span $startpos $endpos }
  }
;

expr_opt:
| /* empty */ { None }
| expr { Some $1 }
;

(* カンマ演算子はないため expr は assign そのもの *)
expr:
| assign { $1 }
;

assign:
| cond_e ASSIGN assign {
    Assign { lhs = $1; rhs = $3; line = line_of_expr $1; span = span $startpos $endpos }
  }
| cond_e { $1 }
;

(* 条件演算子（右結合） *)
cond_e:
| e_or QUESTION expr COLON cond_e {
    Cond { cond = $1; then_ = $3; else_ = $5; line = line_of_expr $1; span = span $startpos $endpos }
  }
| e_or { $1 }
;

e_or:
| e_or OROR e_and {
    Binary { op = Or; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| e_and { $1 }
;

e_and:
| e_and ANDAND eq {
    Binary { op = And; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| eq { $1 }
;

eq:
| eq EQEQ rel {
    Binary { op = Eq; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| eq NE rel {
    Binary { op = Ne; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel { $1 }
;

rel:
| rel LT add {
    Binary { op = Lt; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel GT add {
    Binary { op = Lt; lhs = $3; rhs = $1; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel LE add {
    Binary { op = Le; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel GE add {
    Binary { op = Le; lhs = $3; rhs = $1; line = ln $startpos($2); span = span $startpos $endpos }
  }
| add { $1 }
;

add:
| add PLUS mul {
    Binary { op = Add; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| add MINUS mul {
    Binary { op = Sub; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| mul { $1 }
;

mul:
| mul STAR unary {
    Binary { op = Mul; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| mul SLASH unary {
    Binary { op = Div; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| mul PERCENT unary {
    Binary { op = Mod; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| unary { $1 }
;

unary:
| MINUS unary {
    Unary { op = Neg; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| BANG unary {
    Unary { op = Not; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| STAR unary {
    Unary { op = Deref; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| AMP unary {
    Unary { op = Addr; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| PLUSPLUS unary {
    Unary { op = PreInc; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| MINUSMINUS unary {
    Unary { op = PreDec; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
(* sizeof は型名形式のみ（sizeof 式 は言語仕様外。sizeof(x) は構文エラー） *)
| SIZEOF LPAREN sizeof_type RPAREN {
    SizeofType { ty = $3; line = ln $startpos($1); span = span $startpos $endpos }
  }
| postfix { $1 }
;

sizeof_type:
| decl_type { mk_obj_ty $1 }
;

postfix:
| primary { $1 }
| postfix LBRACKET expr RBRACKET {
    Index { base = $1; index = $3; line = line_of_expr $1; span = span $startpos $endpos }
  }
| postfix ARROW IDENT {
    Member { base = $1; name = $3; is_arrow = true; line = line_of_expr $1; span = span $startpos $endpos }
  }
| postfix DOT IDENT {
    Member { base = $1; name = $3; is_arrow = false; line = line_of_expr $1; span = span $startpos $endpos }
  }
;

primary:
| NUM {
    Num { value = $1; line = ln $startpos($1); span = span $startpos $endpos }
  }
| CHAR_LIT {
    Num { value = $1; line = ln $startpos($1); span = span $startpos $endpos }
  }
| STR {
    StrLit { value = $1; line = ln $startpos($1); span = span $startpos $endpos }
  }
| IDENT {
    Var { name = $1; line = ln $startpos($1); span = span $startpos $endpos }
  }
| IDENT LPAREN arg_list_opt RPAREN {
    Call { name = $1; args = $3; line = ln $startpos($1); span = span $startpos $endpos }
  }
| LPAREN expr RPAREN { with_expr_span $2 (span $startpos $endpos) }
;

arg_list_opt:
| /* empty */ { [] }
| arg_list { $1 }
;

arg_list:
| expr { [$1] }
| arg_list COMMA expr { $1 @ [$3] }
;
