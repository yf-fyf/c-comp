(*
   ソース上の位置。

   前処理後ソースの UTF-8 バイト半開区間 [start_offset, end_offset) と、その先頭の行番号を持つ。
   行番号はエラーメッセージ用、オフセットはアセンブリの見出しに元の C を切り出すために使う。
   前処理で #include を展開すると行番号はずれるが、オフセットは前処理後ソースへの位置なので
   必ず一致する。

   構文木のノードは全部この 1 フィールドだけを持ち、行番号と区間を別々には持たない。
*)

type t = { line : int; start_offset : int; end_offset : int }

(* menhir の $startpos / $endpos から作る *)
let of_positions (start : Lexing.position) (stop : Lexing.position) =
  { line = start.pos_lnum; start_offset = start.pos_cnum; end_offset = stop.pos_cnum }

let line_of (pos : Lexing.position) = pos.pos_lnum
