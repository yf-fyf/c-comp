(*
   C の型。

   このサブセットの型は int / char / void とポインタ、それに struct だけである。
   struct はタグ参照だけを持ち、フィールドの並びと変位は Layout が管理する。
   型はここだけで定義し、構文木・型付き木・コード生成のすべてがこれを共有する。
*)

type t = Int | Char | Void | Ptr of t | Struct of string

let is_ptr = function Ptr _ -> true | _ -> false

(* 注記やエラーメッセージに出す名前 *)
let name = function
  | Int -> "int"
  | Char -> "char"
  | Void -> "void"
  | Ptr _ -> "ポインタ"
  | Struct tag -> "struct " ^ tag
