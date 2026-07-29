(*
    コマ 5: 制御構文① — if / else + 比較演算子
*)

open Ast_def

let emit line = print_endline line

let error ?(line = 0) msg =
  prerr_endline (Printf.sprintf "[line %d] %s" line msg);
  exit 1

let locals : (string, int) Hashtbl.t = Hashtbl.create 64
let stack_offset = ref 0
let label_count = ref 0
let ret_label = ref ""

let new_label () =
  incr label_count;
  Printf.sprintf ".L%d" !label_count

let align_to n align = ((n + align - 1) / align) * align

let alloc_local name =
  stack_offset := !stack_offset + 8;
  Hashtbl.replace locals name (-(16 + !stack_offset))

let lookup_var name line =
  match Hashtbl.find_opt locals name with
  | Some offset -> offset
  | None -> error ~line (Printf.sprintf "未定義の変数: '%s'" name)

let codegen_lval = function
  | Var { name; line; _ } ->
      emit (Printf.sprintf "  addi a0, s0, %d" (lookup_var name line))
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

let rec codegen = function
  | Num { value; _ } ->
      emit (Printf.sprintf "  li a0, %d" value)
  | Var _ as v ->
      codegen_lval v;
      emit "  ld a0, 0(a0)"
  | Assign { lhs; rhs; _ } ->
      codegen_lval lhs;
      emit "  addi sp, sp, -8";
      emit "  sd a0, 0(sp)";
      codegen rhs;
      emit "  ld a1, 0(sp)";
      emit "  addi sp, sp, 8";
      emit "  sd a0, 0(a1)"
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
      | Eq -> emit "  sub a0, a1, a0"; emit "  seqz a0, a0"
      | Ne -> emit "  sub a0, a1, a0"; emit "  snez a0, a0"
      | Lt -> emit "  slt a0, a1, a0"
      | Le -> emit "  slt a0, a0, a1"; emit "  xori a0, a0, 1"
      | _ -> error "コマ5で未対応の二項演算です")
  | e -> error ~line:(line_of_expr e) "コマ5で未対応の式です"

let rec gen_stmt = function
  | Decl { name; init_expr = Some e; line; _ } ->
      codegen (Assign { lhs = Var { name; line; span = None }; rhs = e; line; span = None })
  | Decl _ -> ()
  | ExprStmt { expr = Some e; _ } -> codegen e
  | ExprStmt _ -> ()
  | Return { expr; _ } ->
      Option.iter codegen expr;
      emit (Printf.sprintf "  j %s" !ret_label)
  | Block { stmts; _ } -> List.iter gen_stmt stmts
  | If { cond; then_; else_; _ } ->
      let label_else = new_label () in
      codegen cond;
      emit (Printf.sprintf "  beqz a0, %s" label_else);
      gen_stmt then_;
      (match else_ with
      | Some else_stmt ->
          let label_end = new_label () in
          emit (Printf.sprintf "  j %s" label_end);
          emit (label_else ^ ":");
          gen_stmt else_stmt;
          emit (label_end ^ ":")
      | None -> emit (label_else ^ ":"))
  | s -> error ~line:(line_of_stmt s) "コマ5で未対応の文です"

let collect_decls = function
  | Decl { name; _ } -> alloc_local name
  | _ -> ()

let gen_func = function
  | FuncDef { name; body = Block { stmts; _ }; _ } ->
      Hashtbl.clear locals;
      stack_offset := 0;
      ret_label := new_label ();
      List.iter collect_decls stmts;
      let frame_size = align_to !stack_offset 16 in
      emit (Printf.sprintf "  .globl %s" name);
      emit (name ^ ":");
      emit (Printf.sprintf "  addi sp, sp, -%d" (frame_size + 16));
      emit (Printf.sprintf "  sd ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  sd s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  addi s0, sp, %d" (frame_size + 16));
      List.iter gen_stmt stmts;
      emit (!ret_label ^ ":");
      emit (Printf.sprintf "  ld s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  ld ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  addi sp, sp, %d" (frame_size + 16));
      emit "  ret"
  | FuncDef _ -> error "gen_func: 関数本体がブロックではありません"
  | _ -> ()

let () =
  if Array.length Sys.argv < 2 then (
    prerr_endline "使い方: dune exec ./koma05.exe -- <source.c>";
    exit 1);
  let filename = Sys.argv.(1) in
  let source = Utils.read_file filename in
  let prog = Frontend.parse_source ~filename source in
  emit "  .text";
  List.iter gen_func prog
