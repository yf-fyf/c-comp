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

(* 条件式は両腕から型を決め、選んだ腕だけを実行する。 *)
let conditional_type ~line ~col ~then_ty ~else_ty ~then_null ~else_null =
  match then_ty, else_ty with
  | (Int | Char), (Int | Char) -> Int
  | a, b when a = b -> a
  | Ptr _, Ptr Void | Ptr Void, Ptr _ -> Ptr Void
  | (Ptr _ as ty), _ when else_null -> ty
  | _, (Ptr _ as ty) when then_null -> ty
  | _ -> Diag.error ~phase:Diag.Typing ~line ~col "条件式の両腕の型が対応しません"
