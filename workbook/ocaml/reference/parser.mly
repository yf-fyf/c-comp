%{
(*
   構文解析。

   support/parser.mly と同じ言語を受理するが、作る木はこちら専用の Ast である。
   言語仕様を変えるときは support/parser.mly と両方直すこと。

   support 版との違い:
   - struct 定義を副作用で表へ登録せず、struct_def として木に出す
   - エラーは位置つきの Diag.Error（support 版は位置なしの failwith）
   - 局所宣言を文の列から分け、関数の locals として持つ
*)

open Ast

(* トップレベルの項目。struct 定義と宣言は別の並びに分けて Ast.program にする *)
type item = Sdef of struct_def | Tdef of top | Nothing

let parse_error pos fmt =
  Diag.error ~phase:Diag.Parse ~line:(Loc.line_of pos) ~col:(Loc.col_of pos) fmt
let loc = Loc.of_positions
let mk_expr desc startpos endpos = { e_desc = desc; e_loc = loc startpos endpos }
let mk_stmt desc startpos endpos = { s_desc = desc; s_loc = loc startpos endpos }

let rec wrap_ptrs base n = if n <= 0 then base else Ctype.Ptr (wrap_ptrs base (n - 1))

(* 言語仕様の型文法（scalar_type / obj_type / ret_type）を、
   base + '*' の個数を読んでから位置ごとに検証する形で実現する。 *)

(* 変数宣言・sizeof の型名（obj_type）: void 単独は不可 *)
let mk_obj_ty pos (base, n) =
  if n = 0 && base = Ctype.Void then parse_error pos "void 型の変数は宣言できない"
  else wrap_ptrs base n

(* 引数・struct フィールド（scalar_type）: void 単独・struct 値は不可 *)
let mk_scalar_ty pos (base, n) =
  if n = 0 then (
    match base with
    | Ctype.Void -> parse_error pos "void 型は使えない（void * は可）"
    | Ctype.Struct _ -> parse_error pos "struct 値はここでは使えない（ポインタにする）"
    | t -> t)
  else wrap_ptrs base n

(* 戻り値型（ret_type）: struct 値は不可。void 単独は可 *)
let mk_ret_ty pos (base, n) =
  if n = 0 then (
    match base with
    | Ctype.Struct _ -> parse_error pos "struct 値の戻り値は使えない（ポインタにする）"
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
%type <Ast.program> program

%%

program:
| top_list EOF {
    let items = List.rev $1 in
    {
      structs = List.filter_map (function Sdef s -> Some s | _ -> None) items;
      tops = List.filter_map (function Tdef t -> Some t | _ -> None) items;
    }
  }
;

top_list:
| /* empty */ { [] }
| top_list top_item { $2 :: $1 }
;

top_item:
(* struct 定義。レイアウトは Layout がこの並びを定義順に畳み込んで決める *)
| KW_STRUCT IDENT LBRACE field_list RBRACE SEMI {
    Sdef { sd_tag = $2; sd_fields = List.rev $4; sd_loc = loc $startpos $endpos }
  }
(* struct 前方宣言。レイアウトを持たないので木には出さない *)
| KW_STRUCT IDENT SEMI { Nothing }
| decl_type IDENT LPAREN param_clause RPAREN SEMI {
    let params, variadic = $4 in
    Tdef
      (Proto
         {
           pt_name = $2;
           pt_ret = mk_ret_ty $startpos($1) $1;
           pt_params = params;
           pt_variadic = variadic;
           pt_loc = loc $startpos $endpos;
         })
  }
| decl_type IDENT LPAREN param_clause RPAREN func_body {
    let params, variadic = $4 in
    if variadic then
      parse_error $startpos($2) "可変長 '...' はプロトタイプ宣言でのみ使える";
    let locals, body = $6 in
    Tdef
      (Func
         {
           fn_name = $2;
           fn_ret = mk_ret_ty $startpos($1) $1;
           fn_params = params;
           fn_locals = locals;
           fn_body = body;
           fn_loc = loc $startpos $endpos;
         })
  }
| decl_type IDENT SEMI {
    Tdef (Global { d_name = $2; d_ty = mk_obj_ty $startpos($1) $1; d_loc = loc $startpos $endpos })
  }
;

decl_type:
| type_base ptrs { ($1, $2) }
;

type_base:
| KW_INT { Ctype.Int }
| KW_CHAR { Ctype.Char }
| KW_VOID { Ctype.Void }
| KW_STRUCT IDENT { Ctype.Struct $2 }
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
| decl_type IDENT SEMI { ($2, mk_scalar_ty $startpos($1) $1) }
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
    { p_name = $2; p_ty = mk_scalar_ty $startpos($1) $1; p_loc = loc $startpos $endpos }
  }
;

(* 関数本体。局所宣言は先頭にのみ置けるので、文の列とは別に返す *)
func_body:
| LBRACE local_decls stmt_list RBRACE { ($2, $3) }
;

local_decls:
| /* empty */ { [] }
| local_decls local_decl { $1 @ [$2] }
;

local_decl:
| decl_type IDENT SEMI {
    { d_name = $2; d_ty = mk_obj_ty $startpos($1) $1; d_loc = loc $startpos $endpos }
  }
;

(* 入れ子ブロックは文のみを含む（宣言は関数本体の先頭のみ） *)
block:
| LBRACE stmt_list RBRACE { mk_stmt (Block $2) $startpos $endpos }
;

stmt_list:
| /* empty */ { [] }
| stmt_list stmt { $1 @ [$2] }
;

stmt:
| RETURN SEMI { mk_stmt (Return None) $startpos $endpos }
| RETURN expr SEMI { mk_stmt (Return (Some $2)) $startpos $endpos }
| BREAK SEMI { mk_stmt Break $startpos $endpos }
| CONTINUE SEMI { mk_stmt Continue $startpos $endpos }
| IF LPAREN expr RPAREN stmt ELSE stmt {
    mk_stmt (If { cond = $3; then_ = $5; else_ = Some $7 }) $startpos $endpos
  }
| IF LPAREN expr RPAREN stmt %prec LOWER_THAN_ELSE {
    mk_stmt (If { cond = $3; then_ = $5; else_ = None }) $startpos $endpos
  }
| WHILE LPAREN expr RPAREN stmt {
    mk_stmt (While { cond = $3; body = $5 }) $startpos $endpos
  }
| FOR LPAREN expr_opt SEMI expr_opt SEMI expr_opt RPAREN stmt {
    mk_stmt (For { init = $3; cond = $5; step = $7; body = $9 }) $startpos $endpos
  }
| block { $1 }
| SEMI { mk_stmt Empty $startpos $endpos }
| expr SEMI { mk_stmt (Expr $1) $startpos $endpos }
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
| cond_e ASSIGN assign { mk_expr (Assign { lhs = $1; rhs = $3 }) $startpos $endpos }
| cond_e { $1 }
;

(* 条件演算子（右結合） *)
cond_e:
| e_or QUESTION expr COLON cond_e {
    mk_expr (Cond { cond = $1; then_ = $3; else_ = $5 }) $startpos $endpos
  }
| e_or { $1 }
;

e_or:
| e_or OROR e_and { mk_expr (Binary { op = Or; lhs = $1; rhs = $3 }) $startpos $endpos }
| e_and { $1 }
;

e_and:
| e_and ANDAND eq { mk_expr (Binary { op = And; lhs = $1; rhs = $3 }) $startpos $endpos }
| eq { $1 }
;

eq:
| eq EQEQ rel { mk_expr (Binary { op = Eq; lhs = $1; rhs = $3 }) $startpos $endpos }
| eq NE rel { mk_expr (Binary { op = Ne; lhs = $1; rhs = $3 }) $startpos $endpos }
| rel { $1 }
;

(* > と >= は左右を入れ替えて < と <= に正規化する。
   木が小さくなるだけでなく、**評価順も入れ替わる**（a > b は b を先に評価する）。
   コード生成の出力はこの順に依存しているので、勝手に直さないこと。 *)
rel:
| rel LT add { mk_expr (Binary { op = Lt; lhs = $1; rhs = $3 }) $startpos $endpos }
| rel GT add { mk_expr (Binary { op = Lt; lhs = $3; rhs = $1 }) $startpos $endpos }
| rel LE add { mk_expr (Binary { op = Le; lhs = $1; rhs = $3 }) $startpos $endpos }
| rel GE add { mk_expr (Binary { op = Le; lhs = $3; rhs = $1 }) $startpos $endpos }
| add { $1 }
;

add:
| add PLUS mul { mk_expr (Binary { op = Add; lhs = $1; rhs = $3 }) $startpos $endpos }
| add MINUS mul { mk_expr (Binary { op = Sub; lhs = $1; rhs = $3 }) $startpos $endpos }
| mul { $1 }
;

mul:
| mul STAR unary { mk_expr (Binary { op = Mul; lhs = $1; rhs = $3 }) $startpos $endpos }
| mul SLASH unary { mk_expr (Binary { op = Div; lhs = $1; rhs = $3 }) $startpos $endpos }
| mul PERCENT unary { mk_expr (Binary { op = Mod; lhs = $1; rhs = $3 }) $startpos $endpos }
| unary { $1 }
;

unary:
| MINUS unary { mk_expr (Unary { op = Neg; operand = $2 }) $startpos $endpos }
| BANG unary { mk_expr (Unary { op = Not; operand = $2 }) $startpos $endpos }
| STAR unary { mk_expr (Unary { op = Deref; operand = $2 }) $startpos $endpos }
| AMP unary { mk_expr (Unary { op = Addr; operand = $2 }) $startpos $endpos }
| PLUSPLUS unary { mk_expr (Unary { op = PreInc; operand = $2 }) $startpos $endpos }
| MINUSMINUS unary { mk_expr (Unary { op = PreDec; operand = $2 }) $startpos $endpos }
(* sizeof は型名形式のみ（sizeof 式 は言語仕様外。sizeof(x) は構文エラー） *)
| SIZEOF LPAREN sizeof_type RPAREN { mk_expr (Sizeof $3) $startpos $endpos }
| postfix { $1 }
;

sizeof_type:
| decl_type { mk_obj_ty $startpos($1) $1 }
;

postfix:
| primary { $1 }
| postfix LBRACKET expr RBRACKET {
    mk_expr (Index { base = $1; index = $3 }) $startpos $endpos
  }
| postfix ARROW IDENT {
    mk_expr (Member { base = $1; field = $3; arrow = true }) $startpos $endpos
  }
| postfix DOT IDENT {
    mk_expr (Member { base = $1; field = $3; arrow = false }) $startpos $endpos
  }
;

primary:
| NUM { mk_expr (Num $1) $startpos $endpos }
| CHAR_LIT { mk_expr (Num $1) $startpos $endpos }
| STR { mk_expr (Str $1) $startpos $endpos }
| IDENT { mk_expr (Var $1) $startpos $endpos }
| IDENT LPAREN arg_list_opt RPAREN {
    mk_expr (Call { name = $1; args = $3 }) $startpos $endpos
  }
(* 括弧つきの式は、位置だけ括弧の外側まで広げて中身をそのまま返す *)
| LPAREN expr RPAREN { { $2 with e_loc = loc $startpos $endpos } }
;

arg_list_opt:
| /* empty */ { [] }
| arg_list { $1 }
;

arg_list:
| expr { [$1] }
| arg_list COMMA expr { $1 @ [$3] }
;
