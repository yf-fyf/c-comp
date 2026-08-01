(*
   文字列リテラルの通し番号（.LC）。

   採番の規則はここだけに書く。番号は .data セクションの並びと la 命令の両方に
   現れるので、走査の順を変えると生成されるアセンブリが変わる。

   規則:
   - プログラム全体（複数ファイルなら並んだ順）を 1 回だけ走査する
   - 見るのは関数定義の本体だけ（プロトタイプ・グローバル宣言には文字列がない）
   - 同じ内容の文字列は同じ番号（先着順）。番号は 1 始まり
   - 式は lhs → rhs、cond → then → else、引数は並び順
   - 文は出現順。for は init → cond → step → body
*)

type t = { ids : (string, int) Hashtbl.t; mutable rev_all : string list; mutable count : int }

let create () = { ids = Hashtbl.create 64; rev_all = []; count = 0 }

let intern t s =
  match Hashtbl.find_opt t.ids s with
  | Some id -> id
  | None ->
      t.count <- t.count + 1;
      Hashtbl.replace t.ids s t.count;
      t.rev_all <- s :: t.rev_all;
      t.count

let id t s =
  match Hashtbl.find_opt t.ids s with
  | Some id -> id
  | None -> intern t s (* 収集漏れがあっても番号は必ず引ける *)

(* 番号順（1 番から）に並べた内容。.data はこの順に出す *)
let contents t = List.rev t.rev_all

let rec walk_expr t (e : Ast.expr) =
  match e.e_desc with
  | Ast.Str s -> ignore (intern t s)
  | Ast.Assign { lhs; rhs } | Ast.Binary { lhs; rhs; _ } | Ast.Index { base = lhs; index = rhs } ->
      walk_expr t lhs;
      walk_expr t rhs
  | Ast.Unary { operand; _ } | Ast.Member { base = operand; _ } -> walk_expr t operand
  | Ast.Cond { cond; then_; else_ } ->
      walk_expr t cond;
      walk_expr t then_;
      walk_expr t else_
  | Ast.Call { args; _ } -> List.iter (walk_expr t) args
  | Ast.Num _ | Ast.Var _ | Ast.Sizeof _ -> ()

let rec walk_stmt t (s : Ast.stmt) =
  match s.s_desc with
  | Ast.Block stmts -> List.iter (walk_stmt t) stmts
  | Ast.Expr e -> walk_expr t e
  | Ast.Return e -> Option.iter (walk_expr t) e
  | Ast.If { cond; then_; else_ } ->
      walk_expr t cond;
      walk_stmt t then_;
      Option.iter (walk_stmt t) else_
  | Ast.While { cond; body } ->
      walk_expr t cond;
      walk_stmt t body
  | Ast.For { init; cond; step; body } ->
      Option.iter (walk_expr t) init;
      Option.iter (walk_expr t) cond;
      Option.iter (walk_expr t) step;
      walk_stmt t body
  | Ast.Empty | Ast.Break | Ast.Continue -> ()

let collect (programs : Ast.program list) =
  let t = create () in
  List.iter
    (fun (p : Ast.program) ->
      List.iter
        (function Ast.Func f -> List.iter (walk_stmt t) f.fn_body | Ast.Proto _ | Ast.Global _ -> ())
        p.tops)
    programs;
  t
