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

(* line も col も 1 起点。0 は「その情報が取れなかった」を表す（前処理は行までしか持たない）。
   col は行頭からの UTF-8 バイト数で数える（Loc.col_of と同じ定義）。 *)
type t = { phase : phase; line : int; col : int; msg : string }

exception Error of t

let phase_name = function
  | Preprocess -> "前処理エラー"
  | Parse -> "構文解析エラー"
  | Typing -> "OCamlコード生成エラー"

let error ~phase ~line ~col fmt =
  Printf.ksprintf (fun msg -> raise (Error { phase; line; col; msg })) fmt

(* line = 0 は「位置が取れなかった」を表し、行の表示を省く。
   行が取れて列が取れない（col = 0）ときは行だけを出す *)
let to_string { phase; line; col; msg } =
  let where =
    if line = 0 then ""
    else if col = 0 then Printf.sprintf "[line %d] " line
    else Printf.sprintf "[line %d, col %d] " line col
  in
  Printf.sprintf "%s: %s%s" (phase_name phase) where msg
