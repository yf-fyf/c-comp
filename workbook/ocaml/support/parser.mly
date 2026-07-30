%{
open Ast_def

(* menhir 生成パーサでは ocamlyacc の Parsing モジュールは位置を返さない。
   位置は各アクション内の $startpos($i) / $symbolstartpos キーワードで取る。 *)
let ln (pos : Lexing.position) = pos.Lexing.pos_lnum
let span (start_pos : Lexing.position) (end_pos : Lexing.position) =
  Some { start_offset = start_pos.pos_cnum; end_offset = end_pos.pos_cnum }

let rec wrap_ptrs base n =
  if n <= 0 then base else TyPtr (wrap_ptrs base (n - 1))

let combine_array base arr_opt =
  match arr_opt with None -> base | Some n -> TyArray { elem = base; length = n }

let lookup_type name =
  match Typedef_env.find name with
  | Some ty -> ty
  | None -> TyUnknown name

let lookup_struct tag =
  let key = "struct " ^ tag in
  match Typedef_env.find key with
  | Some ty -> ty
  | None -> TyUnknown key

let align_to n align = ((n + align - 1) / align) * align

let build_struct_type tag fields name =
  let offset, fields_with_offset =
    List.fold_left (fun (offset, acc) (fname, fty) ->
        let a = min (size_of_ty fty) 8 in
        let offset = align_to offset a in
        let next = offset + size_of_ty fty in
        (next, ((fname, { offset; ty = fty }) :: acc)))
      (0, []) fields
  in
  let total_size = align_to offset 8 in
  let fields_with_offset = List.rev fields_with_offset in
  let struct_ty = TyStruct { name = tag; fields = fields_with_offset; size = total_size } in
  Typedef_env.set name struct_ty;
  Option.iter (fun t -> Typedef_env.set ("struct " ^ t) struct_ty) tag;
  struct_ty
%}

%token <int> NUM CHAR_LIT
%token <string> STR IDENT TYPE_NAME

%token KW_INT KW_CHAR KW_VOID KW_STRUCT TYPEDEF
%token IF ELSE WHILE FOR RETURN BREAK CONTINUE SIZEOF

%token PLUS MINUS STAR SLASH PERCENT
%token AMP PIPE CARET TILDE BANG
%token LT GT ASSIGN
%token SEMI COMMA DOT
%token LPAREN RPAREN LBRACE RBRACE LBRACKET RBRACKET
%token EQEQ NE LE GE ANDAND OROR SHL SHR ARROW
%token ELLIPSIS
%token EOF

%nonassoc LOWER_THAN_ELSE
%nonassoc ELSE

%start program
%type <Ast_def.program> program

%%

(* 宣言位置での名前 — typedef 直後の先読みや struct タグでは TYPE_NAME になる *)
name_or_type:
| IDENT { $1 }
| TYPE_NAME { $1 }
;

(* typedef で導入する別名。SEMI の次のトークンが字句解析される前に登録する。
   LR の先読みが規則の還元より先に走ると、`typedef struct {...} Pair; Pair x;`
   の2つ目の Pair が IDENT のまま届いて構文エラーになるため（字句フィードバック）。
   型そのものは還元時の build_struct_type が set で上書きする。 *)
typedef_alias:
| name_or_type { Typedef_env.register_forward $1; $1 }
;

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
(* anonymous struct typedef — LBRACE after KW_STRUCT で決定 *)
| TYPEDEF KW_STRUCT LBRACE struct_members RBRACE typedef_alias SEMI {
    let fields = List.rev $4 in
    ignore (build_struct_type None fields $6);
    Some (StructDef { tag = None; fields; name = $6; line = ln $startpos($2); span = span $startpos $endpos })
  }
(* struct typedef with tag — 自己参照の前方登録は build_struct_type 内で行う *)
| TYPEDEF KW_STRUCT name_or_type struct_def_opt typedef_alias SEMI {
    let tag = $3 in
    let fields = List.rev $4 in
    ignore (build_struct_type (Some tag) fields $5);
    Some (StructDef { tag = Some tag; fields; name = $5; line = ln $startpos($2); span = span $startpos $endpos })
  }
(* non-struct typedef — ctype の代わりに KW_STRUCT を含まない型規則を使う *)
| TYPEDEF non_struct_ctype name_or_type SEMI {
    Typedef_env.register_name $3 $2; None
  }
(* 宣言子を伴わない struct 定義（`struct S { ... };` と前方宣言 `struct S;`）。
   型だけ登録して AST には出さない。scaffold/parser.py も同じ扱いにしてある。 *)
| KW_STRUCT name_or_type struct_def_opt SEMI {
    let tag = $2 in
    ignore (build_struct_type (Some tag) (List.rev $3) ("struct " ^ tag));
    None
  }
| ctype name_or_type LPAREN param_clause RPAREN SEMI {
    Some (FuncProto { name = $2; ty = $1; params = $4; line = ln $startpos($2); span = span $startpos $endpos })
  }
| ctype name_or_type LPAREN param_clause RPAREN block {
    Some (FuncDef { name = $2; ty = $1; params = $4; body = $6; line = ln $startpos($2); span = span $startpos $endpos })
  }
| ctype name_or_type array_opt init_opt SEMI {
    Some (GlobalDecl { name = $2; ty = combine_array $1 $3; init_expr = $4; line = ln $startpos($2); span = span $startpos $endpos })
  }
;

ctype:
| type_base ptrs { wrap_ptrs $1 $2 }
;

(* 非構造体の typedef 用: ctype から KW_STRUCT を除いたバージョン *)
non_struct_type_base:
| KW_INT { TyInt }
| KW_CHAR { TyChar }
| KW_VOID { TyVoid }
| TYPE_NAME { lookup_type $1 }
;

non_struct_ctype:
| non_struct_type_base ptrs { wrap_ptrs $1 $2 }
;

ptrs:
| /* empty */ { 0 }
| ptrs STAR { $1 + 1 }
;

type_base:
| KW_INT { TyInt }
| KW_CHAR { TyChar }
| KW_VOID { TyVoid }
| TYPE_NAME { lookup_type $1 }
| KW_STRUCT name_or_type struct_def_opt { lookup_struct $2 }
| KW_STRUCT LBRACE struct_members RBRACE { TyUnknown "struct" }
;

struct_def_opt:
| /* empty */ { [] }
| LBRACE struct_members RBRACE { List.rev $2 }
;

struct_members:
| /* empty */ { [] }
| struct_members struct_member { $2 :: $1 }
;

struct_member:
| ctype name_or_type array_opt SEMI { ($2, combine_array $1 $3) }
;

param_clause:
| /* empty */ { [] }
| param_list {
    match ($1 : param list) with
    | [({ name = None; ty = TyVoid; _ } : param)] -> []
    | params -> params
  }
;

param_list:
| parameter { [$1] }
| param_list COMMA parameter { $1 @ [$3] }
| param_list COMMA ELLIPSIS { $1 }
;

parameter:
| ctype {
    ({ name = None; ty = $1; line = ln $symbolstartpos; span = span $startpos $endpos } : param)
  }
| ctype name_or_type {
    ({ name = Some $2; ty = $1; line = ln $startpos($2); span = span $startpos $endpos } : param)
  }
;

block:
| LBRACE local_decls stmt_list RBRACE {
    Block { stmts = $2 @ $3; line = ln $startpos($1); span = span $startpos $endpos }
  }
;

local_decls:
| /* empty */ { [] }
| local_decls local_decl { $1 @ [$2] }
;

local_decl:
| ctype name_or_type array_opt init_opt SEMI {
    Decl { name = $2; ty = combine_array $1 $3; init_expr = $4; line = ln $startpos($2); span = span $startpos $endpos }
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

expr:
| assign { $1 }
;

assign:
| e_or ASSIGN assign {
    Assign { lhs = $1; rhs = $3; line = line_of_expr $1; span = span $startpos $endpos }
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
| e_and ANDAND bitor {
    Binary { op = And; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| bitor { $1 }
;

bitor:
| bitor PIPE bitxor {
    Binary { op = BitOr; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| bitxor { $1 }
;

bitxor:
| bitxor CARET bitand {
    Binary { op = BitXor; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| bitand { $1 }
;

bitand:
| bitand AMP eq {
    Binary { op = BitAnd; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
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
| rel LT shift {
    Binary { op = Lt; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel GT shift {
    Binary { op = Lt; lhs = $3; rhs = $1; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel LE shift {
    Binary { op = Le; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| rel GE shift {
    Binary { op = Le; lhs = $3; rhs = $1; line = ln $startpos($2); span = span $startpos $endpos }
  }
| shift { $1 }
;

shift:
| shift SHL add {
    Binary { op = Shl; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
  }
| shift SHR add {
    Binary { op = Shr; lhs = $1; rhs = $3; line = ln $startpos($2); span = span $startpos $endpos }
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
| TILDE unary {
    Unary { op = BitNot; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| STAR unary {
    Unary { op = Deref; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| AMP unary {
    Unary { op = Addr; operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| SIZEOF LPAREN ctype RPAREN {
    SizeofType { ty = $3; line = ln $startpos($1); span = span $startpos $endpos }
  }
| SIZEOF unary {
    SizeofExpr { operand = $2; line = ln $startpos($1); span = span $startpos $endpos }
  }
| postfix { $1 }
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

array_opt:
| /* empty */ { None }
| LBRACKET NUM RBRACKET { Some $2 }
;

init_opt:
| /* empty */ { None }
| ASSIGN expr { Some $2 }
;
