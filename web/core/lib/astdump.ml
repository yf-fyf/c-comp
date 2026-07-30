(*
   AST 直列化 — parse_viewer.py と同一の S 式 / DOT / JSON を出力する。

   正は Python 版（workbook/scaffold/parse_viewer.py）である（design/webapps.md 4章）。
   OCaml の AST（ADT）を Python の平坦な Node に相当する中間表現 pnode へ一点変換し、
   3つのレンダラは parse_viewer.py の逐語移植とする。Web用JSONだけは
   sourceRanges を追加する。表現差の吸収はすべて
   of_expr / of_stmt / of_top に集め、レンダラ側には判断を持ち込まない。
*)

open Ast_def

(* ── Python の Node に相当する中間表現 ── *)

type pnode = {
  kind : string;
  lhs : pnode option;
  rhs : pnode option;
  cond : pnode option;
  then_ : pnode option;
  else_ : pnode option;
  init : pnode option;
  step : pnode option;
  body : pnode option;
  operand : pnode option;
  stmts : pnode list;
  args : pnode list;
  params : pnode list;
  pval : int option;        (* Num のみ *)
  sval : string option;     (* Str のみ *)
  name : string;            (* '' = なし *)
  pty : ty option;          (* Python の ty_str に相当 *)
  is_arrow : bool option;   (* Member のみ *)
  line : int;               (* 0 = なし（Python 版がトップレベルと param に行を付けない） *)
  span : source_span option; (* 前処理後ソース上のバイト範囲。JSON UI用 *)
}

let empty =
  { kind = ""; lhs = None; rhs = None; cond = None; then_ = None; else_ = None;
    init = None; step = None; body = None; operand = None;
    stmts = []; args = []; params = []; pval = None; sval = None; name = "";
    pty = None; is_arrow = None; line = 0; span = None }

let binop_kind = function
  | Add -> "Add" | Sub -> "Sub" | Mul -> "Mul" | Div -> "Div" | Mod -> "Mod"
  | Eq -> "Eq" | Ne -> "Ne" | Lt -> "Lt" | Le -> "Le"
  | And -> "And" | Or -> "Or"

let unop_kind = function
  | Neg -> "Neg" | Not -> "Not"
  | Addr -> "Addr" | Deref -> "Deref"
  | PreInc -> "PreInc" | PreDec -> "PreDec"

let rec of_expr (e : expr) : pnode =
  match e with
  | Num { value; line; span } -> { empty with kind = "Num"; pval = Some value; line; span }
  | StrLit { value; line; span } -> { empty with kind = "Str"; sval = Some value; line; span }
  | Var { name; line; span } -> { empty with kind = "Var"; name; line; span }
  | Assign { lhs; rhs; line; span } ->
      { empty with kind = "Assign"; lhs = Some (of_expr lhs); rhs = Some (of_expr rhs); line; span }
  | Cond { cond; then_; else_; line; span } ->
      { empty with kind = "Cond"; cond = Some (of_expr cond);
        then_ = Some (of_expr then_); else_ = Some (of_expr else_); line; span }
  | Binary { op; lhs; rhs; line; span } ->
      { empty with kind = binop_kind op;
        lhs = Some (of_expr lhs); rhs = Some (of_expr rhs); line; span }
  | Unary { op; operand; line; span } ->
      { empty with kind = unop_kind op; operand = Some (of_expr operand); line; span }
  | Index { base; index; line; span } ->
      (* Python 版は Index を lhs / rhs に格納する *)
      { empty with kind = "Index"; lhs = Some (of_expr base); rhs = Some (of_expr index); line; span }
  | Member { base; name; is_arrow; line; span } ->
      { empty with kind = "Member"; operand = Some (of_expr base); name;
        is_arrow = Some is_arrow; line; span }
  | SizeofType { ty; line; span } -> { empty with kind = "SizeofType"; pty = Some ty; line; span }
  | Call { name; args; line; span } ->
      { empty with kind = "Call"; name; args = List.map of_expr args; line; span }

let of_decl ?(line_override = None) (d : decl) : pnode =
  let line = match line_override with Some l -> l | None -> d.line in
  { empty with kind = "Decl"; name = d.name; pty = Some d.ty; line; span = d.span }

let rec of_stmt (s : stmt) : pnode =
  match s with
  | Block { stmts; line; span } -> { empty with kind = "Block"; stmts = List.map of_stmt stmts; line; span }
  | ExprStmt { expr; line; span } ->
      { empty with kind = "ExprStmt"; operand = Option.map of_expr expr; line; span }
  | Return { expr; line; span } ->
      { empty with kind = "Return"; operand = Option.map of_expr expr; line; span }
  | Break { line; span } -> { empty with kind = "Break"; line; span }
  | Continue { line; span } -> { empty with kind = "Continue"; line; span }
  | If { cond; then_; else_; line; span } ->
      { empty with kind = "If"; cond = Some (of_expr cond); then_ = Some (of_stmt then_);
        else_ = Option.map of_stmt else_; line; span }
  | While { cond; body; line; span } ->
      { empty with kind = "While"; cond = Some (of_expr cond); body = Some (of_stmt body); line; span }
  | For { init; cond; step; body; line; span } ->
      { empty with kind = "For"; init = Option.map of_expr init;
        cond = Option.map of_expr cond; step = Option.map of_expr step;
        body = Some (of_stmt body); line; span }
  | Decl d -> of_decl d

(* Python 版の param は行番号なしの Decl ノード *)
let of_param (p : param) : pnode =
  { empty with kind = "Decl"; name = Option.value p.name ~default:""; pty = Some p.ty;
    span = p.span }

(* Python 版はトップレベルノードに行番号を付けない。同じ木にするため line = 0 とする
   （struct 宣言は構文解析の段階で AST に出ない）。 *)
let of_top (t : top) : pnode =
  match t with
  | FuncDef { name; ty; params; body; span; _ } ->
      { empty with kind = "FuncDef"; name; pty = Some ty;
        params = List.map of_param params; body = Some (of_stmt body); span }
  | FuncProto { name; ty; params; span; _ } ->
      { empty with kind = "FuncProto"; name; pty = Some ty;
        params = List.map of_param params; span }
  | GlobalDecl d -> of_decl ~line_override:(Some 0) d

let of_program (prog : program) : pnode list = List.map of_top prog

(* ── S 式（parse_viewer.py の Sym / render_sexp の移植） ── *)

type sexp =
  | SSym of string    (* 裸のシンボル *)
  | SStr of string    (* 引用符付き文字列 *)
  | SInt of int
  | SList of sexp list

(* Python json.dumps(ensure_ascii=False) と同じエスケープ *)
let quote_string s =
  let buf = Buffer.create (String.length s + 2) in
  Buffer.add_char buf '"';
  String.iter
    (fun c ->
      match c with
      | '"' -> Buffer.add_string buf "\\\""
      | '\\' -> Buffer.add_string buf "\\\\"
      | '\n' -> Buffer.add_string buf "\\n"
      | '\r' -> Buffer.add_string buf "\\r"
      | '\t' -> Buffer.add_string buf "\\t"
      | '\b' -> Buffer.add_string buf "\\b"
      | '\012' -> Buffer.add_string buf "\\f"
      | c when Char.code c < 0x20 ->
          Buffer.add_string buf (Printf.sprintf "\\u%04x" (Char.code c))
      | c -> Buffer.add_char buf c)
    s;
  Buffer.add_char buf '"';
  Buffer.contents buf

let render_atom = function
  | SSym s -> s
  | SStr s -> quote_string s
  | SInt n -> string_of_int n
  | SList _ -> invalid_arg "render_atom"

let is_list = function SList _ -> true | _ -> false

let is_flat = function
  | SList items -> List.for_all (fun i -> not (is_list i)) items
  | _ -> true

let lstrip s =
  let n = String.length s in
  let i = ref 0 in
  while !i < n && (s.[!i] = ' ' || s.[!i] = '\t') do incr i done;
  String.sub s !i (n - !i)

let rec render_sexp ?(indent = 0) (expr : sexp) : string =
  match expr with
  | SSym _ | SStr _ | SInt _ -> render_atom expr
  | SList [] -> "()"
  | SList items when is_flat expr ->
      "(" ^ String.concat " " (List.map render_atom items) ^ ")"
  | SList items -> (
      (* 最初の「平坦でないリスト」より前を先頭行に、それ以降を1項目1行にする *)
      let rec split prefix = function
        | item :: _ as rest when is_list item && not (is_flat item) ->
            Some (List.rev prefix, rest)
        | item :: tl -> split (item :: prefix) tl
        | [] -> None
      in
      match split [] items with
      | None -> "(" ^ String.concat " " (List.map (render_sexp ~indent:0) items) ^ ")"
      | Some (prefix, rest) ->
          let pad = String.make indent ' ' in
          let child_pad = String.make (indent + 2) ' ' in
          let first =
            pad ^ "(" ^ String.concat " " (List.map (render_sexp ~indent:0) prefix)
          in
          let children =
            List.map
              (fun item -> child_pad ^ lstrip (render_sexp ~indent:(indent + 2) item))
              rest
          in
          String.concat "\n" (first :: children) ^ ")")

let starts_with_s prefix s =
  String.length s >= String.length prefix
  && String.sub s 0 (String.length prefix) = prefix

(* Python format_type(ty_str) と同じ構造の S 式を、構造化された ty から作る *)
let rec type_sexp (ty : ty) : sexp =
  match ty with
  | TyInt -> SSym "int"
  | TyChar -> SSym "char"
  | TyVoid -> SSym "void"
  | TyPtr t -> SList [ SSym "ptr"; type_sexp t ]
  | TyStruct tag -> SList [ SSym "struct"; SStr tag ]

(* Python の ty_str 文字列表現（JSON 表示用。バイト一致の対象外） *)
let rec ty_str_of (ty : ty) : string =
  match ty with
  | TyInt -> "int"
  | TyChar -> "char"
  | TyVoid -> "void"
  | TyPtr t -> ty_str_of t ^ "*"
  | TyStruct tag -> "struct " ^ tag

let binary_sexp_name = function
  | "Add" -> Some "add" | "Sub" -> Some "sub" | "Mul" -> Some "mul"
  | "Div" -> Some "div" | "Mod" -> Some "mod"
  | "Eq" -> Some "eq" | "Ne" -> Some "ne" | "Lt" -> Some "lt" | "Le" -> Some "le"
  | "And" -> Some "and" | "Or" -> Some "or"
  | _ -> None

let unary_sexp_name = function
  | "Neg" -> Some "neg" | "Not" -> Some "not"
  | "Addr" -> Some "addr" | "Deref" -> Some "deref"
  | "PreInc" -> Some "preinc" | "PreDec" -> Some "predec"
  | _ -> None

let line_attr (n : pnode) show_line =
  if show_line && n.line <> 0 then [ SSym ":line"; SInt n.line ] else []

let type_attr (n : pnode) =
  match n.pty with Some ty -> [ SSym ":type"; type_sexp ty ] | None -> []

let param_to_sexp (n : pnode) show_line =
  let name = if n.name <> "" then [ SStr n.name ] else [] in
  SList ((SSym "param" :: name) @ type_attr n @ line_attr n show_line)

let rec node_to_sexp ?(show_line = false) (n : pnode) : sexp =
  let sub x = node_to_sexp ~show_line x in
  let la = line_attr n show_line in
  match n.kind with
  | "Num" -> SList ((SSym "num" :: SInt (Option.get n.pval) :: []) @ la)
  | "Str" -> SList ((SSym "str" :: SStr (Option.get n.sval) :: []) @ la)
  | "Var" -> SList ((SSym "var" :: SStr n.name :: []) @ la)
  | "Call" ->
      SList
        ([ SSym "call"; SStr n.name ] @ la
        @ [ SList (SSym "args" :: List.map sub n.args) ])
  | "Assign" ->
      SList ([ SSym "assign" ] @ la @ [ sub (Option.get n.lhs); sub (Option.get n.rhs) ])
  | "Cond" ->
      SList
        ([ SSym "ternary" ] @ la
        @ [ sub (Option.get n.cond); sub (Option.get n.then_); sub (Option.get n.else_) ])
  | k when binary_sexp_name k <> None ->
      SList
        ([ SSym (Option.get (binary_sexp_name k)) ] @ la
        @ [ sub (Option.get n.lhs); sub (Option.get n.rhs) ])
  | k when unary_sexp_name k <> None ->
      SList ([ SSym (Option.get (unary_sexp_name k)) ] @ la @ [ sub (Option.get n.operand) ])
  | "Index" ->
      SList ([ SSym "index" ] @ la @ [ sub (Option.get n.lhs); sub (Option.get n.rhs) ])
  | "Member" ->
      let op = if n.is_arrow = Some true then "->" else "." in
      SList
        ([ SSym "member"; SStr op; SStr n.name ] @ la @ [ sub (Option.get n.operand) ])
  | "SizeofType" -> SList ([ SSym "sizeof-type"; type_sexp (Option.get n.pty) ] @ la)
  | "Block" -> SList ([ SSym "block" ] @ la @ List.map sub n.stmts)
  | "ExprStmt" ->
      SList ([ SSym "exprstmt" ] @ la @ Option.to_list (Option.map sub n.operand))
  | "Return" ->
      SList ([ SSym "return" ] @ la @ Option.to_list (Option.map sub n.operand))
  | "Break" -> SList ([ SSym "break" ] @ la)
  | "Continue" -> SList ([ SSym "continue" ] @ la)
  | "If" ->
      let base =
        [ SSym "if" ] @ la
        @ [ SList [ SSym "cond"; sub (Option.get n.cond) ];
            SList [ SSym "then"; sub (Option.get n.then_) ] ]
      in
      let els =
        match n.else_ with
        | Some e -> [ SList [ SSym "else"; sub e ] ]
        | None -> []
      in
      SList (base @ els)
  | "While" ->
      SList
        ([ SSym "while" ] @ la
        @ [ SList [ SSym "cond"; sub (Option.get n.cond) ];
            SList [ SSym "body"; sub (Option.get n.body) ] ])
  | "For" ->
      let slot name v =
        SList [ SSym name; (match v with Some e -> sub e | None -> SSym "none") ]
      in
      SList
        ([ SSym "for" ] @ la
        @ [ slot "init" n.init; slot "cond" n.cond; slot "step" n.step;
            SList [ SSym "body"; sub (Option.get n.body) ] ])
  | "Decl" -> SList ([ SSym "decl"; SStr n.name ] @ type_attr n @ la)
  | "FuncDef" ->
      SList
        ([ SSym "funcdef"; SStr n.name ] @ type_attr n @ la
        @ [ SList (SSym "params" :: List.map (fun p -> param_to_sexp p show_line) n.params);
            sub (Option.get n.body) ])
  | "FuncProto" ->
      SList
        ([ SSym "funcproto"; SStr n.name ] @ type_attr n @ la
        @ [ SList (SSym "params" :: List.map (fun p -> param_to_sexp p show_line) n.params) ])
  | k -> SList ([ SSym "unknown"; SStr k ] @ la)

let program_sexp ?(show_line = false) (prog : program) : string =
  let tops = of_program prog in
  render_sexp (SList (SSym "program" :: List.map (node_to_sexp ~show_line) tops))

(* ── DOT（parse_viewer.py の render_dot の移植） ── *)

let node_to_dot_label (n : pnode) show_line =
  let parts = ref [ n.kind ] in
  let add s = parts := !parts @ [ s ] in
  if n.name <> "" then add (quote_string n.name);
  (match (n.kind, n.pval) with "Num", Some v -> add (string_of_int v) | _ -> ());
  (match (n.kind, n.sval) with "Str", Some s -> add (quote_string s) | _ -> ());
  (match (n.kind, n.is_arrow) with
  | "Member", Some arrow -> add (if arrow then "->" else ".")
  | _ -> ());
  (match n.pty with Some ty -> add (":type " ^ render_sexp (type_sexp ty)) | None -> ());
  if show_line && n.line <> 0 then add (Printf.sprintf "line %d" n.line);
  String.concat "\n" !parts

let program_dot ?(show_line = false) (prog : program) : string =
  let tops = of_program prog in
  let buf = Buffer.create 4096 in
  let emit s = Buffer.add_string buf s; Buffer.add_char buf '\n' in
  let counter = ref 1 in
  let fresh () = let c = !counter in incr counter; c in
  Buffer.add_string buf "digraph AST {\n";
  emit "  graph [rankdir=TB];";
  emit "  node [shape=box, fontname=\"monospace\"];";
  emit "  edge [fontname=\"monospace\"];";
  emit "";
  let root_id = fresh () in
  emit (Printf.sprintf "  n%d [label=%s];" root_id (quote_string "Program"));
  let rec walk parent_id edge_label (n : pnode) child_index =
    let nid = fresh () in
    emit (Printf.sprintf "  n%d [label=%s];" nid (quote_string (node_to_dot_label n show_line)));
    let suffix = if child_index >= 0 then Printf.sprintf "[%d]" child_index else "" in
    emit (Printf.sprintf "  n%d -> n%d [label=%s];" parent_id nid (quote_string (edge_label ^ suffix)));
    (* Python の Node の dataclass フィールド順と同じ順で子を辿る *)
    List.iter
      (fun (fname, fval) ->
        match fval with Some child -> walk nid fname child (-1) | None -> ())
      [ ("lhs", n.lhs); ("rhs", n.rhs); ("cond", n.cond); ("then", n.then_);
        ("else", n.else_); ("init", n.init); ("step", n.step); ("body", n.body);
        ("operand", n.operand) ];
    List.iter
      (fun (fname, children) ->
        List.iteri (fun i child -> walk nid fname child i) children)
      [ ("stmts", n.stmts); ("args", n.args); ("params", n.params) ]
  in
  List.iteri (fun i n -> walk root_id "top" n i) tops;
  emit "";
  Buffer.add_string buf "}";
  Buffer.contents buf

(* ── JSON（アプリ用。AST本体はnode_to_dict準拠。sourceRangesはWeb固有） ── *)

type json =
  | JStr of string
  | JInt of int
  | JBool of bool
  | JList of json list
  | JObj of (string * json) list

let rec json_to_buf buf indent (j : json) =
  let pad n = String.make n ' ' in
  match j with
  | JStr s -> Buffer.add_string buf (quote_string s)
  | JInt n -> Buffer.add_string buf (string_of_int n)
  | JBool b -> Buffer.add_string buf (if b then "true" else "false")
  | JList [] -> Buffer.add_string buf "[]"
  | JList items ->
      Buffer.add_string buf "[\n";
      List.iteri
        (fun i item ->
          if i > 0 then Buffer.add_string buf ",\n";
          Buffer.add_string buf (pad (indent + 2));
          json_to_buf buf (indent + 2) item)
        items;
      Buffer.add_string buf ("\n" ^ pad indent ^ "]")
  | JObj [] -> Buffer.add_string buf "{}"
  | JObj fields ->
      Buffer.add_string buf "{\n";
      List.iteri
        (fun i (k, v) ->
          if i > 0 then Buffer.add_string buf ",\n";
          Buffer.add_string buf (pad (indent + 2) ^ quote_string k ^ ": ");
          json_to_buf buf (indent + 2) v)
        fields;
      Buffer.add_string buf ("\n" ^ pad indent ^ "}")

let json_to_string (j : json) : string =
  let buf = Buffer.create 4096 in
  json_to_buf buf 0 j;
  Buffer.contents buf

let rec node_to_json ?(show_line = true) ?(map_span = fun _ -> []) (n : pnode) : json =
  let sub x = node_to_json ~show_line ~map_span x in
  let opt name v = match v with Some x -> [ (name, sub x) ] | None -> [] in
  let lst name v = match v with [] -> [] | xs -> [ (name, JList (List.map sub xs)) ] in
  let fields =
    [ ("kind", JStr n.kind) ]
    @ opt "lhs" n.lhs @ opt "rhs" n.rhs @ opt "cond" n.cond @ opt "then" n.then_
    @ opt "else_" n.else_ @ opt "init" n.init @ opt "step" n.step @ opt "body" n.body
    @ opt "operand" n.operand
    @ lst "stmts" n.stmts @ lst "args" n.args @ lst "params" n.params
    @ (match (n.kind, n.pval) with "Num", Some v -> [ ("val", JInt v) ] | _ -> [])
    @ (match n.sval with Some s when s <> "" -> [ ("sval", JStr s) ] | _ -> [])
    @ (if n.name <> "" then [ ("name", JStr n.name) ] else [])
    @ (match n.pty with
      | Some ty ->
          [ ("ty_str", JStr (ty_str_of ty));
            ("type_sexp", JStr (render_sexp (type_sexp ty))) ]
      | None -> [])
    @ (match (n.kind, n.is_arrow) with
      | "Member", Some b -> [ ("is_arrow", JBool b) ]
      | _ -> [])
    @ (if show_line && n.line <> 0 then [ ("line", JInt n.line) ] else [])
    @ (match map_span n.span with
      | [] -> []
      | ranges ->
          [ ("sourceRanges",
              JList
                (List.map
                   (fun (from_pos, to_pos) ->
                     JObj [ ("from", JInt from_pos); ("to", JInt to_pos) ])
                   ranges)) ])
  in
  JObj fields

let program_json ?(map_span = fun _ -> []) (prog : program) : json =
  JList (List.map (node_to_json ~show_line:true ~map_span) (of_program prog))

(* 前処理後バイト範囲を、直接コピーされた主ソースのUTF-16範囲へ写す。
   macro展開とinclude由来の未対応区間は返さない。 *)
let source_range_mapper source (segments : Preprocess.map_segment list) =
  let byte_len = String.length source in
  let utf16 = Array.make (byte_len + 1) 0 in
  let rec fill i units =
    if i >= byte_len then utf16.(byte_len) <- units
    else
      let first = Char.code source.[i] in
      let width, unit_width =
        if first land 0x80 = 0 then (1, 1)
        else if first land 0xe0 = 0xc0 then (2, 1)
        else if first land 0xf0 = 0xe0 then (3, 1)
        else if first land 0xf8 = 0xf0 then (4, 2)
        else (1, 1)
      in
      let width = min width (byte_len - i) in
      for j = i to i + width - 1 do utf16.(j) <- units done;
      fill (i + width) (units + unit_width)
  in
  fill 0 0;
  let merge ranges =
    List.fold_left
      (fun acc (from_pos, to_pos) ->
        match acc with
        | (prev_from, prev_to) :: rest when prev_to = from_pos ->
            (prev_from, to_pos) :: rest
        | _ -> (from_pos, to_pos) :: acc)
      [] ranges
    |> List.rev
  in
  function
  | None -> []
  | Some span ->
      segments
      |> List.filter_map (fun (segment : Preprocess.map_segment) ->
             let first = max span.start_offset segment.generated_start in
             let last = min span.end_offset segment.generated_end in
             if first >= last then None
             else
               let source_first = segment.source_start + (first - segment.generated_start) in
               let source_last = segment.source_start + (last - segment.generated_start) in
               Some (utf16.(source_first), utf16.(source_last)))
      |> merge

(* ── トークン列（Python の tokenize / TK_* と同じ分類） ── *)

let token_info (t : Parser.token) : string * string * int option =
  match t with
  | Parser.NUM n -> ("TK_NUM", string_of_int n, Some n)
  | Parser.CHAR_LIT n -> ("TK_CHAR", string_of_int n, Some n)
  | Parser.STR s -> ("TK_STR", s, None)
  | Parser.IDENT s -> ("TK_IDENT", s, None)
  | Parser.KW_INT -> ("TK_KW", "int", None)
  | Parser.KW_CHAR -> ("TK_KW", "char", None)
  | Parser.KW_VOID -> ("TK_KW", "void", None)
  | Parser.KW_STRUCT -> ("TK_KW", "struct", None)
  | Parser.IF -> ("TK_KW", "if", None)
  | Parser.ELSE -> ("TK_KW", "else", None)
  | Parser.WHILE -> ("TK_KW", "while", None)
  | Parser.FOR -> ("TK_KW", "for", None)
  | Parser.RETURN -> ("TK_KW", "return", None)
  | Parser.BREAK -> ("TK_KW", "break", None)
  | Parser.CONTINUE -> ("TK_KW", "continue", None)
  | Parser.SIZEOF -> ("TK_KW", "sizeof", None)
  | Parser.ELLIPSIS -> ("TK_PUNCT", "...", None)
  | Parser.EQEQ -> ("TK_PUNCT", "==", None)
  | Parser.NE -> ("TK_PUNCT", "!=", None)
  | Parser.LE -> ("TK_PUNCT", "<=", None)
  | Parser.GE -> ("TK_PUNCT", ">=", None)
  | Parser.ANDAND -> ("TK_PUNCT", "&&", None)
  | Parser.OROR -> ("TK_PUNCT", "||", None)
  | Parser.ARROW -> ("TK_PUNCT", "->", None)
  | Parser.PLUSPLUS -> ("TK_PUNCT", "++", None)
  | Parser.MINUSMINUS -> ("TK_PUNCT", "--", None)
  | Parser.PLUS -> ("TK_PUNCT", "+", None)
  | Parser.MINUS -> ("TK_PUNCT", "-", None)
  | Parser.STAR -> ("TK_PUNCT", "*", None)
  | Parser.SLASH -> ("TK_PUNCT", "/", None)
  | Parser.PERCENT -> ("TK_PUNCT", "%", None)
  | Parser.AMP -> ("TK_PUNCT", "&", None)
  | Parser.BANG -> ("TK_PUNCT", "!", None)
  | Parser.LT -> ("TK_PUNCT", "<", None)
  | Parser.GT -> ("TK_PUNCT", ">", None)
  | Parser.ASSIGN -> ("TK_PUNCT", "=", None)
  | Parser.QUESTION -> ("TK_PUNCT", "?", None)
  | Parser.COLON -> ("TK_PUNCT", ":", None)
  | Parser.SEMI -> ("TK_PUNCT", ";", None)
  | Parser.COMMA -> ("TK_PUNCT", ",", None)
  | Parser.DOT -> ("TK_PUNCT", ".", None)
  | Parser.LPAREN -> ("TK_PUNCT", "(", None)
  | Parser.RPAREN -> ("TK_PUNCT", ")", None)
  | Parser.LBRACE -> ("TK_PUNCT", "{", None)
  | Parser.RBRACE -> ("TK_PUNCT", "}", None)
  | Parser.LBRACKET -> ("TK_PUNCT", "[", None)
  | Parser.RBRACKET -> ("TK_PUNCT", "]", None)
  | Parser.EOF -> ("TK_EOF", "<eof>", None)

(* 前処理済みソースをトークン列にする（Lexer を単独駆動） *)
let tokens_json ~filename (preprocessed : string) : json =
  let lexbuf = Frontend.init_lexbuf filename preprocessed in
  let rec loop acc =
    let tok = Lexer.token lexbuf in
    let line = lexbuf.Lexing.lex_start_p.Lexing.pos_lnum in
    let kind, text, v = token_info tok in
    let fields =
      [ ("kind", JStr kind); ("text", JStr text) ]
      @ (match v with Some n -> [ ("val", JInt n) ] | None -> [])
      @ [ ("line", JInt line) ]
    in
    let acc = JObj fields :: acc in
    match tok with Parser.EOF -> List.rev acc | _ -> loop acc
  in
  JList (loop [])

(* ── 前処理の行対応表 ──
   support/preprocess.ml と同じ判断（#include の展開・#define 行の削除）を
   数え上げだけ再現し、前処理後の行番号 → 元ソースの行番号の表を作る。
   AST の行番号は前処理後のテキスト基準なので、エディタのハイライトに必要。 *)

let include_re = Str.regexp "^#include[ \t]+\"\\([^\"]+\\)\""

let find_include dirs fname =
  List.find_map
    (fun d ->
      let p = Filename.concat d fname in
      if Sys.file_exists p then Some p else None)
    dirs

(* ファイルが前処理後に占める行数 *)
let rec contrib_lines source dirs =
  List.fold_left
    (fun acc line ->
      let stripped = String.trim line in
      if starts_with_s "#include" stripped then
        if Str.string_match include_re stripped 0 then
          match find_include dirs (Str.matched_group 1 stripped) with
          | Some path -> acc + contrib_lines (Utils.read_file path) dirs
          | None -> acc
        else acc
      else if starts_with_s "#define" stripped then acc
      else acc + 1)
    0
    (String.split_on_char '\n' source)

(* [(前処理後の行, 元の行); ...]（主ファイルの行のみ。include 展開部は対象外） *)
let build_line_map source dirs : (int * int) list =
  let lines = String.split_on_char '\n' source in
  let _, acc =
    List.fold_left
      (fun (pp, acc) (lineno, line) ->
        let stripped = String.trim line in
        if starts_with_s "#include" stripped then
          if Str.string_match include_re stripped 0 then
            match find_include dirs (Str.matched_group 1 stripped) with
            | Some path -> (pp + contrib_lines (Utils.read_file path) dirs, acc)
            | None -> (pp, acc)
          else (pp, acc)
        else if starts_with_s "#define" stripped then (pp, acc)
        else (pp + 1, (pp, lineno) :: acc))
      (1, [])
      (List.mapi (fun i l -> (i + 1, l)) lines)
  in
  List.rev acc

let line_map_json source dirs : json =
  JList (List.map (fun (pp, src) -> JList [ JInt pp; JInt src ]) (build_line_map source dirs))
