(*
   コード生成。型付き木（Tast）をなぞって Emitter へアセンブリを流し込む。

   型・変数の置き場・フィールドの変位・ポインタ演算のスケールは Typing が決め終わって
   いるので、ここに残るのは「どの順に命令を出すか」だけである。エラー処理もない
   （生成できない木は Typing を通らない）。

   持ち回る状態は 2 つだけになった。
     genv … プログラム全体（Emitter・型の大きさの表・ラベル連番・いま生成中のソース）
     fenv … 関数 1 個の間だけ（return の飛び先・ループの飛び先・一時値の段数）

   fenv.depth（スタックに積んでいる一時値の個数）だけは Typing に渡せない。
   これは「どの部分式でスタックへ退避したか」という生成の都合そのもので、
   call 直前に sp が 16 バイト境界にあるかどうかの判定に使う。
*)

(* ── 状態 ── *)

(* ループ 1 個ぶんの飛び先。break と continue は必ず対で決まるので 1 本にまとめる *)
type loop = { break_to : Asm.label; continue_to : Asm.label }

type genv = {
  em : Emitter.t;
  layout : Layout.t;
  mutable label_count : int;
  (* 見出しに元の C を切り出すための、いま生成中のファイルの前処理後ソース *)
  mutable source : string;
}

type fenv = { ret_label : Asm.label; mutable depth : int; mutable loops : loop list }

let create_genv em layout = { em; layout; label_count = 0; source = "" }

let new_label g =
  g.label_count <- g.label_count + 1;
  Asm.L g.label_count

let create_fenv g = { ret_label = new_label g; depth = 0; loops = [] }

(* Typing がループの外の break / continue を弾いているので、空になることはない *)
let innermost_loop f = match f.loops with loop :: _ -> loop | [] -> assert false

let size_of g ty = Layout.size_of g.layout ty

(* ── アセンブリへのコメント ──
   どの命令をどの生成関数が出したのかを、出力を読むだけで追えるようにする。
   with_note で「いま生成を担当している場所」を積み、note を明示した行には
   その 1 行だけの説明を付ける。見せ方の規則は Emitter.print 側が決める。 *)

let emit g ?note line = Emitter.emit g.em ?note line
let with_note g note f = Emitter.with_note g.em note f
let heading g text = Emitter.heading g.em text

(* ── 注記の文言 ── *)

let ty_note g ty = Printf.sprintf "%s（%d バイト）" (Ctype.name ty) (size_of g ty)

let binop_name : Ast.binop -> string = function
  | Add -> "Add" | Sub -> "Sub" | Mul -> "Mul" | Div -> "Div" | Mod -> "Mod"
  | Eq -> "Eq" | Ne -> "Ne" | Lt -> "Lt" | Le -> "Le" | And -> "And" | Or -> "Or"

let lval_kind : Tast.lval_desc -> string = function
  | Lvar (Local { name; _ }) | Lvar (Global { name }) -> Printf.sprintf "Var \"%s\"" name
  | Lderef _ -> "Deref"
  | Lfield { field; _ } -> Printf.sprintf "Field \"%s\"" field

let expr_kind : Tast.expr_desc -> string = function
  | Const n -> Printf.sprintf "Const %d" n
  | StrAddr id -> Printf.sprintf "Str .LC%d" id
  | Rval lv -> "Rval " ^ lval_kind lv.l_desc
  | AddrOf lv -> "Addr " ^ lval_kind lv.l_desc
  | Assign _ -> "Assign"
  | IncDec { delta; _ } -> if delta >= 0 then "PreInc" else "PreDec"
  | Cond _ -> "Cond"
  | PtrArith { op = PtrAdd; _ } -> "PtrAdd"
  | PtrArith { op = PtrSub; _ } -> "PtrSub"
  | Binary { op; _ } -> "Binary " ^ binop_name op
  | Unary { op = Neg; _ } -> "Unary Neg"
  | Unary { op = Not; _ } -> "Unary Not"
  | Call { name; _ } -> Printf.sprintf "Call \"%s\"" name

(* 「codegen: Binary Add」のような、生成関数と木のノードの組を作る *)
let expr_note func (e : Tast.expr) = func ^ ": " ^ expr_kind e.e_desc
let lval_note func (lv : Tast.lval) = func ^ ": " ^ lval_kind lv.l_desc

(* ── 文の見出し（元の C を切り出す） ──
   行番号ではなく位置で本文を切り出す。前処理で #include を展開すると
   行番号はずれるが、位置は前処理後ソースへのものなので必ず一致する。 *)

let stmt_kind : Tast.stmt_desc -> string = function
  | Empty -> "Empty" | Expr _ -> "Expr" | Return _ -> "Return"
  | Break -> "Break" | Continue -> "Continue" | If _ -> "If"
  | While _ -> "While" | For _ -> "For" | Block _ -> "Block"

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

let stmt_heading g (s : Tast.stmt) =
  let kind = stmt_kind s.s_desc in
  (* if / while / for は本体まで位置に含むので、丸括弧の中身までで切る *)
  let head_end =
    let end_of (e : Tast.expr) = Some e.e_loc.end_offset in
    match s.s_desc with
    | If { cond; _ } | While { cond; _ } -> end_of cond
    | For { init; cond; step; _ } ->
        List.fold_left
          (fun acc e -> match e with Some e -> end_of e | None -> acc)
          None [ init; cond; step ]
    | _ -> None
  in
  let { Loc.start_offset; end_offset; _ } = s.s_loc in
  let text =
    match head_end with
    | Some stop when stop > start_offset ->
        Option.map (fun t -> condense t 60 ^ ") ...") (source_slice g start_offset stop)
    | _ -> Option.map (fun t -> condense t 60) (source_slice g start_offset end_offset)
  in
  match text with
  | Some t -> Printf.sprintf "%s  [gen_stmt: %s]" t kind
  | None -> Printf.sprintf "[gen_stmt: %s]" kind

(* ── データセクション / BSS セクション出力 ──
   どちらも Typing が決めた並び（文字列は .LC の番号順、グローバルは宣言の出現順）で出す。 *)

let emit_data_section g strings =
  if strings <> [] then emit g Asm.data;
  List.iteri
    (fun i s ->
      emit g (Asm.deflabel (Asm.Lc (i + 1)));
      String.iter (fun ch -> emit g Asm.(byte (Char.code ch))) s;
      emit g (Asm.byte 0))
    strings

(* グローバル変数に初期化子はない。すべて .bss に置かれ 0 に初期化される *)
let emit_bss_section g globals =
  if globals <> [] then emit g Asm.bss;
  List.iter
    (fun (name, ty) ->
      emit g (Asm.globl name);
      emit g (Asm.defsym name);
      emit g Asm.(zero (Layout.slot_size g.layout ty)))
    globals

(* ── コード生成補助 ── *)

let load g ty =
  with_note g (Printf.sprintf "load: a0 のアドレスから%sを読む" (ty_note g ty)) (fun () ->
      emit g Asm.(load (size_of g ty) a0 (at a0 0)))

let store g ty =
  with_note g (Printf.sprintf "store: a1 のアドレスへ%sを書く" (ty_note g ty)) (fun () ->
      emit g Asm.(store (size_of g ty) a0 (at a1 0)))

let scale_index g elem_size =
  if elem_size <> 1 then
    with_note g (Printf.sprintf "scale_index: 添字に要素の大きさ %d を掛ける" elem_size) (fun () ->
        emit g Asm.(li a1 elem_size);
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

(* ── 左辺値のコード生成 ──
   「その左辺値の番地を a0 に置く」までを行う。読み書きは呼んだ側が load / store で足す。

   本体には手を入れず、注記を付けるためのラッパを再帰の輪に足す。
   codegen_lval_body の中の再帰呼び出しはこちらを指すので、
   どの深さの部分式にも自動で担当が付く。 *)

let rec codegen_lval g f (lv : Tast.lval) =
  with_note g (lval_note "codegen_lval" lv) (fun () -> codegen_lval_body g f lv)

and codegen_lval_body g f (lv : Tast.lval) =
  match lv.l_desc with
  | Lvar (Local { offset; _ }) -> emit g Asm.(addi a0 s0 offset)
  | Lvar (Global { name }) -> emit g Asm.(la a0 (Symbol name))
  | Lderef e -> codegen g f e
  | Lfield { base; offset; _ } ->
      codegen_lval g f base;
      if offset <> 0 then emit g Asm.(addi a0 a0 offset)

(* ── 関数呼び出しのコード生成 ── *)

and gen_call g f name args =
  let n = List.length args in
  assert (n <= Layout.max_args);
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

(* ── 式のコード生成 ──
   「その式の値を a0 に置く」までを行う。 *)

and codegen g f (e : Tast.expr) =
  with_note g (expr_note "codegen" e) (fun () -> codegen_body g f e)

and codegen_body g f (e : Tast.expr) =
  match e.e_desc with
  | Const n -> emit g Asm.(li a0 n)
  | StrAddr id -> emit g Asm.(la a0 (Label (Asm.Lc id)))
  | Rval lv ->
      codegen_lval g f lv;
      load g lv.l_ty
  | AddrOf lv -> codegen_lval g f lv
  | Assign { lhs; rhs } ->
      codegen_lval g f lhs;
      push_a0 g f;
      codegen g f rhs;
      pop_into g f Asm.A1;
      store g lhs.l_ty
  | IncDec { lhs; delta } ->
      codegen_lval g f lhs;
      push_a0 g f;
      load g lhs.l_ty;
      emit g Asm.(addi a0 a0 delta);
      pop_into g f Asm.A1;
      store g lhs.l_ty
  | Cond { cond; then_; else_ } ->
      let label_else = new_label g in
      let label_end = new_label g in
      codegen g f cond;
      emit g Asm.(beqz a0 label_else);
      codegen g f then_;
      emit g (Asm.j label_end);
      emit g (Asm.deflabel label_else);
      codegen g f else_;
      emit g (Asm.deflabel label_end)
  | Call { name; args } -> gen_call g f name args
  | Unary { op = Neg; operand } ->
      codegen g f operand;
      emit g Asm.(unop Neg a0 a0)
  | Unary { op = Not; operand } ->
      codegen g f operand;
      emit g Asm.(unop Seqz a0 a0)
  (* ポインタ演算。ptr 側が先に評価される（Typing が左右をこの順に寄せてある） *)
  | PtrArith { op; ptr; index; elem_size } ->
      codegen g f ptr;
      push_a0 g f;
      codegen g f index;
      scale_index g elem_size;
      pop_into g f Asm.A1;
      emit g Asm.(binop (match op with Tast.PtrAdd -> Add | Tast.PtrSub -> Sub) a0 a1 a0)
  | Binary { op; lhs; rhs } -> codegen_binary g f op lhs rhs

(* ── 二項演算 ──
   左を a1、右を a0 に置いてから演算する。 *)

and codegen_binary g f (op : Ast.binop) lhs rhs =
  codegen g f lhs;
  push_a0 g f;
  codegen g f rhs;
  pop_into g f Asm.A1;
  let open Asm in
  match op with
  | Ast.Add -> emit g (binop Add a0 a1 a0)
  | Ast.Sub -> emit g (binop Sub a0 a1 a0)
  | Ast.Mul -> emit g (binop Mul a0 a1 a0)
  | Ast.Div -> emit g (binop Div a0 a1 a0)
  | Ast.Mod -> emit g (binop Rem a0 a1 a0)
  | Ast.Eq ->
      emit g (binop Sub a0 a1 a0);
      emit g (unop Seqz a0 a0)
  | Ast.Ne ->
      emit g (binop Sub a0 a1 a0);
      emit g (unop Snez a0 a0)
  | Ast.Lt -> emit g (binop Slt a0 a1 a0)
  | Ast.Le ->
      emit g (binop Slt a0 a0 a1);
      emit g (xori a0 a0 1)
  | Ast.And ->
      emit g (unop Snez a1 a1);
      emit g (unop Snez a0 a0);
      emit g (binop And a0 a1 a0)
  | Ast.Or ->
      emit g (binop Or a0 a1 a0);
      emit g (unop Snez a0 a0)

(* ── 文のコード生成 ── *)

(* 文ごとに元の C を見出しとして出す。Block は自分では何も出さないので
   見出しも字下げも増やさず、中の文にそれぞれ付ける。 *)
let rec gen_stmt g f (s : Tast.stmt) =
  match s.s_desc with
  | Block _ -> gen_stmt_body g f s.s_desc
  | _ ->
      heading g (stmt_heading g s);
      Emitter.nested g.em (fun () -> gen_stmt_body g f s.s_desc)

(* ループ本体を、break / continue の飛び先を積んだ状態で生成する *)
and in_loop f ~break_to ~continue_to body =
  f.loops <- { break_to; continue_to } :: f.loops;
  Fun.protect ~finally:(fun () -> f.loops <- List.tl f.loops) (fun () -> body ())

and gen_stmt_body g f : Tast.stmt_desc -> unit = function
  | Empty -> ()
  | Expr e -> codegen g f e
  | Return e ->
      Option.iter (codegen g f) e;
      emit g ~note:"return: エピローグへ飛ぶ" (Asm.j f.ret_label)
  | Block stmts -> List.iter (gen_stmt g f) stmts
  | If { cond; then_; else_ } ->
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
  | While { cond; body } ->
      let label_cond = new_label g in
      let label_end = new_label g in
      in_loop f ~break_to:label_end ~continue_to:label_cond (fun () ->
          emit g ~note:"while: 条件の評価へ戻る先（continue の飛び先）" (Asm.deflabel label_cond);
          codegen g f cond;
          emit g ~note:"while: 条件が偽ならループを抜ける" Asm.(beqz a0 label_end);
          gen_stmt g f body;
          emit g ~note:"while: 条件の評価へ戻る" (Asm.j label_cond);
          emit g ~note:"while: ループの出口（break の飛び先）" (Asm.deflabel label_end))
  | For { init; cond; step; body } ->
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
  | Break -> emit g ~note:"break: ループの出口へ" (Asm.j (innermost_loop f).break_to)
  | Continue -> emit g ~note:"continue: 更新式・条件へ" (Asm.j (innermost_loop f).continue_to)

(* ── 関数のコード生成 ── *)

let gen_func g (fn : Tast.func) =
  (* 関数ごとに状態を作り直すので、前の関数の後片付けは要らない *)
  let f = create_fenv g in
  let frame_size = fn.fn_frame_size in
  emit g (Asm.globl fn.fn_name);
  emit g
    ~note:(Printf.sprintf "gen_func: %s（フレーム %d バイト）" fn.fn_name (frame_size + 16))
    (Asm.defsym fn.fn_name);
  with_note g "gen_func: プロローグ（ra と s0 を退避して s0 を立てる）" (fun () ->
      emit g Asm.(addi sp sp (-(frame_size + 16)));
      emit g Asm.(store 8 ra (at sp (frame_size + 8)));
      emit g Asm.(store 8 s0 (at sp frame_size));
      emit g Asm.(addi s0 sp (frame_size + 16)));
  with_note g "gen_func: 引数レジスタをスタックへ写す" (fun () ->
      List.iteri
        (fun i offset ->
          if i < Layout.max_args then emit g Asm.(store 8 (arg_reg i) (at s0 offset)))
        fn.fn_params);
  List.iter (gen_stmt g f) fn.fn_body;
  emit g ~note:"gen_func: return の飛び先" (Asm.deflabel f.ret_label);
  with_note g "gen_func: エピローグ（s0 と ra を戻して sp を返す）" (fun () ->
      emit g Asm.(load 8 s0 (at sp frame_size));
      emit g Asm.(load 8 ra (at sp (frame_size + 8)));
      emit g Asm.(addi sp sp (frame_size + 16));
      emit g Asm.ret)

(* ── プログラム全体のビルド ── *)

let gen_program g (prog : Tast.program) =
  emit_data_section g prog.strings;
  emit_bss_section g prog.globals;
  emit g Asm.text;
  List.iter
    (fun (u : Tast.unit_) ->
      g.source <- u.u_source;
      List.iter (gen_func g) u.u_funcs)
    prog.units
