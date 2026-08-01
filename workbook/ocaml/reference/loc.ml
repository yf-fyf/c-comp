(*
   ソース上の位置。

   前処理後ソースの UTF-8 バイト半開区間 [start_offset, end_offset) と、その先頭の行番号・
   列番号を持つ。行番号と列番号はエラーメッセージ用、オフセットはアセンブリの見出しに元の C を
   切り出すために使う。前処理で #include を展開すると行番号はずれるが、オフセットは
   前処理後ソースへの位置なので必ず一致する。

   列は 1 起点で、行頭からの UTF-8 バイト数で数える（Lexing.position の pos_bol からの差）。
   バイト単位なので、日本語を含む行では見た目の桁とはずれる。エラー位置の目印には足りる。

   構文木のノードは全部この 1 フィールドだけを持ち、行番号と区間を別々には持たない。
*)

type t = { line : int; col : int; start_offset : int; end_offset : int }

let col_of (pos : Lexing.position) = pos.pos_cnum - pos.pos_bol + 1

(* menhir の $startpos / $endpos から作る *)
let of_positions (start : Lexing.position) (stop : Lexing.position) =
  {
    line = start.pos_lnum;
    col = col_of start;
    start_offset = start.pos_cnum;
    end_offset = stop.pos_cnum;
  }

let line_of (pos : Lexing.position) = pos.pos_lnum
