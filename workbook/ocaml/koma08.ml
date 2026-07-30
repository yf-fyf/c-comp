(*
    コマ 8: 関数② — 引数受け取り + 関数呼び出し
*)

open Ast_def

let emit line = print_endline line

let error ?(line = 0) msg =
  prerr_endline (Printf.sprintf "[line %d] %s" line msg);
  exit 1

let locals : (string, int) Hashtbl.t = Hashtbl.create 64
let stack_offset = ref 0

(* スタックに積んでいる一時値の個数（1個 8 バイト）。
   call 直前に sp が 16 の倍数かどうかを判定するために数える。 *)
let depth = ref 0

let label_count = ref 0
let ret_label = ref ""
let break_stack : string list ref = ref []
let cont_stack : string list ref = ref []

let push st x = st := x :: !st
let pop st = match !st with [] -> () | _ :: xs -> st := xs
let peek st = match !st with x :: _ -> x | [] -> error "空のラベルスタックです"

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

let rec collect_decls = function
  | Decl { name; _ } -> alloc_local name
  | Block { stmts; _ } -> List.iter collect_decls stmts
  | If { then_; else_; _ } -> collect_decls then_; Option.iter collect_decls else_
  | While { body; _ } | For { body; _ } -> collect_decls body
  | _ -> ()

let codegen_lval = function
  | Var { name; line; _ } ->
      emit (Printf.sprintf "  addi a0, s0, %d" (lookup_var name line))
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

let push_a0 () =
  emit "  addi sp, sp, -8";
  emit "  sd a0, 0(sp)";
  incr depth

let pop_into reg =
  emit (Printf.sprintf "  ld %s, 0(sp)" reg);
  emit "  addi sp, sp, 8";
  decr depth

let rec codegen = function
  | Num { value; _ } ->
      emit (Printf.sprintf "  li a0, %d" value)
  | Var _ as v ->
      codegen_lval v;
      emit "  ld a0, 0(a0)"
  | Assign { lhs; rhs; _ } ->
      codegen_lval lhs;
      push_a0 ();
      codegen rhs;
      pop_into "a1";
      emit "  sd a0, 0(a1)"
  | Unary { op = Neg; operand; _ } ->
      codegen operand;
      emit "  neg a0, a0"
  | Unary { op = PreInc; operand; _ } ->
      codegen_lval operand;
      emit "  ld a1, 0(a0)";
      emit "  addi a1, a1, 1";
      emit "  sd a1, 0(a0)";
      emit "  mv a0, a1"
  | Unary { op = PreDec; operand; _ } ->
      codegen_lval operand;
      emit "  ld a1, 0(a0)";
      emit "  addi a1, a1, -1";
      emit "  sd a1, 0(a0)";
      emit "  mv a0, a1"
  | Call { name; args; _ } -> gen_call name args
  | Binary { op; lhs; rhs; _ } ->
      codegen lhs;
      push_a0 ();
      codegen rhs;
      pop_into "a1";
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
      | _ -> error "コマ8で未対応の二項演算です")
  | Cond { cond; then_; else_; _ } ->
      let label_else = new_label () in
      let label_end = new_label () in
      codegen cond;
      emit (Printf.sprintf "  beqz a0, %s" label_else);
      codegen then_;
      emit (Printf.sprintf "  j %s" label_end);
      emit (label_else ^ ":");
      codegen else_;
      emit (label_end ^ ":")
  | e -> error ~line:(line_of_expr e) "コマ8で未対応の式です"

and gen_call name args =
  let n = List.length args in
  List.iter (fun arg -> codegen arg; push_a0 ()) args;
  for i = 0 to n - 1 do
    emit (Printf.sprintf "  ld a%d, %d(sp)" i ((n - 1 - i) * 8))
  done;
  if n > 0 then (
    emit (Printf.sprintf "  addi sp, sp, %d" (n * 8));
    depth := !depth - n);
  (* ここで sp は「呼び出しを囲む式が積んだ一時値」の分だけフレームから下がっている。
     一時値は 1 個 8 バイトなので、奇数個なら 16 バイト境界からずれている。 *)
  let pad = if !depth mod 2 <> 0 then 8 else 0 in
  if pad <> 0 then emit (Printf.sprintf "  addi sp, sp, -%d" pad);
  emit (Printf.sprintf "  call %s" name);
  if pad <> 0 then emit (Printf.sprintf "  addi sp, sp, %d" pad)

let rec gen_stmt = function
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
  | While { cond; body; _ } ->
      let label_cond = new_label () in
      let label_end = new_label () in
      push break_stack label_end;
      push cont_stack label_cond;
      emit (label_cond ^ ":");
      codegen cond;
      emit (Printf.sprintf "  beqz a0, %s" label_end);
      gen_stmt body;
      emit (Printf.sprintf "  j %s" label_cond);
      emit (label_end ^ ":");
      pop break_stack;
      pop cont_stack
  | For { init; cond; step; body; _ } ->
      let label_cond = new_label () in
      let label_step = new_label () in
      let label_end = new_label () in
      push break_stack label_end;
      push cont_stack label_step;
      Option.iter codegen init;
      emit (label_cond ^ ":");
      Option.iter (fun c -> codegen c; emit (Printf.sprintf "  beqz a0, %s" label_end)) cond;
      gen_stmt body;
      emit (label_step ^ ":");
      Option.iter codegen step;
      emit (Printf.sprintf "  j %s" label_cond);
      emit (label_end ^ ":");
      pop break_stack;
      pop cont_stack
  | Break _ -> emit (Printf.sprintf "  j %s" (peek break_stack))
  | Continue _ -> emit (Printf.sprintf "  j %s" (peek cont_stack))

let gen_func = function
  | FuncDef { name; params; body; _ } ->
      Hashtbl.clear locals;
      stack_offset := 0;
      depth := 0;
      ret_label := new_label ();
      break_stack := [];
      cont_stack := [];
      List.iter (fun (p : param) -> Option.iter alloc_local p.name) params;
      collect_decls body;
      let frame_size = align_to !stack_offset 16 in
      emit (Printf.sprintf "  .globl %s" name);
      emit (name ^ ":");
      emit (Printf.sprintf "  addi sp, sp, -%d" (frame_size + 16));
      emit (Printf.sprintf "  sd ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  sd s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  addi s0, sp, %d" (frame_size + 16));
      List.iteri
        (fun i (p : param) ->
          match p.name with
          | Some pname when i < 8 ->
              (match Hashtbl.find_opt locals pname with
              | Some offset -> emit (Printf.sprintf "  sd a%d, %d(s0)" i offset)
              | None -> ())
          | _ -> ())
        params;
      gen_stmt body;
      if !depth <> 0 then
        error (Printf.sprintf "push と pop の数が合っていません (depth=%d)" !depth);
      emit (!ret_label ^ ":");
      emit (Printf.sprintf "  ld s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  ld ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  addi sp, sp, %d" (frame_size + 16));
      emit "  ret"
  | _ -> ()

let () =
  if Array.length Sys.argv < 2 then (
    prerr_endline "使い方: dune exec ./koma08.exe -- <source.c>";
    exit 1);
  let filename = Sys.argv.(1) in
  let source = Utils.read_file filename in
  let prog = Frontend.parse_source ~filename source in
  emit "  .text";
  List.iter gen_func prog
