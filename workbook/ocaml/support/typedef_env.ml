(*
   typedef 名と型の対応表を管理する。
   lexer が識別子を TYPE_NAME として返すためと、
   パーサー / コード生成が型名を解決するための両方に利用する。
*)

open Ast_def

let tbl : (string, ty) Hashtbl.t = Hashtbl.create 64

let reset () = Hashtbl.clear tbl

let set name ty = Hashtbl.replace tbl name ty

(* パーサーの typedef_decl 用: 未登録のときだけ型を設定する。
   collect_struct_typedefs が先に登録している場合は上書きしない。 *)
let register_name name ty =
  if not (Hashtbl.mem tbl name) then Hashtbl.replace tbl name ty

(* 構造体 typedef の前方登録（パーサーの mid-rule action 用）。
   タグ名と typedef 名を TyUnknown で即時登録し、
   構造体本体の自己参照が解決できるようにする。 *)
let register_forward ?(tag = "") name =
  set name (TyUnknown name);
  if tag <> "" then set ("struct " ^ tag) (TyUnknown ("struct " ^ tag))

let find name = Hashtbl.find_opt tbl name

let mem name = Hashtbl.mem tbl name

(* 登録済みの (名前, 型) を畳み込む（AST ダンプの型表示などの読み取り用） *)
let fold f init = Hashtbl.fold f tbl init
