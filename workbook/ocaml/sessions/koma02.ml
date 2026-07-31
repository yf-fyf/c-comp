(*
   コマ 2: AST インタープリター（OCaml 版）
*)

open Ast_def
let c_div a b =
  if b = 0 then raise Division_by_zero;
  a / b

let c_mod a b = a - (b * c_div a b)

let rec eval_ast = function
  | Num { value; _ } -> value
  | Unary { op = Neg; operand; _ } -> -(eval_ast operand)
  | Binary { op = Add; lhs; rhs; _ } -> eval_ast lhs + eval_ast rhs
  | Binary { op = Sub; lhs; rhs; _ } -> eval_ast lhs - eval_ast rhs
  | Binary { op = Mul; lhs; rhs; _ } -> eval_ast lhs * eval_ast rhs
  | Binary { op = Div; lhs; rhs; _ } -> c_div (eval_ast lhs) (eval_ast rhs)
  | Binary { op = Mod; lhs; rhs; _ } -> c_mod (eval_ast lhs) (eval_ast rhs)
  | _ -> failwith "eval_ast: コマ2で未対応の式です"

let run_main prog =
  let rec eval_stmt = function
    | Return { expr = Some e; _ } -> Some (eval_ast e)
    | Block { stmts; _ } -> eval_stmts stmts
    | _ -> None
  and eval_stmts = function
    | [] -> None
    | s :: ss ->
        (match eval_stmt s with
        | Some v -> Some v
        | None -> eval_stmts ss)
  in
  match List.find_opt (function FuncDef { name = "main"; _ } -> true | _ -> false) prog with
  | Some (FuncDef { body; _ }) ->
      (match eval_stmt body with
      | Some v -> v
      | None -> failwith "main 関数内に評価可能な return が見つかりません")
  | _ -> failwith "main 関数が見つかりません"

let () =
  if Array.length Sys.argv < 2 then (
    prerr_endline "使い方: dune exec ./koma02.exe -- <source.c>";
    exit 1);
  let filename = Sys.argv.(1) in
  let source = Utils.read_file filename in
  let prog = Frontend.parse_source ~filename source in
  let result = run_main prog in
  Printf.printf "評価結果: %d\n" result
