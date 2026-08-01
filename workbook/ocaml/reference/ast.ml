(*
   構文木。

   字句解析・構文解析の出力そのもので、意味づけ（型の決定・変数の解決）はしていない。
   ここから Typing が型付き木（Tast）を作り、コード生成はそちらだけを見る。

   位置は全ノードが Loc.t を 1 フィールド持つ形に統一してある。
   構文の形をそのまま写すことを優先していて、たとえば `p->x` と `v.x` は
   同じ Member ノード（arrow で区別）である。これらの整理は Tast 側で行う。
*)

type binop = Add | Sub | Mul | Div | Mod | Eq | Ne | Lt | Le | And | Or
type unop = Neg | Not | Addr | Deref | PreInc | PreDec

type expr = { e_desc : expr_desc; e_loc : Loc.t }

and expr_desc =
  | Num of int (* 整数リテラルと文字リテラル *)
  | Str of string
  | Var of string
  | Assign of { lhs : expr; rhs : expr }
  | Cond of { cond : expr; then_ : expr; else_ : expr }
  | Binary of { op : binop; lhs : expr; rhs : expr }
  | Unary of { op : unop; operand : expr }
  | Index of { base : expr; index : expr }
  | Member of { base : expr; field : string; arrow : bool }
  | Sizeof of Ctype.t (* 型名形式のみ。sizeof 式 はこのサブセットにない *)
  | Call of { name : string; args : expr list }

type stmt = { s_desc : stmt_desc; s_loc : Loc.t }

and stmt_desc =
  | Empty (* 空文 ; *)
  | Expr of expr
  | Return of expr option
  | Break
  | Continue
  | If of { cond : expr; then_ : stmt; else_ : stmt option }
  | While of { cond : expr; body : stmt }
  | For of { init : expr option; cond : expr option; step : expr option; body : stmt }
  | Block of stmt list

(* 局所宣言・グローバル宣言。初期化子はこのサブセットにない *)
type decl = { d_name : string; d_ty : Ctype.t; d_loc : Loc.t }

(* 仮引数。文法上、名前は必須である *)
type param = { p_name : string; p_ty : Ctype.t; p_loc : Loc.t }

type struct_def = { sd_tag : string; sd_fields : (string * Ctype.t) list; sd_loc : Loc.t }

(* 局所宣言は関数本体の先頭にしか置けない（文法の制約）ので、
   文の列とは別に持つ。入れ子ブロックは文だけを含む。 *)
type func = {
  fn_name : string;
  fn_ret : Ctype.t;
  fn_params : param list;
  fn_locals : decl list;
  fn_body : stmt list;
  fn_loc : Loc.t;
}

type proto = {
  pt_name : string;
  pt_ret : Ctype.t;
  pt_params : param list;
  pt_variadic : bool; (* 可変長 '...' はプロトタイプ宣言でのみ使える *)
  pt_loc : Loc.t;
}

type top = Func of func | Proto of proto | Global of decl

(* struct 定義は宣言の列から分けて持つ。
   レイアウトは定義順に畳み込むので、structs の順序には意味がある。 *)
type program = { structs : struct_def list; tops : top list }
