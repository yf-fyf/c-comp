(*
   struct タグ表: タグ名 → フィールドレイアウト。
   scaffold/parser.py は struct 宣言を読み捨てるが、OCaml 側は
   各回の実装（sessions/lectureNN.ml）のコード生成がレイアウトを引けるように表へ登録する。

   レイアウトは言語仕様「実行時の意味」に従う:
   フィールドは宣言順、各オフセットはそのフィールドのアラインメントへ切り上げ、
   struct 全体のサイズは struct のアラインメント（最大フィールドアラインメント）の倍数へ切り上げ。
*)

open Ast_def

type field_info = { offset : int; ty : ty }
type info = { fields : (string * field_info) list; size : int; align : int }

let tbl : (string, info) Hashtbl.t = Hashtbl.create 64

let reset () = Hashtbl.clear tbl
let find tag = Hashtbl.find_opt tbl tag

let align_of_ty = function
  | TyInt -> 4
  | TyChar -> 1
  | TyVoid -> 1
  | TyPtr _ -> 8
  | TyStruct tag -> ( match find tag with Some i -> i.align | None -> 8)

let size_of_ty = function
  | TyInt -> 4
  | TyChar -> 1
  | TyVoid -> 1
  | TyPtr _ -> 8
  | TyStruct tag -> ( match find tag with Some i -> i.size | None -> 0)

let align_to n a = (n + a - 1) / a * a

let define tag fields =
  let offset, align, rev =
    List.fold_left
      (fun (offset, align, acc) (fname, fty) ->
        let a = align_of_ty fty in
        let offset = align_to offset a in
        (offset + size_of_ty fty, max align a, (fname, { offset; ty = fty }) :: acc))
      (0, 1, []) fields
  in
  let size = align_to offset align in
  Hashtbl.replace tbl tag { fields = List.rev rev; size; align }
