(* コマ8以降で使う、提供済みの型変換と条件式の共通型。 *)
open Ast_def

let convert_to emit = function
  | TyChar -> emit "  slli a0, a0, 56"; emit "  srai a0, a0, 56"
  | _ -> ()

let conditional_type then_ then_ty else_ else_ty =
  let is_null = function Num { value = 0; _ } -> true | _ -> false in
  match then_ty, else_ty with
  | (TyInt | TyChar), (TyInt | TyChar) -> TyInt
  | a, b when a = b -> a
  | TyPtr _, TyPtr TyVoid | TyPtr TyVoid, TyPtr _ -> TyPtr TyVoid
  | (TyPtr _ as ty), _ when is_null else_ -> ty
  | _, (TyPtr _ as ty) when is_null then_ -> ty
  | _ -> failwith "型エラー: 条件式の両腕の型が対応しません"
