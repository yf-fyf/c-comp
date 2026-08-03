(*
   コマ3: コード生成② — 変数・代入・シンボルテーブル
*)

open Ast_def

let emit line = print_endline line

let error ?(line = 0) msg =
  prerr_endline (Printf.sprintf "[line %d] %s" line msg);
  exit 1

let locals : (string, int) Hashtbl.t = Hashtbl.create 64
let stack_offset = ref 0

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
      | _ -> error "コマ3で未対応の二項演算です")
  | e -> error ~line:(line_of_expr e) "コマ3で未対応の式です"

let gen_stmt = function
  | Decl _ -> ()
  | ExprStmt { expr = Some e; _ } -> codegen e
  | ExprStmt _ -> ()
  | Return { expr; _ } -> Option.iter codegen expr
  | _ -> ()

let collect_decls = function
  | Decl { name; _ } -> alloc_local name
  | _ -> ()

let gen_func = function
  | FuncDef { name; body = Block { stmts; _ }; _ } ->
      Hashtbl.clear locals;
      stack_offset := 0;
      List.iter collect_decls stmts;
      let frame_size = align_to !stack_offset 16 in
      emit (Printf.sprintf "  .globl %s" name);
      emit (name ^ ":");
      emit (Printf.sprintf "  addi sp, sp, -%d" (frame_size + 16));
      emit (Printf.sprintf "  sd ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  sd s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  addi s0, sp, %d" (frame_size + 16));
      List.iter gen_stmt stmts;
      emit (Printf.sprintf "  ld s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  ld ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  addi sp, sp, %d" (frame_size + 16));
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
