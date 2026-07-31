(*
   コンパイラ本体。AST を受け取り、Emitter へアセンブリを流し込む。

   走査の順番と主要な関数名（codegen / codegen_lval / gen_stmt / gen_func）は
   Python 版 mycc.py・OCaml 版 koma16.ml と揃えてある。違うのは状態の持ち方で、
   グローバルな可変変数ではなく、

     genv … プログラム全体（グローバル変数表・文字列リテラル表・ラベル連番）
     fenv … 関数 1 個の間だけ（ローカル変数表・フレーム・ループの飛び先）

   の 2 つのレコードを引数で持ち回る。gen_func は fenv を作り直すだけでよく、
   関数をまたぐ状態の消し忘れが起きない。
*)

open Ast_def

let size_of_ty = Struct_env.size_of_ty
let align_to n align = ((n + align - 1) / align) * align

(* ── エラー ──
   その場で exit せずに例外にする。呼び出し側（main）が印字と終了コードを決める。 *)

exception Error of { line : int; msg : string }

let error ?(line = 0) msg = raise (Error { line; msg })

let error_message line msg =
  let prefix = if line = 0 then "" else Printf.sprintf "[line %d] " line in
  Printf.sprintf "OCamlコード生成エラー: %s%s" prefix msg

(* ── 変数情報 ── *)

type var_info =
  | Local of { offset : int; ty : ty }
  | Global of { ty : ty }

(* ループ 1 個ぶんの飛び先。break と continue は必ず対で決まるので 1 本にまとめる。 *)
type loop = { break_to : Asm.label; continue_to : Asm.label }

(* ── プログラム全体の状態 ── *)

type genv = {
  em : Emitter.t;
  globals : (string, var_info) Hashtbl.t;
  strings : (string, Asm.label) Hashtbl.t;
  mutable label_count : int;
  mutable string_count : int;
  (* 見出しに元の C を切り出すための、いま生成中のファイルの前処理後ソース *)
  mutable source : string;
}

(* ── 関数 1 個の状態 ── *)

type fenv = {
  locals : (string, var_info) Hashtbl.t;
  mutable stack_offset : int;
  (* スタックに積んでいる一時値の個数（1 個 8 バイト）。
     call 直前に sp が 16 の倍数かどうかを判定するために数える。 *)
  mutable depth : int;
  ret_label : Asm.label;
  mutable loops : loop list;
}

let create_genv em =
  {
    em;
    globals = Hashtbl.create 64;
    strings = Hashtbl.create 64;
    label_count = 0;
    string_count = 0;
    source = "";
  }

let new_label g =
  g.label_count <- g.label_count + 1;
  Asm.L g.label_count

let create_fenv g =
  { locals = Hashtbl.create 128; stack_offset = 0; depth = 0; ret_label = new_label g; loops = [] }

let innermost_loop ?line f =
  match f.loops with loop :: _ -> loop | [] -> error ?line "ループの外にいます"

(* ── アセンブリへのコメント ──
   どの命令をどの生成関数が出したのかを、出力を読むだけで追えるようにする。
   with_note で「いま生成を担当している場所」を積み、note を明示した行には
   その 1 行だけの説明を付ける。見せ方の規則は Emitter.print 側が決める。 *)

let emit g ?note line = Emitter.emit g.em ?note line
let with_note g note f = Emitter.with_note g.em note f
let heading g text = Emitter.heading g.em text

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

let source_slice g start_offset end_offset =
  if start_offset < 0 || end_offset > String.length g.source || end_offset <= start_offset then None
  else Some (String.sub g.source start_offset (end_offset - start_offset))

let stmt_heading g stmt =
  let kind = stmt_kind stmt in
  (* if / while / for は本体まで span に含むので、丸括弧の中身までで切る *)
  let head_end =
    let end_of expr = Option.map (fun (s : source_span) -> s.end_offset) (span_of_expr expr) in
    match stmt with
    | If { cond; _ } | While { cond; _ } -> end_of cond
    | For { init; cond; step; _ } ->
        List.fold_left
          (fun acc e ->
            match e with
            | Some e -> (match end_of e with Some _ as r -> r | None -> acc)
            | None -> acc)
          None [ init; cond; step ]
    | _ -> None
  in
  let text =
    match span_of_stmt stmt with
    | None -> None
    | Some { start_offset; end_offset } -> (
        match head_end with
        | Some stop when stop > start_offset ->
            Option.map (fun t -> condense t 60 ^ ") ...") (source_slice g start_offset stop)
        | _ -> Option.map (fun t -> condense t 60) (source_slice g start_offset end_offset))
  in
  match text with
  | Some t -> Printf.sprintf "%s  [gen_stmt: %s]" t kind
  | None -> Printf.sprintf "[gen_stmt: %s]" kind

(* ── 構造体レイアウト ──
   struct 定義は support の構文解析時に Struct_env へ登録される。 *)

(* ── グローバル変数宣言の収集 ──
   初期化子はない。グローバル変数はすべて .bss に置かれ 0 に初期化される。 *)

let collect_global_decls g prog =
  List.iter
    (function
      | GlobalDecl { name; ty; _ } -> Hashtbl.replace g.globals name (Global { ty })
      | _ -> ())
    prog

(* ── 文字列リテラルの収集 ── *)

let intern_string g s =
  match Hashtbl.find_opt g.strings s with
  | Some label -> label
  | None ->
      g.string_count <- g.string_count + 1;
      let label = Asm.Lc g.string_count in
      Hashtbl.replace g.strings s label;
      label

let rec collect_strings_expr g = function
  | StrLit { value; _ } -> ignore (intern_string g value)
  | Assign { lhs; rhs; _ } | Binary { lhs; rhs; _ } | Index { base = lhs; index = rhs; _ } ->
      collect_strings_expr g lhs;
      collect_strings_expr g rhs
  | Unary { operand; _ } | Member { base = operand; _ } -> collect_strings_expr g operand
  | Cond { cond; then_; else_; _ } ->
      collect_strings_expr g cond;
      collect_strings_expr g then_;
      collect_strings_expr g else_
  | Call { args; _ } -> List.iter (collect_strings_expr g) args
  | Num _ | Var _ | SizeofType _ -> ()

let rec collect_strings_stmt g = function
  | Block { stmts; _ } -> List.iter (collect_strings_stmt g) stmts
  | ExprStmt { expr; _ } | Return { expr; _ } -> Option.iter (collect_strings_expr g) expr
  | If { cond; then_; else_; _ } ->
      collect_strings_expr g cond;
      collect_strings_stmt g then_;
      Option.iter (collect_strings_stmt g) else_
  | While { cond; body; _ } ->
      collect_strings_expr g cond;
      collect_strings_stmt g body
  | For { init; cond; step; body; _ } ->
      Option.iter (collect_strings_expr g) init;
      Option.iter (collect_strings_expr g) cond;
      Option.iter (collect_strings_expr g) step;
      collect_strings_stmt g body
  | Decl _ -> ()
  | Break _ | Continue _ -> ()

let collect_strings_top g = function
  | FuncDef { body; _ } -> collect_strings_stmt g body
  | GlobalDecl _ | FuncProto _ -> ()

(* ── データセクション / BSS セクション出力 ── *)

let emit_data_section g =
  if Hashtbl.length g.strings > 0 then emit g Asm.data;
  Hashtbl.iter
    (fun s label ->
      emit g (Asm.deflabel label);
      String.iter (fun ch -> emit g Asm.(byte (Char.code ch))) s;
      emit g (Asm.byte 0))
    g.strings

let emit_bss_section g =
  if Hashtbl.length g.globals > 0 then emit g Asm.bss;
  Hashtbl.iter
    (fun name -> function
      | Global { ty } ->
          emit g (Asm.globl name);
          emit g (Asm.defsym name);
          emit g Asm.(zero (align_to (size_of_ty ty) 8))
      | _ -> ())
    g.globals

(* ── 変数管理 ── *)

let lookup_var g f name line =
  match Hashtbl.find_opt f.locals name with
  | Some info -> info
  | None -> (
      match Hashtbl.find_opt g.globals name with
      | Some info -> info
      | None -> error ~line (Printf.sprintf "未定義の変数: '%s'" name))

let alloc_local f name ty =
  f.stack_offset <- f.stack_offset + align_to (size_of_ty ty) 8;
  Hashtbl.replace f.locals name (Local { offset = -(16 + f.stack_offset); ty })

let rec collect_decls f = function
  | Decl { name; ty; _ } -> alloc_local f name ty
  | Block { stmts; _ } -> List.iter (collect_decls f) stmts
  | If { then_; else_; _ } ->
      collect_decls f then_;
      Option.iter (collect_decls f) else_
  | While { body; _ } | For { body; _ } -> collect_decls f body
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

let rec type_of_lval g f = function
  | Var { name; line; _ } -> (
      match lookup_var g f name line with Local { ty; _ } | Global { ty; _ } -> ty)
  | Unary { op = Deref; operand; line; _ } -> (
      match type_of g f operand with
      | TyPtr base -> base
      | _ -> error ~line "* の対象がポインタではありません")
  | Index { base; line; _ } -> (
      match type_of g f base with
      | TyPtr base_ty -> base_ty
      | _ -> error ~line "[] の対象がポインタではありません")
  | Member { base; name; is_arrow; line; _ } ->
      let struct_ty = struct_ty_of_member g f base is_arrow line in
      field_ty struct_ty name line
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

and type_of g f = function
  | Num _ -> TyInt
  | StrLit _ -> TyPtr TyChar
  | Var _ as v -> type_of_lval g f v
  | Unary { op = Addr; operand; _ } -> TyPtr (type_of_lval g f operand)
  | Unary { op = Deref; operand; line; _ } -> (
      match type_of g f operand with
      | TyPtr base -> base
      | _ -> error ~line "* の対象がポインタではありません")
  | Index _ as e -> type_of_lval g f e
  | Member _ as e -> type_of_lval g f e
  | Assign { lhs; _ } -> type_of_lval g f lhs
  | Call _ -> TyInt
  | SizeofType _ -> TyInt
  | Unary { op = Neg | Not; _ } -> TyInt
  | Unary { op = PreInc; operand; _ } | Unary { op = PreDec; operand; _ } ->
      type_of_lval g f operand
  | Cond { then_; _ } -> type_of g f then_
  | Binary { op = Add; lhs; rhs; _ } ->
      let lt = type_of g f lhs and rt = type_of g f rhs in
      (match (lt, rt) with TyPtr _, _ -> lt | _, TyPtr _ -> rt | _ -> TyInt)
  | Binary { op = Sub; lhs; _ } -> (
      match type_of g f lhs with TyPtr _ as lt -> lt | _ -> TyInt)
  | Binary _ -> TyInt

(* `p->x` なら p の指す構造体、`v.x` なら v 自身の構造体 *)
and struct_ty_of_member g f base is_arrow line =
  if is_arrow then
    match type_of g f base with
    | TyPtr (TyStruct _ as s) -> s
    | _ -> error ~line "-> の対象が構造体ポインタではありません"
  else
    match type_of_lval g f base with
    | TyStruct _ as s -> s
    | _ -> error ~line ". の対象が構造体ではありません"

(* ── コード生成補助 ── *)

let load g ty =
  with_note g (Printf.sprintf "load: a0 のアドレスから%sを読む" (ty_note ty)) (fun () ->
      emit g Asm.(load (size_of_ty ty) a0 (at a0 0)))

let store g ty =
  with_note g (Printf.sprintf "store: a1 のアドレスへ%sを書く" (ty_note ty)) (fun () ->
      emit g Asm.(store (size_of_ty ty) a0 (at a1 0)))

let scale_index g elem_ty =
  let sz = size_of_ty elem_ty in
  if sz <> 1 then
    with_note g (Printf.sprintf "scale_index: 添字に要素の大きさ %d を掛ける" sz) (fun () ->
        emit g Asm.(li a1 sz);
        emit g Asm.(binop Mul a0 a0 a1))

let push_a0 g f =
  with_note g "push_a0: a0 をスタックへ退避" (fun () ->
      emit g Asm.(addi sp sp (-8));
      emit g Asm.(store 8 a0 (at sp 0)));
  f.depth <- f.depth + 1

let pop_into g f reg =
  with_note g (Printf.sprintf "pop_into: 退避した値を %s へ戻す" (Asm.reg_name reg)) (fun () ->
      emit g Asm.(load 8 reg (at sp 0));
      emit g Asm.(addi sp sp 8));
  f.depth <- f.depth - 1

(* ── 左辺値のコード生成 ── *)

(* 本体には手を入れず、注記を付けるためのラッパを再帰の輪に足す。
   codegen_lval_body の中の再帰呼び出しはこちらを指すので、
   どの深さの部分式にも自動で担当が付く。 *)
let rec codegen_lval g f expr =
  with_note g (expr_note "codegen_lval" expr) (fun () -> codegen_lval_body g f expr)

and codegen_lval_body g f = function
  | Var { name; line; _ } -> (
      match lookup_var g f name line with
      | Local { offset; _ } -> emit g Asm.(addi a0 s0 offset)
      | Global _ -> emit g Asm.(la a0 (Symbol name)))
  | Unary { op = Deref; operand; _ } -> codegen g f operand
  | Index { base; index; line; _ } ->
      let elem_ty =
        match type_of g f base with
        | TyPtr e -> e
        | _ -> error ~line "[] の対象がポインタではありません"
      in
      codegen g f base;
      push_a0 g f;
      codegen g f index;
      scale_index g elem_ty;
      pop_into g f Asm.A1;
      emit g Asm.(binop Add a0 a1 a0)
  | Member { base; name; is_arrow; line; _ } ->
      let struct_ty = struct_ty_of_member g f base is_arrow line in
      (* -> はポインタの値、. は入れ物のアドレスが要る *)
      if is_arrow then codegen g f base else codegen_lval g f base;
      let offset = field_offset struct_ty name line in
      if offset <> 0 then emit g Asm.(addi a0 a0 offset)
  | e -> error ~line:(line_of_expr e) "lvalue でない式です"

(* ── 関数呼び出しのコード生成 ── *)

and gen_call g f name args ~line =
  let n = List.length args in
  if n > Array.length Asm.arg_regs then
    error ~line
      (Printf.sprintf "%s の呼び出し: 引数は %d 個までです（%d 個渡されています）" name
         (Array.length Asm.arg_regs) n);
  List.iter
    (fun arg ->
      codegen g f arg;
      push_a0 g f)
    args;
  if n > 0 then begin
    with_note g
      (if n = 1 then "gen_call: 積んだ引数を a0 へ移す"
       else Printf.sprintf "gen_call: 積んだ引数を a0–a%d へ移す" (n - 1))
      (fun () ->
        for i = 0 to n - 1 do
          emit g Asm.(load 8 (arg_reg i) (at sp ((n - 1 - i) * 8)))
        done);
    emit g ~note:"gen_call: 引数を積んだ分の sp を戻す" Asm.(addi sp sp (n * 8));
    f.depth <- f.depth - n
  end;
  (* 呼び出しを囲む式が積んでいる一時値は 1 個 8 バイト。
     奇数個なら sp が 16 バイト境界からずれているので詰める（呼び出し規約）。 *)
  let pad = if f.depth mod 2 <> 0 then 8 else 0 in
  if pad <> 0 then
    emit g ~note:"gen_call: sp を 16 バイト境界へ揃える（呼び出し規約）" Asm.(addi sp sp (-pad));
  emit g ~note:(Printf.sprintf "gen_call: %s を呼ぶ" name) (Asm.call name);
  if pad <> 0 then emit g ~note:"gen_call: 揃えるために詰めた分を戻す" Asm.(addi sp sp pad)

(* ── 式のコード生成 ── *)

and codegen g f expr = with_note g (expr_note "codegen" expr) (fun () -> codegen_body g f expr)

and codegen_body g f = function
  | Num { value; _ } -> emit g Asm.(li a0 value)
  | StrLit { value; _ } -> emit g Asm.(la a0 (Label (intern_string g value)))
  | Var _ as v ->
      let ty = type_of g f v in
      codegen_lval g f v;
      load g ty
  | Unary { op = Addr; operand; _ } -> codegen_lval g f operand
  | Unary { op = Deref; operand; _ } as e ->
      let ty = type_of g f e in
      codegen g f operand;
      load g ty
  | (Index _ | Member _) as e ->
      let ty = type_of g f e in
      codegen_lval g f e;
      load g ty
  | Assign { lhs; rhs; _ } ->
      let ty = type_of_lval g f lhs in
      codegen_lval g f lhs;
      push_a0 g f;
      codegen g f rhs;
      pop_into g f Asm.A1;
      store g ty
  | Unary { op = Neg; operand; _ } ->
      codegen g f operand;
      emit g Asm.(unop Neg a0 a0)
  | Unary { op = Not; operand; _ } ->
      codegen g f operand;
      emit g Asm.(unop Seqz a0 a0)
  | Unary { op = (PreInc | PreDec) as op; operand; _ } ->
      let ty = type_of_lval g f operand in
      (* ポインタなら 1 要素ぶん、それ以外は 1 *)
      let step = match ty with TyPtr e -> size_of_ty e | _ -> 1 in
      let delta = if op = PreInc then step else -step in
      codegen_lval g f operand;
      push_a0 g f;
      load g ty;
      emit g Asm.(addi a0 a0 delta);
      pop_into g f Asm.A1;
      store g ty
  | Cond { cond; then_; else_; _ } ->
      let label_else = new_label g in
      let label_end = new_label g in
      codegen g f cond;
      emit g Asm.(beqz a0 label_else);
      codegen g f then_;
      emit g (Asm.j label_end);
      emit g (Asm.deflabel label_else);
      codegen g f else_;
      emit g (Asm.deflabel label_end)
  | SizeofType { ty; _ } -> emit g Asm.(li a0 (size_of_ty ty))
  | Call { name; args; line; _ } -> gen_call g f name args ~line
  | Binary { op = Add; lhs; rhs; _ } ->
      let lt = type_of g f lhs and rt = type_of g f rhs in
      if is_ptr_ty lt || is_ptr_ty rt then codegen_pointer_add g f lhs rhs lt rt
      else codegen_binary g f Add lhs rhs
  | Binary { op = Sub; lhs; rhs; _ } ->
      let lt = type_of g f lhs in
      if is_ptr_ty lt then codegen_pointer_sub g f lhs rhs lt else codegen_binary g f Sub lhs rhs
  | Binary { op; lhs; rhs; _ } -> codegen_binary g f op lhs rhs

(* ── ポインタ演算（ptr + int / ptr - int） ── *)

and codegen_pointer_add g f lhs rhs lhs_ty rhs_ty =
  let ptr_expr, int_expr, ptr_ty =
    if is_ptr_ty lhs_ty then (lhs, rhs, lhs_ty) else (rhs, lhs, rhs_ty)
  in
  let elem_ty = match ptr_ty with TyPtr e -> e | _ -> assert false in
  codegen g f ptr_expr;
  push_a0 g f;
  codegen g f int_expr;
  scale_index g elem_ty;
  pop_into g f Asm.A1;
  emit g Asm.(binop Add a0 a1 a0)

and codegen_pointer_sub g f lhs rhs lhs_ty =
  let elem_ty = match lhs_ty with TyPtr e -> e | _ -> assert false in
  codegen g f lhs;
  push_a0 g f;
  codegen g f rhs;
  scale_index g elem_ty;
  pop_into g f Asm.A1;
  emit g Asm.(binop Sub a0 a1 a0)

(* ── 二項演算 ──
   左を a1、右を a0 に置いてから演算する。 *)

and codegen_binary g f op lhs rhs =
  codegen g f lhs;
  push_a0 g f;
  codegen g f rhs;
  pop_into g f Asm.A1;
  let open Asm in
  match op with
  | Ast_def.Add -> emit g (binop Add a0 a1 a0)
  | Ast_def.Sub -> emit g (binop Sub a0 a1 a0)
  | Ast_def.Mul -> emit g (binop Mul a0 a1 a0)
  | Ast_def.Div -> emit g (binop Div a0 a1 a0)
  | Ast_def.Mod -> emit g (binop Rem a0 a1 a0)
  | Ast_def.Eq ->
      emit g (binop Sub a0 a1 a0);
      emit g (unop Seqz a0 a0)
  | Ast_def.Ne ->
      emit g (binop Sub a0 a1 a0);
      emit g (unop Snez a0 a0)
  | Ast_def.Lt -> emit g (binop Slt a0 a1 a0)
  | Ast_def.Le ->
      emit g (binop Slt a0 a0 a1);
      emit g (xori a0 a0 1)
  | Ast_def.And ->
      emit g (unop Snez a1 a1);
      emit g (unop Snez a0 a0);
      emit g (binop And a0 a1 a0)
  | Ast_def.Or ->
      emit g (binop Or a0 a1 a0);
      emit g (unop Snez a0 a0)

(* ── 文のコード生成 ── *)

(* 文ごとに元の C を見出しとして出す。Block は自分では何も出さないので
   見出しも字下げも増やさず、中の文にそれぞれ付ける。 *)
let rec gen_stmt g f stmt =
  match stmt with
  | Block _ -> gen_stmt_body g f stmt
  | _ ->
      heading g (stmt_heading g stmt);
      Emitter.nested g.em (fun () -> gen_stmt_body g f stmt)

(* ループ本体を、break / continue の飛び先を積んだ状態で生成する *)
and in_loop f ~break_to ~continue_to body =
  f.loops <- { break_to; continue_to } :: f.loops;
  Fun.protect ~finally:(fun () -> f.loops <- List.tl f.loops) (fun () -> body ())

and gen_stmt_body g f = function
  | Decl _ -> ()
  | ExprStmt { expr; _ } -> Option.iter (codegen g f) expr
  | Return { expr; _ } ->
      Option.iter (codegen g f) expr;
      emit g ~note:"return: エピローグへ飛ぶ" (Asm.j f.ret_label)
  | Block { stmts; _ } -> List.iter (gen_stmt g f) stmts
  | If { cond; then_; else_; _ } ->
      let label_else = new_label g in
      codegen g f cond;
      emit g
        ~note:
          (if else_ = None then "if: 条件が偽なら then を飛ばす" else "if: 条件が偽なら else へ")
        Asm.(beqz a0 label_else);
      gen_stmt g f then_;
      (match else_ with
      | Some else_stmt ->
          let label_end = new_label g in
          emit g ~note:"if: then を終えたら else を飛ばす" (Asm.j label_end);
          emit g ~note:"if: else の入口" (Asm.deflabel label_else);
          gen_stmt g f else_stmt;
          emit g ~note:"if: then と else の合流点" (Asm.deflabel label_end)
      | None -> emit g ~note:"if: 条件が偽のときの合流点" (Asm.deflabel label_else))
  | While { cond; body; _ } ->
      let label_cond = new_label g in
      let label_end = new_label g in
      in_loop f ~break_to:label_end ~continue_to:label_cond (fun () ->
          emit g ~note:"while: 条件の評価へ戻る先（continue の飛び先）"
            (Asm.deflabel label_cond);
          codegen g f cond;
          emit g ~note:"while: 条件が偽ならループを抜ける" Asm.(beqz a0 label_end);
          gen_stmt g f body;
          emit g ~note:"while: 条件の評価へ戻る" (Asm.j label_cond);
          emit g ~note:"while: ループの出口（break の飛び先）" (Asm.deflabel label_end))
  | For { init; cond; step; body; _ } ->
      let label_cond = new_label g in
      let label_step = new_label g in
      let label_end = new_label g in
      in_loop f ~break_to:label_end ~continue_to:label_step (fun () ->
          Option.iter (codegen g f) init;
          emit g ~note:"for: 条件の評価へ戻る先" (Asm.deflabel label_cond);
          Option.iter
            (fun c ->
              codegen g f c;
              emit g ~note:"for: 条件が偽ならループを抜ける" Asm.(beqz a0 label_end))
            cond;
          gen_stmt g f body;
          emit g ~note:"for: 更新式の入口（continue の飛び先）" (Asm.deflabel label_step);
          Option.iter (codegen g f) step;
          emit g ~note:"for: 条件の評価へ戻る" (Asm.j label_cond);
          emit g ~note:"for: ループの出口（break の飛び先）" (Asm.deflabel label_end))
  | Break { line; _ } ->
      emit g ~note:"break: ループの出口へ" (Asm.j (innermost_loop ~line f).break_to)
  | Continue { line; _ } ->
      emit g ~note:"continue: 更新式・条件へ" (Asm.j (innermost_loop ~line f).continue_to)

(* ── 関数のコード生成 ── *)

let gen_func g = function
  | FuncDef { name; params; body; _ } ->
      (* 関数ごとに状態を作り直すので、前の関数の後片付けは要らない *)
      let f = create_fenv g in
      List.iter (fun (p : param) -> Option.iter (fun n -> alloc_local f n p.ty) p.name) params;
      collect_decls f body;
      let frame_size = align_to f.stack_offset 16 in
      emit g (Asm.globl name);
      emit g
        ~note:(Printf.sprintf "gen_func: %s（フレーム %d バイト）" name (frame_size + 16))
        (Asm.defsym name);
      with_note g "gen_func: プロローグ（ra と s0 を退避して s0 を立てる）" (fun () ->
          emit g Asm.(addi sp sp (-(frame_size + 16)));
          emit g Asm.(store 8 ra (at sp (frame_size + 8)));
          emit g Asm.(store 8 s0 (at sp frame_size));
          emit g Asm.(addi s0 sp (frame_size + 16)));
      with_note g "gen_func: 引数レジスタをスタックへ写す" (fun () ->
          List.iteri
            (fun i (p : param) ->
              match p.name with
              | Some pname when i < 8 -> (
                  match Hashtbl.find_opt f.locals pname with
                  | Some (Local { offset; _ }) -> emit g Asm.(store 8 (arg_reg i) (at s0 offset))
                  | _ -> ())
              | _ -> ())
            params);
      gen_stmt g f body;
      emit g ~note:"gen_func: return の飛び先" (Asm.deflabel f.ret_label);
      with_note g "gen_func: エピローグ（s0 と ra を戻して sp を返す）" (fun () ->
          emit g Asm.(load 8 s0 (at sp frame_size));
          emit g Asm.(load 8 ra (at sp (frame_size + 8)));
          emit g Asm.(addi sp sp (frame_size + 16));
          emit g Asm.ret)
  | FuncProto _ | GlobalDecl _ -> ()

(* ── プログラム全体のビルド ── *)

(* units は (前処理後ソース, そのファイルの宣言列) の並び。
   見出しに元の C を出すので、span の基準になるソースをファイルごとに持ち替える。 *)
let gen_program g units =
  let prog = List.concat_map snd units in
  collect_global_decls g prog;
  List.iter (collect_strings_top g) prog;
  emit_data_section g;
  emit_bss_section g;
  emit g Asm.text;
  List.iter
    (fun (source, decls) ->
      g.source <- source;
      List.iter (gen_func g) decls)
    units
