(*
    コマ 13: sizeof + malloc — SizeofType / SizeofExpr
*)

open Ast_def

let emit line = print_endline line
let error ?(line = 0) msg = prerr_endline (Printf.sprintf "[line %d] %s" line msg); exit 1

let locals : (string, int * ty) Hashtbl.t = Hashtbl.create 64
let stack_offset = ref 0

(* スタックに積んでいる一時値の個数（1個 8 バイト）。
   call 直前に sp が 16 の倍数かどうかを判定するために数える。 *)
let depth = ref 0
let label_count = ref 0
let ret_label = ref ""
let break_stack : string list ref = ref []
let cont_stack : string list ref = ref []
let string_literals : (string, string) Hashtbl.t = Hashtbl.create 64
let string_label_count = ref 0

let push st x = st := x :: !st
let pop st = match !st with [] -> () | _ :: xs -> st := xs
let peek st = match !st with x :: _ -> x | [] -> error "空のラベルスタックです"
let new_label () = incr label_count; Printf.sprintf ".L%d" !label_count
let align_to n align = ((n + align - 1) / align) * align
let push_a0 () = emit "  addi sp, sp, -8"; emit "  sd a0, 0(sp)"; incr depth
let pop_into reg = emit (Printf.sprintf "  ld %s, 0(sp)" reg); emit "  addi sp, sp, 8"; decr depth

let alloc_local name ty =
  stack_offset := !stack_offset + align_to (size_of_ty ty) 8;
  Hashtbl.replace locals name (-(16 + !stack_offset), ty)

let lookup_var name line =
  match Hashtbl.find_opt locals name with Some (offset, _) -> offset | None -> error ~line (Printf.sprintf "未定義の変数: '%s'" name)

let rec collect_decls = function
  | Decl { name; ty; _ } -> alloc_local name ty
  | Block { stmts; _ } -> List.iter collect_decls stmts
  | If { then_; else_; _ } -> collect_decls then_; Option.iter collect_decls else_
  | While { body; _ } | For { body; _ } -> collect_decls body
  | _ -> ()

let load ty = match ty with TyArray _ -> () | _ -> (match size_of_ty ty with 1 -> emit "  lb a0, 0(a0)" | 4 -> emit "  lw a0, 0(a0)" | _ -> emit "  ld a0, 0(a0)")
let store ty = match size_of_ty ty with 1 -> emit "  sb a0, 0(a1)" | 4 -> emit "  sw a0, 0(a1)" | _ -> emit "  sd a0, 0(a1)"
let scale_index elem_ty = let sz = size_of_ty elem_ty in if sz <> 1 then (emit (Printf.sprintf "  li a1, %d" sz); emit "  mul a0, a0, a1")

let intern_string s = match Hashtbl.find_opt string_literals s with Some label -> label | None -> incr string_label_count; let label = Printf.sprintf ".LC%d" !string_label_count in Hashtbl.replace string_literals s label; label

let pre_register_typedef_names source =
  let typedef_re = Str.regexp "typedef[ \t\n\r]" in let pos = ref 0 in
  try while true do
    ignore (Str.search_forward typedef_re source !pos);
    let start = Str.match_end () in
    let brace_depth = ref 0 in let semi_pos = ref start in let found = ref false in let i = ref start in
    while !i < String.length source && not !found do let c = source.[!i] in (match c with '{' -> incr brace_depth | '}' -> decr brace_depth | ';' when !brace_depth = 0 -> semi_pos := !i; found := true | _ -> ()); incr i done;
    if not !found then raise Not_found;
    let text = String.sub source start (!semi_pos - start) in
    let rec scan_name i = if i < 0 then ("",0) else let c = text.[i] in if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c = '_' then scan_name (i-1) else (String.sub text (i+1) (String.length text - i - 1), i) in
    let name = String.trim (fst (scan_name (String.length text - 1))) in
    if String.length name > 0 then Typedef_env.register_name name (TyUnknown name);
    pos := !semi_pos + 1
  done with Not_found -> ()

let resolve_struct_types prog =
  List.iter (function
    | StructDef { tag; fields; name; _ } ->
        let offset, fields_with_offset = List.fold_left (fun (offset, acc) (fname, fty) -> let align = min (size_of_ty fty) 8 in let offset = align_to offset align in let next = offset + size_of_ty fty in (next, ((fname, { offset; ty = fty }) :: acc))) (0, []) fields in
        let total_size = align_to offset 8 in let fields_with_offset = List.rev fields_with_offset in
        let struct_ty = TyStruct { name = tag; fields = fields_with_offset; size = total_size } in
        Typedef_env.set name struct_ty; Option.iter (fun t -> Typedef_env.set ("struct " ^ t) struct_ty) tag
    | _ -> ()) prog

let field_ty struct_ty name line = match struct_ty with TyStruct { fields; _ } -> (match List.assoc_opt name fields with Some fi -> fi.ty | None -> error ~line (Printf.sprintf "構造体にフィールド '%s' がありません" name)) | _ -> error ~line "構造体型ではありません"
let field_offset struct_ty name line = match struct_ty with TyStruct { fields; _ } -> (match List.assoc_opt name fields with Some fi -> fi.offset | None -> error ~line (Printf.sprintf "構造体にフィールド '%s' がありません" name)) | _ -> error ~line "構造体型ではありません"

let rec collect_strings_expr = function
  | StrLit { value; _ } -> ignore (intern_string value)
  | Assign { lhs; rhs; _ } | Binary { lhs; rhs; _ } | Index { base = lhs; index = rhs; _ } -> collect_strings_expr lhs; collect_strings_expr rhs
  | Unary { operand; _ } | SizeofExpr { operand; _ } | Member { base = operand; _ } -> collect_strings_expr operand
  | Call { args; _ } -> List.iter collect_strings_expr args
  | Num _ | Var _ | SizeofType _ -> ()

let rec collect_strings_stmt = function
  | Block { stmts; _ } -> List.iter collect_strings_stmt stmts
  | ExprStmt { expr; _ } | Return { expr; _ } -> Option.iter collect_strings_expr expr
  | If { cond; then_; else_; _ } -> collect_strings_expr cond; collect_strings_stmt then_; Option.iter collect_strings_stmt else_
  | While { cond; body; _ } -> collect_strings_expr cond; collect_strings_stmt body
  | For { init; cond; step; body; _ } -> Option.iter collect_strings_expr init; Option.iter collect_strings_expr cond; Option.iter collect_strings_expr step; collect_strings_stmt body
  | Decl { init_expr; _ } -> Option.iter collect_strings_expr init_expr
  | Break _ | Continue _ -> ()

let emit_data_section () =
  if Hashtbl.length string_literals > 0 then emit "  .data";
  Hashtbl.iter (fun s label -> emit (label ^ ":"); String.iter (fun ch -> emit (Printf.sprintf "  .byte %d" (Char.code ch))) s; emit "  .byte 0") string_literals

let rec codegen_lval = function
  | Var { name; line; _ } -> emit (Printf.sprintf "  addi a0, s0, %d" (lookup_var name line))
  | Unary { op = Deref; operand; _ } -> codegen operand
  | Index { base; index; _ } -> let elem_ty = match type_of_expr base with TyPtr e | TyArray { elem = e; _ } -> e | _ -> TyInt in codegen base; push_a0 (); codegen index; scale_index elem_ty; pop_into "a1"; emit "  add a0, a1, a0"
  | Member { base; name; is_arrow; line; _ } -> let struct_ty = if is_arrow then (match type_of_expr base with TyPtr (TyStruct _ as s) -> codegen base; s | _ -> error ~line "-> の対象が構造体ポインタではありません") else (match type_of_lval base with TyStruct _ as s -> codegen_lval base; s | _ -> error ~line ". の対象が構造体ではありません") in let offset = field_offset struct_ty name line in if offset <> 0 then emit (Printf.sprintf "  addi a0, a0, %d" offset)
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

and type_of_lval = function
  | Var { name; line; _ } -> lookup_local_ty name line
  | Unary { op = Deref; operand; _ } -> (match type_of_expr operand with TyPtr base -> base | _ -> error ~line:(line_of_expr operand) "* の対象がポインタではありません")
  | Index { base; _ } -> (match type_of_expr base with TyPtr e | TyArray { elem = e; _ } -> e | _ -> TyInt)
  | Member { base; name; is_arrow; line; _ } -> let struct_ty = if is_arrow then match type_of_expr base with TyPtr (TyStruct _ as s) -> s | _ -> error ~line "-> の対象が構造体ポインタではありません" else match type_of_lval base with TyStruct _ as s -> s | _ -> error ~line ". の対象が構造体ではありません" in field_ty struct_ty name line
  | _ -> TyInt

and type_of_expr = function
  | Num _ -> TyInt | StrLit _ -> TyPtr TyChar | Var { name; line; _ } -> lookup_local_ty name line
  | Unary { op = Addr; operand; _ } -> TyPtr (type_of_lval operand)
  | Unary { op = Deref; operand; _ } -> (match type_of_expr operand with TyPtr t -> t | _ -> TyInt)
  | Index _ as e -> type_of_lval e
  | Member _ as e -> type_of_lval e
  | Assign { lhs; _ } -> type_of_lval lhs
  | Call _ -> TyInt
  | SizeofType _ | SizeofExpr _ -> TyInt
  | Unary { op = Neg | Not | BitNot; _ } -> TyInt
  | Binary { op = Add; lhs; rhs; _ } -> let lt = type_of_expr lhs and rt = type_of_expr rhs in (match lt, rt with TyPtr _, _ -> lt | _, TyPtr _ -> rt | _ -> TyInt)
  | Binary { op = Sub; lhs; _ } -> let lt = type_of_expr lhs in (match lt with TyPtr _ -> lt | _ -> TyInt)
  | Binary _ -> TyInt

and lookup_local_ty name line = match Hashtbl.find_opt locals name with Some (_, ty) -> ty | None -> error ~line (Printf.sprintf "未定義の変数: '%s'" name)

and codegen = function
  | Num { value; _ } -> emit (Printf.sprintf "  li a0, %d" value)
  | StrLit { value; _ } -> emit (Printf.sprintf "  la a0, %s" (intern_string value))
  | Var _ as v -> let ty = type_of_expr v in codegen_lval v; load ty
  | Unary { op = Addr; operand; _ } -> codegen_lval operand
  | Unary { op = Deref; operand; _ } -> let ty = type_of_expr operand in codegen operand; (match ty with TyPtr t -> load t | _ -> load TyInt)
  | Unary { op = Neg; operand; _ } -> codegen operand; emit "  neg a0, a0"
  | Index _ as e -> let ty = type_of_expr e in codegen_lval e; load ty
  | Member _ as e -> let ty = type_of_expr e in codegen_lval e; load ty
  | Assign { lhs; rhs; _ } -> let ty = type_of_lval lhs in codegen_lval lhs; push_a0 (); codegen rhs; pop_into "a1"; store ty
  | SizeofType { ty; _ } -> emit (Printf.sprintf "  li a0, %d" (size_of_ty ty))
  | SizeofExpr { operand; _ } -> emit (Printf.sprintf "  li a0, %d" (size_of_ty (type_of_expr operand)))
  | Call { name; args; _ } ->
      let n = List.length args in
      List.iter (fun arg -> codegen arg; push_a0 ()) args;
      for i = 0 to n - 1 do emit (Printf.sprintf "  ld a%d, %d(sp)" i ((n - 1 - i) * 8)) done;
      if n > 0 then (
        emit (Printf.sprintf "  addi sp, sp, %d" (n * 8));
        depth := !depth - n);
      (* 呼び出しを囲む式が積んでいる一時値は 1 個 8 バイト。
         奇数個なら sp が 16 バイト境界からずれているので詰める。 *)
      let pad = if !depth mod 2 <> 0 then 8 else 0 in
      if pad <> 0 then emit (Printf.sprintf "  addi sp, sp, -%d" pad);
      emit (Printf.sprintf "  call %s" name);
      if pad <> 0 then emit (Printf.sprintf "  addi sp, sp, %d" pad)
  | Binary { op = Add; lhs; rhs; _ } ->
      let lt = type_of_expr lhs and rt = type_of_expr rhs in
      if is_ptr_ty lt || is_ptr_ty rt then (
        let ptr_expr, int_expr, ptr_ty = if is_ptr_ty lt then (lhs, rhs, lt) else (rhs, lhs, rt) in
        let elem_ty = match ptr_ty with TyPtr e -> e | _ -> TyInt in codegen ptr_expr; push_a0 (); codegen int_expr; scale_index elem_ty; pop_into "a1"; emit "  add a0, a1, a0")
      else (codegen lhs; push_a0 (); codegen rhs; pop_into "a1"; emit "  add a0, a1, a0")
  | Binary { op = Sub; lhs; rhs; _ } ->
      let lt = type_of_expr lhs in if is_ptr_ty lt then (let elem_ty = match lt with TyPtr e -> e | _ -> TyInt in codegen lhs; push_a0 (); codegen rhs; scale_index elem_ty; pop_into "a1"; emit "  sub a0, a1, a0")
      else (codegen lhs; push_a0 (); codegen rhs; pop_into "a1"; emit "  sub a0, a1, a0")
  | Binary { op; lhs; rhs; _ } -> codegen lhs; push_a0 (); codegen rhs; pop_into "a1";
      (match op with Mul -> emit "  mul a0, a1, a0" | Div -> emit "  div a0, a1, a0" | Mod -> emit "  rem a0, a1, a0"
      | Eq -> emit "  sub a0, a1, a0"; emit "  seqz a0, a0" | Ne -> emit "  sub a0, a1, a0"; emit "  snez a0, a0"
      | Lt -> emit "  slt a0, a1, a0" | Le -> emit "  slt a0, a0, a1"; emit "  xori a0, a0, 1"
      | _ -> error "コマ13で未対応の二項演算です")
  | e -> error ~line:(line_of_expr e) "コマ13で未対応の式です"

let rec gen_stmt = function
  | Decl { name; init_expr = Some e; line; _ } -> codegen (Assign { lhs = Var { name; line; span = None }; rhs = e; line; span = None })
  | Decl _ -> () | ExprStmt { expr = Some e; _ } -> codegen e | ExprStmt _ -> ()
  | Return { expr; _ } -> Option.iter codegen expr; emit (Printf.sprintf "  j %s" !ret_label)
  | Block { stmts; _ } -> List.iter gen_stmt stmts
  | If { cond; then_; else_; _ } -> let lel = new_label () in codegen cond; emit (Printf.sprintf "  beqz a0, %s" lel); gen_stmt then_; (match else_ with Some e -> let lend = new_label () in emit (Printf.sprintf "  j %s" lend); emit (lel ^ ":"); gen_stmt e; emit (lend ^ ":") | None -> emit (lel ^ ":"))
  | While { cond; body; _ } -> let lc = new_label () in let le = new_label () in push break_stack le; push cont_stack lc; emit (lc ^ ":"); codegen cond; emit (Printf.sprintf "  beqz a0, %s" le); gen_stmt body; emit (Printf.sprintf "  j %s" lc); emit (le ^ ":"); pop break_stack; pop cont_stack
  | For { init; cond; step; body; _ } -> let lc = new_label () in let ls = new_label () in let le = new_label () in push break_stack le; push cont_stack ls; Option.iter codegen init; emit (lc ^ ":"); Option.iter (fun c -> codegen c; emit (Printf.sprintf "  beqz a0, %s" le)) cond; gen_stmt body; emit (ls ^ ":"); Option.iter codegen step; emit (Printf.sprintf "  j %s" lc); emit (le ^ ":"); pop break_stack; pop cont_stack
  | Break _ -> emit (Printf.sprintf "  j %s" (peek break_stack))
  | Continue _ -> emit (Printf.sprintf "  j %s" (peek cont_stack))

let gen_func = function
  | FuncDef { name; params; body; _ } ->
      Hashtbl.clear locals; stack_offset := 0; depth := 0; ret_label := new_label (); break_stack := []; cont_stack := [];
      List.iter (fun (p : param) -> Option.iter (fun n -> alloc_local n p.ty) p.name) params;
      collect_decls body;
      let frame_size = align_to !stack_offset 16 in
      emit (Printf.sprintf "  .globl %s" name); emit (name ^ ":");
      emit (Printf.sprintf "  addi sp, sp, -%d" (frame_size + 16)); emit (Printf.sprintf "  sd ra, %d(sp)" (frame_size + 8)); emit (Printf.sprintf "  sd s0, %d(sp)" frame_size); emit (Printf.sprintf "  addi s0, sp, %d" (frame_size + 16));
      List.iteri (fun i (p : param) -> match p.name with Some pname when i < 8 -> (match Hashtbl.find_opt locals pname with Some (offset, _) -> emit (Printf.sprintf "  sd a%d, %d(s0)" i offset) | None -> ()) | _ -> ()) params;
      gen_stmt body;
      emit (!ret_label ^ ":"); emit (Printf.sprintf "  ld s0, %d(sp)" frame_size); emit (Printf.sprintf "  ld ra, %d(sp)" (frame_size + 8)); emit (Printf.sprintf "  addi sp, sp, %d" (frame_size + 16)); emit "  ret"
  | _ -> ()

let () =
  if Array.length Sys.argv < 2 then (prerr_endline "使い方: dune exec ./koma13.exe -- <source.c>"; exit 1);
  Typedef_env.reset ();
  let filename = Sys.argv.(1) in
  let source = Utils.read_file filename in
  let preprocessed = Preprocess.preprocess source filename in
  pre_register_typedef_names preprocessed;
  let prog = Frontend.parse_source ~already_preprocessed:true ~filename preprocessed in
  resolve_struct_types prog;
  List.iter (function FuncDef { body; _ } -> collect_strings_stmt body | _ -> ()) prog;
  emit_data_section ();
  emit "  .text";
  List.iter gen_func prog
