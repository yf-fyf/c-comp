(*
   型付き木。Typing が構文木（Ast）から作り、コード生成はこちらだけを見る。

   構文木との違いは「決め終わっていること」である。
   - 変数はスタックの変位かグローバルのラベルに解決済み（Lvar）
   - すべての式に型が付いている（load / store の幅がこれで決まる）
   - 左辺値は式とは別のカテゴリ（lval）。lvalue でない式が代入の左に来る木は作れない
   - p->x は「p を間接参照した入れ物の x」へ、a[i] は「a + i を間接参照したもの」へ
     均してある（Lderef と Lfield の組み合わせになる）。フィールドの変位も解決済み
   - ポインタ演算は PtrArith に分かれ、要素の大きさを持つ。加算の被演算子は
     「ポインタ側が ptr」に正規化してある（コード生成はこちらを先に評価する）
   - 前置 ++ / -- は増減の量（ポインタなら 1 要素ぶん）に解決済み

   コード生成に届く木はすべて生成できる木であり、Typing で弾かれた形は
   ここで表現できない。したがってコード生成にエラー処理はない。
*)

type var_ref =
  | Local of { name : string; offset : int } (* s0 からの変位。name は注記のため *)
  | Global of { name : string }

type unop = Neg | Not
type ptr_op = PtrAdd | PtrSub

type expr = { e_desc : expr_desc; e_ty : Ctype.t; e_loc : Loc.t }

and expr_desc =
  | Const of int (* 整数・文字リテラルと sizeof *)
  | StrAddr of int (* 文字列リテラルの通し番号（.LC） *)
  | Rval of lval (* 左辺値からの読み出し *)
  | AddrOf of lval
  | Assign of { lhs : lval; rhs : expr }
  | IncDec of { lhs : lval; delta : int }
  | Cond of { cond : expr; then_ : expr; else_ : expr }
  | PtrArith of { op : ptr_op; ptr : expr; index : expr; elem_size : int }
  | Binary of { op : Ast.binop; lhs : expr; rhs : expr } (* 整数演算のみ *)
  | Unary of { op : unop; operand : expr }
  | Call of { name : string; args : expr list }

and lval = { l_desc : lval_desc; l_ty : Ctype.t }

and lval_desc =
  | Lvar of var_ref
  | Lderef of expr (* 式の値がそのまま番地 *)
  | Lfield of { base : lval; field : string; offset : int }

type stmt = { s_desc : stmt_desc; s_loc : Loc.t }

and stmt_desc =
  | Empty
  | Expr of expr
  | Return of expr option
  | Break
  | Continue
  | If of { cond : expr; then_ : stmt; else_ : stmt option }
  | While of { cond : expr; body : stmt }
  | For of { init : expr option; cond : expr option; step : expr option; body : stmt }
  | Block of stmt list

type func = {
  fn_name : string;
  (* 仮引数の置き場。i 番目が i 番目の引数レジスタに対応する。
     同名の局所宣言に隠された仮引数は、そちらの変位を指す（元の実装と同じ） *)
  fn_params : int list;
  fn_frame_size : int;
  fn_body : stmt list;
}

(* ファイル 1 つぶん。見出しに元の C を切り出すため、前処理後ソースを持つ *)
type unit_ = { u_source : string; u_funcs : func list }

type program = {
  layout : Layout.t; (* 型の大きさを引くための表。struct はここにしかない *)
  strings : string list; (* 添字 + 1 が .LC の番号 *)
  globals : (string * Ctype.t) list; (* 宣言の出現順 *)
  units : unit_ list;
}
