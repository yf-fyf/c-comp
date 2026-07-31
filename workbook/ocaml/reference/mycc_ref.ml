(*
   必修パート（コマ2〜16）の完成版リファレンス実装。
   koma16 と同じコード生成に、どの命令をどの生成関数が出したかを示す
   アセンブリコメントを付けたもの。
*)

open Ast_def

let size_of_ty = Struct_env.size_of_ty

(* ── 変数情報 ── *)

type var_info =
  | Local of { offset : int; ty : ty }
  | Global of { ty : ty }

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

(* ── アセンブリへのコメント ──
   どの命令をどの生成関数が出したのかを、出力を読むだけで追えるようにする。
   ctx に「いま生成を担当している場所」を積み、emit は担当が変わった行にだけ
   注記を付ける。同じ担当が続く間は繰り返さないので、注記で出力が埋もれない。
   --no-comments で素の出力に戻せる。 *)

let comments = ref true
let ctx : string list ref = ref []
let last_note = ref ""
let heading_depth = ref 0
(* 見出しは印字を遅らせるので、登録した時点の深さも一緒に覚えておく *)
let pending_heading : (string * int) option ref = ref None

(* 見出しは命令が実際に出るまで保留する。初期化なしの Decl のように
   1 命令も出さない文があり、先に出すと見出しだけが取り残される。 *)
let heading text = if !comments then pending_heading := Some (text, !heading_depth)

let emit line =
  if not !comments then print_endline line
  else begin
    (match !pending_heading with
    | Some (text, depth) ->
        pending_heading := None;
        last_note := "";
        print_endline (Printf.sprintf "# %s── %s" (String.make (2 * depth) ' ') text)
    | None -> ());
    match !ctx with
    | note :: _ when note <> "" && note <> !last_note ->
        last_note := note;
        print_endline (Printf.sprintf "%-28s # %s" line note)
    | _ -> print_endline line
  end

(* f が出す命令の担当を note にする *)
let with_note note f =
  ctx := note :: !ctx;
  let result = f () in
  ctx := List.tl !ctx;
  result

(* この 1 行にだけ注記を付ける（ラベルや分岐など、担当より用途を書きたい場所） *)
let emit_note line note = with_note note (fun () -> last_note := ""; emit line)

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

(* ── 注記の文言 ── *)

let ty_note ty =
  let name =
    match ty with
    | TyInt -> "int"
    | TyChar -> "char"
    | TyVoid -> "void"
    | TyPtr _ -> "ポインタ"
    | TyStruct tag -> "struct " ^ tag
  in
  Printf.sprintf "%s（%d バイト）" name (size_of_ty ty)

let binop_name = function
  | Add -> "Add" | Sub -> "Sub" | Mul -> "Mul" | Div -> "Div" | Mod -> "Mod"
  | Eq -> "Eq" | Ne -> "Ne" | Lt -> "Lt" | Le -> "Le" | And -> "And" | Or -> "Or"

let unop_name = function
  | Neg -> "Neg" | Not -> "Not" | Addr -> "Addr" | Deref -> "Deref"
  | PreInc -> "PreInc" | PreDec -> "PreDec"

(* 「codegen: Binary Add」のような、生成関数と AST ノードの組を作る *)
let expr_note func expr =
  let node =
    match expr with
    | Num { value; _ } -> Printf.sprintf "Num %d" value
    | StrLit _ -> "StrLit"
    | Var { name; _ } -> Printf.sprintf "Var \"%s\"" name
    | Assign _ -> "Assign"
    | Binary { op; _ } -> "Binary " ^ binop_name op
    | Unary { op; _ } -> "Unary " ^ unop_name op
    | Index _ -> "Index"
    | Member { name; is_arrow; _ } ->
        Printf.sprintf "Member \"%s%s\"" (if is_arrow then "->" else ".") name
    | SizeofType _ -> "SizeofType"
    | Cond _ -> "Cond"
    | Call { name; _ } -> Printf.sprintf "Call \"%s\"" name
  in
  func ^ ": " ^ node

(* ── 文の見出し（元の C を切り出す） ──
   行番号ではなく span で本文を切り出す。前処理で #include を展開すると
   行番号はずれるが、span は前処理後ソースへの位置なので必ず一致する。 *)

let current_source = ref ""

let span_of_stmt = function
  | Block { span; _ } | ExprStmt { span; _ } | Return { span; _ }
  | Break { span; _ } | Continue { span; _ } | If { span; _ }
  | While { span; _ } | For { span; _ } | Decl { span; _ } ->
      span

let stmt_kind = function
  | Block _ -> "Block" | ExprStmt _ -> "ExprStmt" | Return _ -> "Return"
  | Break _ -> "Break" | Continue _ -> "Continue" | If _ -> "If"
  | While _ -> "While" | For _ -> "For" | Decl _ -> "Decl"

(* 空白を 1 個に潰し、長すぎる文は先頭だけ見せる（UTF-8 の途中では切らない） *)
let condense text limit =
  let buf = Buffer.create (String.length text) in
  let space = ref true in
  String.iter
    (fun ch ->
      match ch with
      | ' ' | '\t' | '\n' | '\r' -> if not !space then (Buffer.add_char buf ' '; space := true)
      | _ -> Buffer.add_char buf ch; space := false)
    text;
  let s = String.trim (Buffer.contents buf) in
  if String.length s <= limit then s
  else begin
    let cut = ref limit in
    while !cut > 0 && Char.code s.[!cut] land 0xc0 = 0x80 do decr cut done;
    String.sub s 0 !cut ^ " …"
  end

let source_slice start_offset end_offset =
  if start_offset < 0 || end_offset > String.length !current_source
     || end_offset <= start_offset
  then None
  else Some (String.sub !current_source start_offset (end_offset - start_offset))

let stmt_heading stmt =
  let kind = stmt_kind stmt in
  (* if / while / for は本体まで span に含むので、丸括弧の中身までで切る *)
  let head_end =
    let end_of expr = Option.map (fun (s : source_span) -> s.end_offset) (span_of_expr expr) in
    match stmt with
    | If { cond; _ } | While { cond; _ } -> end_of cond
    | For { init; cond; step; _ } ->
        List.fold_left
          (fun acc e -> match e with Some e -> (match end_of e with Some _ as r -> r | None -> acc) | None -> acc)
          None [ init; cond; step ]
    | _ -> None
  in
  let text =
    match span_of_stmt stmt with
    | None -> None
    | Some { start_offset; end_offset } -> (
        match head_end with
        | Some stop when stop > start_offset ->
            Option.map (fun t -> condense t 60 ^ ") ...") (source_slice start_offset stop)
        | _ -> Option.map (fun t -> condense t 60) (source_slice start_offset end_offset))
  in
  match text with
  | Some t -> Printf.sprintf "%s  [gen_stmt: %s]" t kind
  | None -> Printf.sprintf "[gen_stmt: %s]" kind

(* ── 構造体レイアウト ──
   struct 定義は support の構文解析時に Struct_env へ登録される。 *)

(* ── グローバル変数宣言の収集 ──
   初期化子はない。グローバル変数はすべて .bss に置かれ 0 に初期化される。 *)

let collect_global_decls prog =
  List.iter
    (function
      | GlobalDecl { name; ty; _ } -> Hashtbl.replace globals name (Global { ty })
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
  | Unary { operand; _ } | Member { base = operand; _ } ->
      collect_strings_expr operand
  | Cond { cond; then_; else_; _ } ->
      collect_strings_expr cond;
      collect_strings_expr then_;
      collect_strings_expr else_
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
  | Decl _ -> ()
  | Break _ | Continue _ -> ()

let collect_strings_top = function
  | FuncDef { body; _ } -> collect_strings_stmt body
  | GlobalDecl _ | FuncProto _ -> ()

(* ── データセクション / BSS セクション出力 ── *)

let emit_data_section () =
  if Hashtbl.length string_literals > 0 then emit "  .data";
  Hashtbl.iter
    (fun s label ->
      emit (label ^ ":");
      String.iter (fun ch -> emit (Printf.sprintf "  .byte %d" (Char.code ch))) s;
      emit "  .byte 0")
    string_literals

let emit_bss_section () =
  if Hashtbl.length globals > 0 then emit "  .bss";
  Hashtbl.iter
    (fun name -> function
      | Global { ty } ->
          emit (Printf.sprintf "  .globl %s" name);
          emit (name ^ ":");
          emit (Printf.sprintf "  .zero %d" (align_to (size_of_ty ty) 8))
      | _ -> ())
    globals

(* ── 変数管理 ── *)

let lookup_var name line =
  match Hashtbl.find_opt locals name with
  | Some info -> info
  | None -> (
      match Hashtbl.find_opt globals name with
      | Some info -> info
      | None -> error ~line (Printf.sprintf "未定義の変数: '%s'" name))

let alloc_local name ty =
  stack_offset := !stack_offset + align_to (size_of_ty ty) 8;
  Hashtbl.replace locals name (Local { offset = -(16 + !stack_offset); ty })

let rec collect_decls = function
  | Decl { name; ty; _ } -> alloc_local name ty
  | Block { stmts; _ } -> List.iter collect_decls stmts
  | If { then_; else_; _ } -> collect_decls then_; Option.iter collect_decls else_
  | While { body; _ } | For { body; _ } -> collect_decls body
  | _ -> ()

(* ── 型システム補助関数 ── *)

let field_info struct_ty name line =
  match struct_ty with
  | TyStruct tag -> (
      match Struct_env.find tag with
      | None -> error ~line (Printf.sprintf "未定義の構造体: 'struct %s'" tag)
      | Some info -> (
          match List.assoc_opt name info.Struct_env.fields with
          | Some fi -> fi
          | None -> error ~line (Printf.sprintf "構造体にフィールド '%s' がありません" name)))
  | _ -> error ~line "構造体型ではありません"

let field_ty struct_ty name line = (field_info struct_ty name line).Struct_env.ty
let field_offset struct_ty name line = (field_info struct_ty name line).Struct_env.offset

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
      | TyPtr base_ty -> base_ty
      | _ -> error ~line "[] の対象がポインタではありません")
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
  | SizeofType _ -> TyInt
  | Unary { op = Neg | Not; _ } -> TyInt
  | Unary { op = PreInc; operand; _ } | Unary { op = PreDec; operand; _ } ->
      type_of_lval operand
  | Cond { then_; _ } -> type_of then_
  | Binary { op = Add; lhs; rhs; _ } ->
      let lt = type_of lhs and rt = type_of rhs in
      (match lt, rt with TyPtr _, _ -> lt | _, TyPtr _ -> rt | _ -> TyInt)
  | Binary { op = Sub; lhs; _ } ->
      let lt = type_of lhs in
      (match lt with TyPtr _ -> lt | _ -> TyInt)
  | Binary _ -> TyInt

(* ── コード生成補助 ── *)

let load ty =
  with_note (Printf.sprintf "load: a0 のアドレスから%sを読む" (ty_note ty)) (fun () ->
      match size_of_ty ty with
      | 1 -> emit "  lb a0, 0(a0)"
      | 4 -> emit "  lw a0, 0(a0)"
      | _ -> emit "  ld a0, 0(a0)")

let store ty =
  with_note (Printf.sprintf "store: a1 のアドレスへ%sを書く" (ty_note ty)) (fun () ->
      match size_of_ty ty with
      | 1 -> emit "  sb a0, 0(a1)"
      | 4 -> emit "  sw a0, 0(a1)"
      | _ -> emit "  sd a0, 0(a1)")

let scale_index elem_ty =
  let sz = size_of_ty elem_ty in
  if sz <> 1 then
    with_note (Printf.sprintf "scale_index: 添字に要素の大きさ %d を掛ける" sz) (fun () ->
        emit (Printf.sprintf "  li a1, %d" sz);
        emit "  mul a0, a0, a1")

let push_a0 () =
  with_note "push_a0: a0 をスタックへ退避" (fun () ->
      emit "  addi sp, sp, -8";
      emit "  sd a0, 0(sp)");
  incr depth

let pop_into reg =
  with_note (Printf.sprintf "pop_into: 退避した値を %s へ戻す" reg) (fun () ->
      emit (Printf.sprintf "  ld %s, 0(sp)" reg);
      emit "  addi sp, sp, 8");
  decr depth

(* ── 左辺値のコード生成 ── *)

(* 本体には手を入れず、注記を付けるためのラッパを再帰の輪に足す。
   codegen_lval_body の中の再帰呼び出しはこちらを指すので、
   どの深さの部分式にも自動で担当が付く。 *)
let rec codegen_lval expr =
  with_note (expr_note "codegen_lval" expr) (fun () -> codegen_lval_body expr)

and codegen_lval_body = function
  | Var { name; line; _ } -> (
      match lookup_var name line with
      | Local { offset; _ } -> emit (Printf.sprintf "  addi a0, s0, %d" offset)
      | Global _ -> emit (Printf.sprintf "  la a0, %s" name))
  | Unary { op = Deref; operand; _ } -> codegen operand
  | Index { base; index; line; _ } ->
      let base_ty = type_of base in
      let elem_ty =
        match base_ty with
        | TyPtr e -> e
        | _ -> error ~line "[] の対象がポインタではありません"
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
  if n > 0 then
    with_note
      (if n = 1 then "gen_call: 積んだ引数を a0 へ移す"
       else Printf.sprintf "gen_call: 積んだ引数を a0–a%d へ移す" (n - 1))
      (fun () ->
        for i = 0 to n - 1 do
          emit (Printf.sprintf "  ld a%d, %d(sp)" i ((n - 1 - i) * 8))
        done);
  if n > 0 then (
    emit_note
      (Printf.sprintf "  addi sp, sp, %d" (n * 8))
      "gen_call: 引数を積んだ分の sp を戻す";
    depth := !depth - n);
  (* 呼び出しを囲む式が積んでいる一時値は 1 個 8 バイト。
     奇数個なら sp が 16 バイト境界からずれているので詰める（呼び出し規約）。 *)
  let pad = if !depth mod 2 <> 0 then 8 else 0 in
  if pad <> 0 then
    emit_note
      (Printf.sprintf "  addi sp, sp, -%d" pad)
      "gen_call: sp を 16 バイト境界へ揃える（呼び出し規約）";
  emit_note (Printf.sprintf "  call %s" name) (Printf.sprintf "gen_call: %s を呼ぶ" name);
  if pad <> 0 then
    emit_note
      (Printf.sprintf "  addi sp, sp, %d" pad)
      "gen_call: 揃えるために詰めた分を戻す"

(* ── 式のコード生成 ── *)

and codegen expr = with_note (expr_note "codegen" expr) (fun () -> codegen_body expr)

and codegen_body = function
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
  | Unary { op = PreInc; operand; _ } ->
      let ty = type_of_lval operand in
      let delta = match ty with TyPtr e -> size_of_ty e | _ -> 1 in
      codegen_lval operand;
      push_a0 ();
      load ty;
      emit (Printf.sprintf "  addi a0, a0, %d" delta);
      pop_into "a1";
      store ty
  | Unary { op = PreDec; operand; _ } ->
      let ty = type_of_lval operand in
      let delta = match ty with TyPtr e -> size_of_ty e | _ -> 1 in
      codegen_lval operand;
      push_a0 ();
      load ty;
      emit (Printf.sprintf "  addi a0, a0, %d" (-delta));
      pop_into "a1";
      store ty
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
  | SizeofType { ty; _ } -> emit (Printf.sprintf "  li a0, %d" (size_of_ty ty))
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

(* ── 文のコード生成 ── *)

(* 文ごとに元の C を見出しとして出す。Block は自分では何も出さないので
   見出しも字下げも増やさず、中の文にそれぞれ付ける。 *)
let rec gen_stmt stmt =
  match stmt with
  | Block _ -> gen_stmt_body stmt
  | _ ->
      heading (stmt_heading stmt);
      incr heading_depth;
      gen_stmt_body stmt;
      decr heading_depth

and gen_stmt_body = function
  | Decl _ -> ()
  | ExprStmt { expr; _ } -> Option.iter codegen expr
  | Return { expr; _ } ->
      Option.iter codegen expr;
      emit_note (Printf.sprintf "  j %s" !ret_label) "return: エピローグへ飛ぶ"
  | Block { stmts; _ } -> List.iter gen_stmt stmts
  | If { cond; then_; else_; _ } ->
      let label_else = new_label () in
      codegen cond;
      emit_note
        (Printf.sprintf "  beqz a0, %s" label_else)
        (if else_ = None then "if: 条件が偽なら then を飛ばす" else "if: 条件が偽なら else へ");
      gen_stmt then_;
      (match else_ with
      | Some else_stmt ->
          let label_end = new_label () in
          emit_note (Printf.sprintf "  j %s" label_end) "if: then を終えたら else を飛ばす";
          emit_note (label_else ^ ":") "if: else の入口";
          gen_stmt else_stmt;
          emit_note (label_end ^ ":") "if: then と else の合流点"
      | None -> emit_note (label_else ^ ":") "if: 条件が偽のときの合流点")
  | While { cond; body; _ } ->
      let label_cond = new_label () in
      let label_end = new_label () in
      push break_stack label_end;
      push cont_stack label_cond;
      emit_note (label_cond ^ ":") "while: 条件の評価へ戻る先（continue の飛び先）";
      codegen cond;
      emit_note (Printf.sprintf "  beqz a0, %s" label_end) "while: 条件が偽ならループを抜ける";
      gen_stmt body;
      emit_note (Printf.sprintf "  j %s" label_cond) "while: 条件の評価へ戻る";
      emit_note (label_end ^ ":") "while: ループの出口（break の飛び先）";
      pop break_stack;
      pop cont_stack
  | For { init; cond; step; body; _ } ->
      let label_cond = new_label () in
      let label_step = new_label () in
      let label_end = new_label () in
      push break_stack label_end;
      push cont_stack label_step;
      Option.iter codegen init;
      emit_note (label_cond ^ ":") "for: 条件の評価へ戻る先";
      Option.iter
        (fun c ->
          codegen c;
          emit_note (Printf.sprintf "  beqz a0, %s" label_end) "for: 条件が偽ならループを抜ける")
        cond;
      gen_stmt body;
      emit_note (label_step ^ ":") "for: 更新式の入口（continue の飛び先）";
      Option.iter codegen step;
      emit_note (Printf.sprintf "  j %s" label_cond) "for: 条件の評価へ戻る";
      emit_note (label_end ^ ":") "for: ループの出口（break の飛び先）";
      pop break_stack;
      pop cont_stack
  | Break _ -> emit_note (Printf.sprintf "  j %s" (peek break_stack)) "break: ループの出口へ"
  | Continue _ -> emit_note (Printf.sprintf "  j %s" (peek cont_stack)) "continue: 更新式・条件へ"

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
      emit_note (name ^ ":")
        (Printf.sprintf "gen_func: %s（フレーム %d バイト）" name (frame_size + 16));
      with_note "gen_func: プロローグ（ra と s0 を退避して s0 を立てる）" (fun () ->
          emit (Printf.sprintf "  addi sp, sp, -%d" (frame_size + 16));
          emit (Printf.sprintf "  sd ra, %d(sp)" (frame_size + 8));
          emit (Printf.sprintf "  sd s0, %d(sp)" frame_size);
          emit (Printf.sprintf "  addi s0, sp, %d" (frame_size + 16)));
      with_note "gen_func: 引数レジスタをスタックへ写す" (fun () ->
          List.iteri
            (fun i (p : param) ->
              match p.name with
              | Some pname when i < 8 -> (
                  match Hashtbl.find_opt locals pname with
                  | Some (Local { offset; _ }) -> emit (Printf.sprintf "  sd a%d, %d(s0)" i offset)
                  | _ -> ())
              | _ -> ())
            params);
      gen_stmt body;
      emit_note (!ret_label ^ ":") "gen_func: return の飛び先";
      with_note "gen_func: エピローグ（s0 と ra を戻して sp を返す）" (fun () ->
          emit (Printf.sprintf "  ld s0, %d(sp)" frame_size);
          emit (Printf.sprintf "  ld ra, %d(sp)" (frame_size + 8));
          emit (Printf.sprintf "  addi sp, sp, %d" (frame_size + 16));
          emit "  ret")
  | _ -> ()

(* ── プログラム全体のビルド ── *)

(* 見出しに元の C を出すため、前処理後ソースも一緒に返す。
   span はこのソースへの位置なので、ファイルごとに対応付けておく必要がある。 *)
let parse_file filename =
  let source = Utils.read_file filename in
  let preprocessed = Preprocess.preprocess source filename in
  let prog = Frontend.parse_source ~already_preprocessed:true ~filename preprocessed in
  (preprocessed, prog)

(* units は (前処理後ソース, そのファイルの宣言列) の並び *)
let gen_program units =
  let prog = List.concat_map snd units in
  collect_global_decls prog;
  List.iter collect_strings_top prog;
  emit_data_section ();
  emit_bss_section ();
  emit "  .text";
  List.iter
    (fun (source, decls) ->
      current_source := source;
      List.iter gen_func decls)
    units

let () =
  let args = List.tl (Array.to_list Sys.argv) in
  let files = List.filter (fun a -> a <> "--no-comments") args in
  if List.mem "--no-comments" args then comments := false;
  if files = [] then (
    prerr_endline "使い方: dune exec ./mycc_ref.exe -- [--no-comments] <source.c> [...]";
    prerr_endline "  --no-comments: 生成元を示すコメントを付けずに出力する";
    exit 1);
  Struct_env.reset ();
  gen_program (List.map parse_file files)
