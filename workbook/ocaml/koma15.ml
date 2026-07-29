(*
   コマ 15: 複数ファイル + 前処理 (#include / #define) — マルチファイルコンパイル
*)

open Ast_def

(* ── 変数情報 ── *)

type var_info =
  | Local of { offset : int; ty : ty }
  | Global of { ty : ty; init : int option }

(* ── グローバル mutable 状態 ── *)

let globals : (string, var_info) Hashtbl.t = Hashtbl.create 64
let locals : (string, var_info) Hashtbl.t = Hashtbl.create 128
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

let emit line = print_endline line
let align_to n align = ((n + align - 1) / align) * align

let error ?(line = 0) msg =
  let prefix = if line = 0 then "" else Printf.sprintf "[line %d] " line in
  prerr_endline (Printf.sprintf "OCamlコード生成エラー: %s%s" prefix msg);
  exit 1

let new_label () =
  incr label_count;
  Printf.sprintf ".L%d" !label_count

let push st x = st := x :: !st
let pop st = match !st with [] -> () | _ :: xs -> st := xs
let peek st = match !st with x :: _ -> x | [] -> error "空のラベルスタックです"

(* ── 構造体レイアウトの解決（パーサーが生成した StructDef から） ── *)

(* 最小限の先読み: typedef 名だけを事前登録する。
   LALR(1) 先読み対策 — パーサーが typedef 文を還元する前に
   次のトークンが読まれるため、事前に名前を登録しておく。 *)
let pre_register_typedef_names source =
  (* typedef を見つけたら、{ } の入れ子を数えて正しい末尾 ; を探し、
     その直前の単語を型名として登録する *)
  let typedef_re = Str.regexp "typedef[ \t\n\r]" in
  let pos = ref 0 in
  try
    while true do
      ignore (Str.search_forward typedef_re source !pos);
      let start = Str.match_end () in
      (* { } の深さを数えながら ; を探す *)
      let brace_depth = ref 0 in
      let semi_pos = ref start in
      let found = ref false in
      let i = ref start in
      while !i < String.length source && not !found do
        let c = source.[!i] in
        (match c with
        | '{' -> incr brace_depth
        | '}' -> decr brace_depth
        | ';' when !brace_depth = 0 -> semi_pos := !i; found := true
        | _ -> ());
        incr i
      done;
      if not !found then raise Not_found;
      let text = String.sub source start (!semi_pos - start) in
      (* 末尾から空白で区切って最後の単語を抽出 *)
      let rec scan_name i =
        if i < 0 then ("", 0)
        else
          let c = text.[i] in
          if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c = '_' then
            scan_name (i - 1)
          else (String.sub text (i + 1) (String.length text - i - 1), i)
      in
      let name, _ = scan_name (String.length text - 1) in
      let name = String.trim name in
      if String.length name > 0 then
        Typedef_env.register_name name (TyUnknown name);
      pos := !semi_pos + 1
    done
  with Not_found -> ()

let resolve_struct_types prog =
  List.iter (function
    | StructDef { tag; fields; name; _ } ->
        let offset, fields_with_offset =
          List.fold_left (fun (offset, acc) (fname, fty) ->
              let align = min (size_of_ty fty) 8 in
              let offset = align_to offset align in
              let next = offset + size_of_ty fty in
              (next, ((fname, { offset; ty = fty }) :: acc)))
            (0, []) fields
        in
        let total_size = align_to offset 8 in
        let fields_with_offset = List.rev fields_with_offset in
        let struct_ty = TyStruct { name = tag; fields = fields_with_offset; size = total_size } in
        Typedef_env.set name struct_ty;
        Option.iter (fun t -> Typedef_env.set ("struct " ^ t) struct_ty) tag
    | _ -> ())
    prog

(* ── TyUnknown 解決 ── *)

(* Typedef_env 経由で TyUnknown を解決する *)
let rec resolve_ty = function
  | TyUnknown name -> (match Typedef_env.find name with Some ty -> resolve_ty ty | None -> TyUnknown name)
  | TyPtr t -> TyPtr (resolve_ty t)
  | TyArray a -> TyArray { a with elem = resolve_ty a.elem }
  | ty -> ty

(* ── グローバル変数宣言の収集 ── *)

let const_int_expr = function
  | None -> None
  | Some (Num { value; _ }) -> Some value
  | Some (Unary { op = Neg; operand = Num { value; _ }; _ }) -> Some (-value)
  | Some e -> error ~line:(line_of_expr e) "グローバル変数の初期値は整数定数だけに対応しています"

let collect_global_decls prog =
  List.iter
    (function
      | GlobalDecl { name; ty; init_expr; _ } ->
          let ty = resolve_ty ty in
          Hashtbl.replace globals name
            (Global { ty; init = const_int_expr init_expr })
      | _ -> ())
    prog

(* ── 文字列リテラルの収集 ── *)

let intern_string s =
  match Hashtbl.find_opt string_literals s with
  | Some label -> label
  | None ->
      incr string_label_count;
      let label = Printf.sprintf ".LC%d" !string_label_count in
      Hashtbl.replace string_literals s label;
      label

let rec collect_strings_expr = function
  | StrLit { value; _ } -> ignore (intern_string value)
  | Assign { lhs; rhs; _ } | Binary { lhs; rhs; _ } | Index { base = lhs; index = rhs; _ } ->
      collect_strings_expr lhs;
      collect_strings_expr rhs
  | Unary { operand; _ } | SizeofExpr { operand; _ } | Member { base = operand; _ } ->
      collect_strings_expr operand
  | Call { args; _ } -> List.iter collect_strings_expr args
  | Num _ | Var _ | SizeofType _ -> ()

let rec collect_strings_stmt = function
  | Block { stmts; _ } -> List.iter collect_strings_stmt stmts
  | ExprStmt { expr; _ } | Return { expr; _ } -> Option.iter collect_strings_expr expr
  | If { cond; then_; else_; _ } ->
      collect_strings_expr cond;
      collect_strings_stmt then_;
      Option.iter collect_strings_stmt else_
  | While { cond; body; _ } ->
      collect_strings_expr cond;
      collect_strings_stmt body
  | For { init; cond; step; body; _ } ->
      Option.iter collect_strings_expr init;
      Option.iter collect_strings_expr cond;
      Option.iter collect_strings_expr step;
      collect_strings_stmt body
  | Decl { init_expr; _ } -> Option.iter collect_strings_expr init_expr
  | Break _ | Continue _ -> ()

let collect_strings_top = function
  | FuncDef { body; _ } -> collect_strings_stmt body
  | GlobalDecl { init_expr; _ } -> Option.iter collect_strings_expr init_expr
  | FuncProto _ | StructDef _ -> ()

(* ── データセクション / BSS セクション出力 ── *)

let emit_data_section () =
  let has_init = ref false in
  Hashtbl.iter (fun _ -> function Global { init = Some _; _ } -> has_init := true | _ -> ()) globals;
  if Hashtbl.length string_literals > 0 || !has_init then emit "  .data";
  Hashtbl.iter
    (fun s label ->
      emit (label ^ ":");
      String.iter (fun ch -> emit (Printf.sprintf "  .byte %d" (Char.code ch))) s;
      emit "  .byte 0")
    string_literals;
  Hashtbl.iter
    (fun name -> function
      | Global { ty; init = Some v } ->
          emit (Printf.sprintf "  .globl %s" name);
          emit (name ^ ":");
          let sz = size_of_ty ty in
          if sz = 1 then emit (Printf.sprintf "  .byte %d" v)
          else if sz = 4 then emit (Printf.sprintf "  .word %d" v)
          else emit (Printf.sprintf "  .dword %d" v)
      | _ -> ())
    globals

let emit_bss_section () =
  let has_uninit = ref false in
  Hashtbl.iter (fun _ -> function Global { init = None; _ } -> has_uninit := true | _ -> ()) globals;
  if !has_uninit then emit "  .bss";
  Hashtbl.iter
    (fun name -> function
      | Global { ty; init = None } ->
          emit (Printf.sprintf "  .globl %s" name);
          emit (name ^ ":");
          emit (Printf.sprintf "  .zero %d" (align_to (size_of_ty ty) 8))
      | _ -> ())
    globals

(* ── 変数管理 ── *)

let lookup_var name line =
  let resolve = function
    | Local { offset; ty } -> Local { offset; ty = resolve_ty ty }
    | Global { ty; init } -> Global { ty = resolve_ty ty; init }
  in
  match Hashtbl.find_opt locals name with
  | Some info -> resolve info
  | None -> (
      match Hashtbl.find_opt globals name with
      | Some info -> resolve info
      | None -> error ~line (Printf.sprintf "未定義の変数: '%s'" name))

let alloc_local name ty =
  let ty = resolve_ty ty in
  stack_offset := !stack_offset + align_to (size_of_ty ty) 8;
  Hashtbl.replace locals name (Local { offset = -(16 + !stack_offset); ty })

let rec collect_decls = function
  | Decl { name; ty; _ } -> alloc_local name ty
  | Block { stmts; _ } -> List.iter collect_decls stmts
  | If { then_; else_; _ } -> collect_decls then_; Option.iter collect_decls else_
  | While { body; _ } | For { body; _ } -> collect_decls body
  | _ -> ()

(* ── 型システム補助関数 ── *)

let field_ty struct_ty name line =
  match struct_ty with
  | TyStruct { fields; _ } -> (
      match List.assoc_opt name fields with
      | Some fi -> fi.ty
      | None -> error ~line (Printf.sprintf "構造体にフィールド '%s' がありません" name))
  | _ -> error ~line "構造体型ではありません"

let field_offset struct_ty name line =
  match struct_ty with
  | TyStruct { fields; _ } -> (
      match List.assoc_opt name fields with
      | Some fi -> fi.offset
      | None -> error ~line (Printf.sprintf "構造体にフィールド '%s' がありません" name))
  | _ -> error ~line "構造体型ではありません"

(* ── lvalue の型推論 ── *)

let rec type_of_lval = function
  | Var { name; line; _ } -> (
      match lookup_var name line with Local { ty; _ } | Global { ty; _ } -> ty)
  | Unary { op = Deref; operand; line; _ } -> (
      match type_of operand with
      | TyPtr base -> base
      | _ -> error ~line "* の対象がポインタではありません")
  | Index { base; line; _ } -> (
      match type_of base with
      | TyPtr base_ty | TyArray { elem = base_ty; _ } -> base_ty
      | _ -> error ~line "[] の対象が配列またはポインタではありません")
  | Member { base; name; is_arrow; line; _ } ->
      let struct_ty =
        if is_arrow then
          match type_of base with
          | TyPtr (TyStruct _ as s) -> s
          | _ -> error ~line "-> の対象が構造体ポインタではありません"
        else
          match type_of_lval base with
          | TyStruct _ as s -> s
          | _ -> error ~line ". の対象が構造体ではありません"
      in
      field_ty struct_ty name line
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

and type_of = function
  | Num _ -> TyInt
  | StrLit _ -> TyPtr TyChar
  | Var _ as v -> type_of_lval v
  | Unary { op = Addr; operand; _ } -> TyPtr (type_of_lval operand)
  | Unary { op = Deref; operand; line; _ } -> (
      match type_of operand with
      | TyPtr base -> base
      | _ -> error ~line "* の対象がポインタではありません")
  | Index _ as e -> type_of_lval e
  | Member _ as e -> type_of_lval e
  | Assign { lhs; _ } -> type_of_lval lhs
  | Call _ -> TyInt
  | SizeofType _ | SizeofExpr _ -> TyInt
  | Unary { op = Neg | Not | BitNot; _ } -> TyInt
  | Binary { op = Add; lhs; rhs; _ } ->
      let lt = type_of lhs and rt = type_of rhs in
      (match lt, rt with TyPtr _, _ -> lt | _, TyPtr _ -> rt | _ -> TyInt)
  | Binary { op = Sub; lhs; _ } ->
      let lt = type_of lhs in
      (match lt with TyPtr _ -> lt | _ -> TyInt)
  | Binary _ -> TyInt

(* ── コード生成補助 ── *)

let load ty =
  match ty with
  | TyArray _ -> ()
  | _ -> (
      match size_of_ty ty with
      | 1 -> emit "  lb a0, 0(a0)"
      | 4 -> emit "  lw a0, 0(a0)"
      | _ -> emit "  ld a0, 0(a0)")

let store ty =
  match size_of_ty ty with
  | 1 -> emit "  sb a0, 0(a1)"
  | 4 -> emit "  sw a0, 0(a1)"
  | _ -> emit "  sd a0, 0(a1)"

let scale_index elem_ty =
  let sz = size_of_ty elem_ty in
  if sz <> 1 then (
    emit (Printf.sprintf "  li a1, %d" sz);
    emit "  mul a0, a0, a1")

let push_a0 () = emit "  addi sp, sp, -8"; emit "  sd a0, 0(sp)"; incr depth
let pop_into reg = emit (Printf.sprintf "  ld %s, 0(sp)" reg); emit "  addi sp, sp, 8"; decr depth

(* ── 左辺値のコード生成 ── *)

let rec codegen_lval = function
  | Var { name; line; _ } -> (
      match lookup_var name line with
      | Local { offset; _ } -> emit (Printf.sprintf "  addi a0, s0, %d" offset)
      | Global _ -> emit (Printf.sprintf "  la a0, %s" name))
  | Unary { op = Deref; operand; _ } -> codegen operand
  | Index { base; index; line; _ } ->
      let base_ty = type_of base in
      let elem_ty =
        match base_ty with
        | TyPtr e | TyArray { elem = e; _ } -> e
        | _ -> error ~line "[] の対象が配列またはポインタではありません"
      in
      codegen base;
      push_a0 ();
      codegen index;
      scale_index elem_ty;
      pop_into "a1";
      emit "  add a0, a1, a0"
  | Member { base; name; is_arrow; line; _ } ->
      let struct_ty =
        if is_arrow then (
          match type_of base with
          | TyPtr (TyStruct _ as s) -> codegen base; s
          | _ -> error ~line "-> の対象が構造体ポインタではありません")
        else (
          match type_of_lval base with
          | TyStruct _ as s -> codegen_lval base; s
          | _ -> error ~line ". の対象が構造体ではありません")
      in
      let offset = field_offset struct_ty name line in
      if offset <> 0 then emit (Printf.sprintf "  addi a0, a0, %d" offset)
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

(* ── 関数呼び出しのコード生成 ── *)

and gen_call name args _line =
  let n = List.length args in
  List.iter
    (fun arg ->
      codegen arg;
      push_a0 ())
    args;
  for i = 0 to n - 1 do
    emit (Printf.sprintf "  ld a%d, %d(sp)" i ((n - 1 - i) * 8))
  done;
  if n > 0 then (
    emit (Printf.sprintf "  addi sp, sp, %d" (n * 8));
    depth := !depth - n);
  (* 呼び出しを囲む式が積んでいる一時値は 1 個 8 バイト。
     奇数個なら sp が 16 バイト境界からずれているので詰める。 *)
  let pad = if !depth mod 2 <> 0 then 8 else 0 in
  if pad <> 0 then emit (Printf.sprintf "  addi sp, sp, -%d" pad);
  emit (Printf.sprintf "  call %s" name);
  if pad <> 0 then emit (Printf.sprintf "  addi sp, sp, %d" pad)

(* ── 式のコード生成 ── *)

and codegen = function
  | Num { value; _ } -> emit (Printf.sprintf "  li a0, %d" value)
  | StrLit { value; _ } -> emit (Printf.sprintf "  la a0, %s" (intern_string value))
  | Var _ as v ->
      let ty = type_of v in
      codegen_lval v;
      load ty
  | Unary { op = Addr; operand; _ } -> codegen_lval operand
  | Unary { op = Deref; operand; _ } as e ->
      let ty = type_of e in
      codegen operand;
      load ty
  | Index _ as e ->
      let ty = type_of e in
      codegen_lval e;
      load ty
  | Member _ as e ->
      let ty = type_of e in
      codegen_lval e;
      load ty
  | Assign { lhs; rhs; _ } ->
      let ty = type_of_lval lhs in
      codegen_lval lhs;
      push_a0 ();
      codegen rhs;
      pop_into "a1";
      store ty
  | Unary { op = Neg; operand; _ } -> codegen operand; emit "  neg a0, a0"
  | Unary { op = Not; operand; _ } -> codegen operand; emit "  seqz a0, a0"
  | Unary { op = BitNot; operand; _ } -> codegen operand; emit "  not a0, a0"
  | SizeofType { ty; _ } -> emit (Printf.sprintf "  li a0, %d" (size_of_ty ty))
  | SizeofExpr { operand; _ } -> emit (Printf.sprintf "  li a0, %d" (size_of_ty (type_of operand)))
  | Call { name; args; line; _ } -> gen_call name args line
  | Binary { op = Add; lhs; rhs; _ } ->
      let lt = type_of lhs and rt = type_of rhs in
      if is_ptr_ty lt || is_ptr_ty rt then codegen_pointer_add lhs rhs lt rt
      else codegen_binary Add lhs rhs
  | Binary { op = Sub; lhs; rhs; _ } ->
      let lt = type_of lhs in
      if is_ptr_ty lt then codegen_pointer_sub lhs rhs lt else codegen_binary Sub lhs rhs
  | Binary { op; lhs; rhs; _ } -> codegen_binary op lhs rhs

(* ── ポインタ演算（ptr + int / ptr - int） ── *)

and codegen_pointer_add lhs rhs lhs_ty rhs_ty =
  let ptr_expr, int_expr, ptr_ty =
    if is_ptr_ty lhs_ty then (lhs, rhs, lhs_ty)
    else (rhs, lhs, rhs_ty)
  in
  let elem_ty = match ptr_ty with TyPtr e -> e | _ -> assert false in
  codegen ptr_expr;
  push_a0 ();
  codegen int_expr;
  scale_index elem_ty;
  pop_into "a1";
  emit "  add a0, a1, a0"

and codegen_pointer_sub lhs rhs lhs_ty =
  let elem_ty = match lhs_ty with TyPtr e -> e | _ -> assert false in
  codegen lhs;
  push_a0 ();
  codegen rhs;
  scale_index elem_ty;
  pop_into "a1";
  emit "  sub a0, a1, a0"

(* ── 二項演算 ── *)

and codegen_binary op lhs rhs =
  codegen lhs;
  push_a0 ();
  codegen rhs;
  pop_into "a1";
  match op with
  | Add -> emit "  add a0, a1, a0"
  | Sub -> emit "  sub a0, a1, a0"
  | Mul -> emit "  mul a0, a1, a0"
  | Div -> emit "  div a0, a1, a0"
  | Mod -> emit "  rem a0, a1, a0"
  | Eq -> emit "  sub a0, a1, a0"; emit "  seqz a0, a0"
  | Ne -> emit "  sub a0, a1, a0"; emit "  snez a0, a0"
  | Lt -> emit "  slt a0, a1, a0"
  | Le -> emit "  slt a0, a0, a1"; emit "  xori a0, a0, 1"
  | And -> emit "  snez a1, a1"; emit "  snez a0, a0"; emit "  and a0, a1, a0"
  | Or -> emit "  or a0, a1, a0"; emit "  snez a0, a0"
  | BitAnd -> emit "  and a0, a1, a0"
  | BitOr -> emit "  or a0, a1, a0"
  | BitXor -> emit "  xor a0, a1, a0"
  | Shl -> emit "  sll a0, a1, a0"
  | Shr -> emit "  sra a0, a1, a0"

(* ── 文のコード生成 ── *)

let rec gen_stmt = function
  | Decl { name; init_expr = Some init_expr; line; _ } ->
      codegen (Assign { lhs = Var { name; line; span = None }; rhs = init_expr; line; span = None })
  | Decl _ -> ()
  | ExprStmt { expr; _ } -> Option.iter codegen expr
  | Return { expr; _ } -> Option.iter codegen expr; emit (Printf.sprintf "  j %s" !ret_label)
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

(* ── 関数のコード生成 ── *)

let gen_func = function
  | FuncDef { name; params; body; _ } ->
      Hashtbl.clear locals;
      stack_offset := 0;
      depth := 0;
      ret_label := new_label ();
      break_stack := [];
      cont_stack := [];
      List.iter (fun (p : param) -> Option.iter (fun name -> alloc_local name p.ty) p.name) params;
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
          | Some pname when i < 8 -> (
              match Hashtbl.find_opt locals pname with
              | Some (Local { offset; _ }) -> emit (Printf.sprintf "  sd a%d, %d(s0)" i offset)
              | _ -> ())
          | _ -> ())
        params;
      gen_stmt body;
      emit (!ret_label ^ ":");
      emit (Printf.sprintf "  ld s0, %d(sp)" frame_size);
      emit (Printf.sprintf "  ld ra, %d(sp)" (frame_size + 8));
      emit (Printf.sprintf "  addi sp, sp, %d" (frame_size + 16));
      emit "  ret"
  | _ -> ()

(* ── プログラム全体のビルド ── *)

let parse_file filename =
  Typedef_env.reset ();
  let source = Utils.read_file filename in
  let preprocessed = Preprocess.preprocess source filename in
  pre_register_typedef_names preprocessed;
  let prog = Frontend.parse_source ~already_preprocessed:true ~filename preprocessed in
  resolve_struct_types prog;
  prog

let gen_program prog =
  collect_global_decls prog;
  List.iter collect_strings_top prog;
  emit_data_section ();
  emit_bss_section ();
  emit "  .text";
  List.iter gen_func prog

let () =
  if Array.length Sys.argv < 2 then (
    prerr_endline "使い方: dune exec ./koma15.exe -- <source.c> [...]";
    exit 1);
  let prog = ref [] in
  for i = 1 to Array.length Sys.argv - 1 do
    prog := !prog @ parse_file Sys.argv.(i)
  done;
  gen_program !prog
