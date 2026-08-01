(*
   型付けと変数解決。構文木（Ast）から型付き木（Tast）を作る。

   ここで決めるのは次の 4 つである。
   - 式の型（load / store の幅と、ポインタ演算のスケールがこれで決まる）
   - 変数の置き場（局所ならスタックの変位、グローバルならラベル）とフレームの大きさ
   - フィールドの変位、前置 ++ / -- の増減量、ポインタ演算の要素の大きさ
   - エラー。ここを通った木はコード生成できることが保証される

   エラーにするのは次だけである（これ以外は、C として妙な形でも黙って通す。
   たとえば struct 値の代入は 8 バイトの sd 1 個、void * の間接参照は 1 バイトの lb になる）。
   - 未定義の変数
   - 未定義の構造体・フィールド
   - lvalue でない式への代入・アドレス取得
   - ポインタでないものへの * と []
   - -> の対象が構造体ポインタでない、. の対象が構造体でない
   - ループの外の break / continue
   - 引数が 9 個以上の呼び出し
*)

module Env = Map.Make (String)

type binding = { b_ref : Tast.var_ref; b_ty : Ctype.t }
type genv = { layout : Layout.t; globals : binding Env.t; strings : Strings.t }
type fenv = { locals : binding Env.t; in_loop : bool }

let error (loc : Loc.t) fmt = Diag.error ~phase:Diag.Typing ~line:loc.line fmt

let lookup g f name loc =
  match Env.find_opt name f.locals with
  | Some b -> b
  | None -> (
      match Env.find_opt name g.globals with
      | Some b -> b
      | None -> error loc "未定義の変数: '%s'" name)

let field_info g tag field loc =
  match Layout.find g.layout tag with
  | None -> error loc "未定義の構造体: 'struct %s'" tag
  | Some info -> (
      match List.assoc_opt field info.Layout.fields with
      | Some fi -> fi
      | None -> error loc "構造体にフィールド '%s' がありません" field)

(* ポインタ型の要素の大きさ。ptr でない型を渡してはいけない *)
let elem_size g = function
  | Ctype.Ptr elem -> Layout.size_of g.layout elem
  | _ -> assert false

let rec type_expr g f (e : Ast.expr) : Tast.expr =
  let mk desc ty = { Tast.e_desc = desc; e_ty = ty; e_loc = e.e_loc } in
  match e.e_desc with
  | Ast.Num n -> mk (Tast.Const n) Ctype.Int
  | Ast.Sizeof ty -> mk (Tast.Const (Layout.size_of g.layout ty)) Ctype.Int
  | Ast.Str s -> mk (Tast.StrAddr (Strings.id g.strings s)) (Ctype.Ptr Ctype.Char)
  (* 左辺値になれる式は、いったん左辺値として解いてから読み出しに包む *)
  | Ast.Var _ | Ast.Index _ | Ast.Member _ | Ast.Unary { op = Ast.Deref; _ } ->
      let lv = type_lval g f e in
      mk (Tast.Rval lv) lv.l_ty
  | Ast.Unary { op = Ast.Addr; operand } ->
      let lv = type_lval g f operand in
      mk (Tast.AddrOf lv) (Ctype.Ptr lv.l_ty)
  | Ast.Unary { op = (Ast.Neg | Ast.Not) as op; operand } ->
      let op = if op = Ast.Neg then Tast.Neg else Tast.Not in
      mk (Tast.Unary { op; operand = type_expr g f operand }) Ctype.Int
  | Ast.Unary { op = (Ast.PreInc | Ast.PreDec) as op; operand } ->
      let lv = type_lval g f operand in
      (* ポインタなら 1 要素ぶん、それ以外は 1 *)
      let step = match lv.l_ty with Ctype.Ptr _ as t -> elem_size g t | _ -> 1 in
      let delta = if op = Ast.PreInc then step else -step in
      mk (Tast.IncDec { lhs = lv; delta }) lv.l_ty
  | Ast.Assign { lhs; rhs } ->
      let lv = type_lval g f lhs in
      let rhs = type_expr g f rhs in
      mk (Tast.Assign { lhs = lv; rhs }) lv.l_ty
  | Ast.Cond { cond; then_; else_ } ->
      let cond = type_expr g f cond in
      let then_ = type_expr g f then_ in
      let else_ = type_expr g f else_ in
      mk (Tast.Cond { cond; then_; else_ }) then_.e_ty
  | Ast.Call { name; args } ->
      let n = List.length args in
      if n > Layout.max_args then
        error e.e_loc "%s の呼び出し: 引数は %d 個までです（%d 個渡されています）" name
          Layout.max_args n;
      mk (Tast.Call { name; args = List.map (type_expr g f) args }) Ctype.Int
  (* ポインタが絡む + と - はポインタ演算になる。ポインタ側を ptr に寄せるので、
     コード生成は左右を見比べずに「ptr を先に評価する」だけでよい *)
  | Ast.Binary { op = Ast.Add; lhs; rhs } -> (
      let lhs = type_expr g f lhs in
      let rhs = type_expr g f rhs in
      match (lhs.e_ty, rhs.e_ty) with
      | (Ctype.Ptr _ as t), _ ->
          mk (Tast.PtrArith { op = Tast.PtrAdd; ptr = lhs; index = rhs; elem_size = elem_size g t }) t
      | _, (Ctype.Ptr _ as t) ->
          mk (Tast.PtrArith { op = Tast.PtrAdd; ptr = rhs; index = lhs; elem_size = elem_size g t }) t
      | _ -> mk (Tast.Binary { op = Ast.Add; lhs; rhs }) Ctype.Int)
  | Ast.Binary { op = Ast.Sub; lhs; rhs } -> (
      let lhs = type_expr g f lhs in
      let rhs = type_expr g f rhs in
      match lhs.e_ty with
      | Ctype.Ptr _ as t ->
          mk (Tast.PtrArith { op = Tast.PtrSub; ptr = lhs; index = rhs; elem_size = elem_size g t }) t
      | _ -> mk (Tast.Binary { op = Ast.Sub; lhs; rhs }) Ctype.Int)
  | Ast.Binary { op; lhs; rhs } ->
      let lhs = type_expr g f lhs in
      let rhs = type_expr g f rhs in
      mk (Tast.Binary { op; lhs; rhs }) Ctype.Int

and type_lval g f (e : Ast.expr) : Tast.lval =
  match e.e_desc with
  | Ast.Var name ->
      let b = lookup g f name e.e_loc in
      { l_desc = Tast.Lvar b.b_ref; l_ty = b.b_ty }
  | Ast.Unary { op = Ast.Deref; operand } -> (
      let operand = type_expr g f operand in
      match operand.e_ty with
      | Ctype.Ptr base -> { l_desc = Tast.Lderef operand; l_ty = base }
      | _ -> error e.e_loc "* の対象がポインタではありません")
  (* a[i] は *(a + i) と同じ。番地の作り方はポインタ加算そのもの *)
  | Ast.Index { base; index } -> (
      let base = type_expr g f base in
      let index = type_expr g f index in
      match base.e_ty with
      | Ctype.Ptr elem as t ->
          let addr =
            {
              Tast.e_desc =
                Tast.PtrArith { op = Tast.PtrAdd; ptr = base; index; elem_size = elem_size g t };
              e_ty = t;
              e_loc = e.e_loc;
            }
          in
          { l_desc = Tast.Lderef addr; l_ty = elem }
      | _ -> error e.e_loc "[] の対象がポインタではありません")
  (* p->x は「p を間接参照した入れ物の x」へ均す。
     残る違いは「-> はポインタの値、. は入れ物の番地が要る」だけになる *)
  | Ast.Member { base; field; arrow } ->
      let base_lval =
        if arrow then (
          let base = type_expr g f base in
          match base.e_ty with
          | Ctype.Ptr (Ctype.Struct _ as s) -> { Tast.l_desc = Tast.Lderef base; l_ty = s }
          | _ -> error e.e_loc "-> の対象が構造体ポインタではありません")
        else
          let base = type_lval g f base in
          match base.l_ty with
          | Ctype.Struct _ -> base
          | _ -> error e.e_loc ". の対象が構造体ではありません"
      in
      let tag = match base_lval.l_ty with Ctype.Struct tag -> tag | _ -> assert false in
      let fi = field_info g tag field e.e_loc in
      { l_desc = Tast.Lfield { base = base_lval; field; offset = fi.Layout.offset }; l_ty = fi.Layout.ty }
  | _ -> error e.e_loc "lvalue でない式です"

let rec type_stmt g f (s : Ast.stmt) : Tast.stmt =
  let mk desc = { Tast.s_desc = desc; s_loc = s.s_loc } in
  let expr = type_expr g f in
  match s.s_desc with
  | Ast.Empty -> mk Tast.Empty
  | Ast.Expr e -> mk (Tast.Expr (expr e))
  | Ast.Return e -> mk (Tast.Return (Option.map expr e))
  | Ast.Break ->
      if not f.in_loop then error s.s_loc "ループの外にいます";
      mk Tast.Break
  | Ast.Continue ->
      if not f.in_loop then error s.s_loc "ループの外にいます";
      mk Tast.Continue
  | Ast.Block stmts -> mk (Tast.Block (List.map (type_stmt g f) stmts))
  | Ast.If { cond; then_; else_ } ->
      mk
        (Tast.If
           {
             cond = expr cond;
             then_ = type_stmt g f then_;
             else_ = Option.map (type_stmt g f) else_;
           })
  | Ast.While { cond; body } ->
      mk (Tast.While { cond = expr cond; body = type_stmt g { f with in_loop = true } body })
  | Ast.For { init; cond; step; body } ->
      mk
        (Tast.For
           {
             init = Option.map expr init;
             cond = Option.map expr cond;
             step = Option.map expr step;
             body = type_stmt g { f with in_loop = true } body;
           })

(* ── 関数 1 個 ── *)

let type_func g (fn : Ast.func) : Tast.func =
  (* 仮引数を宣言順に、続けて局所宣言を宣言順にスタックへ積む。
     同じ名前を 2 度宣言したら場所は 2 つ取り、名前は後の宣言を指す *)
  let add_slot (env, stack) name ty =
    let stack = stack + Layout.slot_size g.layout ty in
    (Env.add name { b_ref = Tast.Local { name; offset = -(16 + stack) }; b_ty = ty } env, stack)
  in
  let env, stack =
    List.fold_left
      (fun acc (p : Ast.param) -> add_slot acc p.p_name p.p_ty)
      (Env.empty, 0) fn.fn_params
  in
  let env, stack =
    List.fold_left (fun acc (d : Ast.decl) -> add_slot acc d.d_name d.d_ty) (env, stack) fn.fn_locals
  in
  (* 引数レジスタから写す先。名前が後の宣言に隠されていれば、そちらの場所へ写す *)
  let param_offsets =
    List.map
      (fun (p : Ast.param) ->
        match Env.find_opt p.p_name env with
        | Some { b_ref = Tast.Local { offset; _ }; _ } -> offset
        | _ -> assert false)
      fn.fn_params
  in
  {
    Tast.fn_name = fn.fn_name;
    fn_params = param_offsets;
    fn_frame_size = Layout.frame_size stack;
    fn_body = List.map (type_stmt g { locals = env; in_loop = false }) fn.fn_body;
  }

(* ── プログラム全体 ── *)

(* struct のレイアウトは、並んだ順に畳み込む（入れ子はその時点の表で解決する） *)
let build_layout programs =
  List.fold_left
    (fun t (p : Ast.program) ->
      List.fold_left
        (fun t (sd : Ast.struct_def) -> Layout.add t ~tag:sd.sd_tag ~fields:sd.sd_fields)
        t p.structs)
    Layout.empty programs

(* グローバル変数は出現順に集める。同じ名前を 2 度宣言したら型は後勝ち *)
let collect_globals programs =
  let step (order, tys) = function
    | Ast.Global (d : Ast.decl) ->
        let order = if List.mem d.d_name order then order else order @ [ d.d_name ] in
        (order, Env.add d.d_name d.d_ty tys)
    | Ast.Func _ | Ast.Proto _ -> (order, tys)
  in
  let order, tys =
    List.fold_left
      (fun acc (p : Ast.program) -> List.fold_left step acc p.tops)
      ([], Env.empty) programs
  in
  List.map (fun name -> (name, Env.find name tys)) order

(* units は (前処理後ソース, そのファイルの構文木) の並び。
   struct の表・グローバル変数・文字列リテラルはプログラム全体で共有し、
   関数の生成だけをファイル単位に分けて持つ（見出しに元の C を出すため）。 *)
let type_program (units : (string * Ast.program) list) : Tast.program =
  let programs = List.map snd units in
  let globals = collect_globals programs in
  let layout = build_layout programs in
  let g =
    {
      layout;
      globals =
        List.fold_left
          (fun env (name, ty) ->
            Env.add name { b_ref = Tast.Global { name }; b_ty = ty } env)
          Env.empty globals;
      strings = Strings.collect programs;
    }
  in
  {
    Tast.layout;
    strings = Strings.contents g.strings;
    globals;
    units =
      List.map
        (fun (source, (p : Ast.program)) ->
          {
            Tast.u_source = source;
            u_funcs =
              List.filter_map
                (function Ast.Func fn -> Some (type_func g fn) | Ast.Proto _ | Ast.Global _ -> None)
                p.tops;
          })
        units;
  }
