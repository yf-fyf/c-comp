(*
   AST ノード定義 — OCaml 版
   文字列ベースの kind 判定をやめ、代数的データ型で表現する。
*)

(* ── 型 ──
   struct はタグ参照（TyStruct "Node"）で表す。フィールドレイアウトは
   Struct_env が管理する（サイズ・整列の計算も Struct_env 側）。 *)

type ty =
  | TyInt
  | TyChar
  | TyVoid
  | TyPtr of ty
  | TyStruct of string

let is_ptr_ty = function TyPtr _ -> true | _ -> false
let is_struct_ty = function TyStruct _ -> true | _ -> false

(* ── 演算子・式・文の AST ── *)

type binop =
  | Add
  | Sub
  | Mul
  | Div
  | Mod
  | Eq
  | Ne
  | Lt
  | Le
  | And
  | Or

type unop =
  | Neg
  | Not
  | Addr
  | Deref
  | PreInc
  | PreDec

(* 前処理後ソース上の UTF-8 バイト半開区間。None は合成ノードを表す。 *)
type source_span = { start_offset : int; end_offset : int }

type expr =
  | Num of { value : int; line : int; span : source_span option }
  | StrLit of { value : string; line : int; span : source_span option }
  | Var of { name : string; line : int; span : source_span option }
  | Assign of { lhs : expr; rhs : expr; line : int; span : source_span option }
  | Cond of { cond : expr; then_ : expr; else_ : expr; line : int; span : source_span option }
  | Binary of { op : binop; lhs : expr; rhs : expr; line : int; span : source_span option }
  | Unary of { op : unop; operand : expr; line : int; span : source_span option }
  | Index of { base : expr; index : expr; line : int; span : source_span option }
  | Member of { base : expr; name : string; is_arrow : bool; line : int; span : source_span option }
  | SizeofType of { ty : ty; line : int; span : source_span option }
  | Call of { name : string; args : expr list; line : int; span : source_span option }

type decl = {
  name : string;
  ty : ty;
  line : int;
  span : source_span option;
}

type stmt =
  | Block of { stmts : stmt list; line : int; span : source_span option }
  | ExprStmt of { expr : expr option; line : int; span : source_span option }
  | Return of { expr : expr option; line : int; span : source_span option }
  | Break of { line : int; span : source_span option }
  | Continue of { line : int; span : source_span option }
  | If of { cond : expr; then_ : stmt; else_ : stmt option; line : int; span : source_span option }
  | While of { cond : expr; body : stmt; line : int; span : source_span option }
  | For of {
      init : expr option;
      cond : expr option;
      step : expr option;
      body : stmt;
      line : int;
      span : source_span option;
    }
  | Decl of decl

type param = {
  name : string option;
  ty : ty;
  line : int;
  span : source_span option;
}

type func = {
  name : string;
  ty : ty;
  params : param list;
  body : stmt;
  line : int;
  span : source_span option;
}

type func_proto = {
  name : string;
  ty : ty;
  params : param list;
  line : int;
  span : source_span option;
}

type top =
  | FuncDef of func
  | FuncProto of func_proto
  | GlobalDecl of decl

type program = top list

let line_of_expr = function
  | Num { line; _ }
  | StrLit { line; _ }
  | Var { line; _ }
  | Assign { line; _ }
  | Cond { line; _ }
  | Binary { line; _ }
  | Unary { line; _ }
  | Index { line; _ }
  | Member { line; _ }
  | SizeofType { line; _ }
  | Call { line; _ } ->
      line

let line_of_stmt = function
  | Block { line; _ }
  | ExprStmt { line; _ }
  | Return { line; _ }
  | Break { line; _ }
  | Continue { line; _ }
  | If { line; _ }
  | While { line; _ }
  | For { line; _ }
  | Decl { line; _ } ->
      line

let span_of_expr = function
  | Num { span; _ }
  | StrLit { span; _ }
  | Var { span; _ }
  | Assign { span; _ }
  | Cond { span; _ }
  | Binary { span; _ }
  | Unary { span; _ }
  | Index { span; _ }
  | Member { span; _ }
  | SizeofType { span; _ }
  | Call { span; _ } ->
      span

let with_expr_span expr span =
  match expr with
  | Num r -> Num { r with span }
  | StrLit r -> StrLit { r with span }
  | Var r -> Var { r with span }
  | Assign r -> Assign { r with span }
  | Cond r -> Cond { r with span }
  | Binary r -> Binary { r with span }
  | Unary r -> Unary { r with span }
  | Index r -> Index { r with span }
  | Member r -> Member { r with span }
  | SizeofType r -> SizeofType { r with span }
  | Call r -> Call { r with span }
