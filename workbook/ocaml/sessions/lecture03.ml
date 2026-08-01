(*
    コマ 3: コード生成① — 算術式 → RV64 アセンブリ
*)

open Ast_def

let emit line = print_endline line

let error ?(line = 0) msg =
  prerr_endline (Printf.sprintf "[line %d] %s" line msg);
  exit 1

let rec codegen = function
  | Num { value; _ } ->
      emit (Printf.sprintf "  li a0, %d" value)
  | Unary { op = Neg; operand; _ } ->
      codegen operand;
      emit "  neg a0, a0"
  | Binary { op; lhs; rhs; _ } ->
      codegen lhs;
      emit "  addi sp, sp, -8";
      emit "  sd a0, 0(sp)";
      codegen rhs;
      emit "  ld a1, 0(sp)";
      emit "  addi sp, sp, 8";
      (match op with
      | Add -> emit "  add a0, a1, a0"
      | Sub -> emit "  sub a0, a1, a0"
      | Mul -> emit "  mul a0, a1, a0"
      | Div -> emit "  div a0, a1, a0"
      | Mod -> emit "  rem a0, a1, a0"
      | _ -> error "コマ3で未対応の二項演算です")
  | e -> error ~line:(line_of_expr e) "コマ3で未対応の式です"

let gen_stmt = function
  | Return { expr; _ } -> Option.iter codegen expr
  | _ -> ()

let gen_func = function
  | FuncDef { name; body = Block { stmts; _ }; _ } ->
      emit (Printf.sprintf "  .globl %s" name);
      emit (name ^ ":");
      emit "  addi sp, sp, -16";
      emit "  sd ra, 8(sp)";
      emit "  sd s0, 0(sp)";
      emit "  addi s0, sp, 16";
      List.iter gen_stmt stmts;
      emit "  ld s0, 0(sp)";
      emit "  ld ra, 8(sp)";
      emit "  addi sp, sp, 16";
      emit "  ret"
  | FuncDef _ -> error "gen_func: 関数本体がブロックではありません"
  | _ -> ()

let () =
  if Array.length Sys.argv < 2 then (
    prerr_endline "使い方: dune exec ./lecture03.exe -- <source.c>";
    exit 1);
  let filename = Sys.argv.(1) in
  let source = Utils.read_file filename in
  let prog = Frontend.parse_source ~filename source in
  emit "  .text";
  List.iter gen_func prog
