(*
   利用者に見せるエラー。

   どのフェーズで落ちても同じ形になるように、位置つきの例外 1 本にまとめてある。
   result を返す形にしないのは、構文解析器（menhir）のアクションが result を返せず、
   parse フェーズだけ例外になってしまうためである。エラーは最初の 1 件で打ち切る
   （このサブセットの規模では、回復して複数件集める仕組みは釣り合わない）。

   コード生成はここを使わない。Typing を通った木は生成できることが型で保証されており、
   codegen 内の到達しない場合分けは assert false にする。
*)

type phase = Preprocess | Parse | Typing

type t = { phase : phase; line : int; msg : string }

exception Error of t

let phase_name = function
  | Preprocess -> "前処理エラー"
  | Parse -> "構文解析エラー"
  | Typing -> "OCamlコード生成エラー"

let error ~phase ~line fmt =
  Printf.ksprintf (fun msg -> raise (Error { phase; line; msg })) fmt

(* line = 0 は「位置が取れなかった」を表し、行の表示を省く *)
let to_string { phase; line; msg } =
  let where = if line = 0 then "" else Printf.sprintf "[line %d] " line in
  Printf.sprintf "%s: %s%s" (phase_name phase) where msg
