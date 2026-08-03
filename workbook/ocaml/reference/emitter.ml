(*
   注記つきの行バッファ。コード生成と印字の間に挟む層である。

   コード生成中は「どの行を、どの担当が、どの見出しの下で出したか」を
   そのままデータとして貯めるだけにする。同じ担当の注記を繰り返さない、
   1 命令も出なかった見出しは捨てる、といった見せ方の規則は
   すべて print の中の畳み込みで決める。
*)

(* 行に添える注記。
   Owner は「この行を出した生成関数」。同じ担当が続く間は繰り返さない。
   Aside はその 1 行だけの説明で、担当が同じでも必ず出す。 *)
type note = Bare | Owner of string | Aside of string

type note_line = { line : Asm.line; note : note }

(* ソース上の範囲。Loc.t の一部だが、こちらは印字の都合しか知らないので
   行番号・列は持たず、前処理後ソースのバイト半開区間だけを覚える。 *)
type span = { sp_start : int; sp_end : int }

type item =
  | Heading of { text : string; depth : int }
  | Line of note_line
  (* 「ここからここまでが 1 つの文の出力」の目印。印字では 1 行も使わない。
     どの文がどの命令を出したかを、出力の行番号で外へ返すために使う（web の A3）。 *)
  | Enter of span
  | Leave

type t = {
  mutable rev_items : item list; (* 逆順に貯めて、印字のときに戻す *)
  mutable owners : string list; (* いま生成を担当している場所のスタック *)
  mutable depth : int; (* 見出しの入れ子の深さ *)
}

(* 文 1 つと、その文が出した命令の範囲（印字後の行番号、1 起点の閉区間） *)
type stmt_span = { s_start : int; s_end : int; from_line : int; to_line : int }

let create () = { rev_items = []; owners = []; depth = 0 }
let add t item = t.rev_items <- item :: t.rev_items

(* f が出す行の担当を owner にする *)
let with_note t owner f =
  t.owners <- owner :: t.owners;
  let result = Fun.protect ~finally:(fun () -> t.owners <- List.tl t.owners) f in
  result

(* note を渡すと、その行だけの説明として必ず印字される（ラベルや分岐など、
   担当より用途を書きたい場所で使う）。省略すると現在の担当が付く。 *)
let emit t ?note line =
  let note =
    match (note, t.owners) with
    | Some text, _ -> Aside text
    | None, owner :: _ when owner <> "" -> Owner owner
    | None, _ -> Bare
  in
  add t (Line { line; note })

let heading t text = add t (Heading { text; depth = t.depth })

(* 見出し 1 段分だけ深いところで f を走らせる *)
let nested t f =
  t.depth <- t.depth + 1;
  Fun.protect ~finally:(fun () -> t.depth <- t.depth - 1) f

(* f が出す行を「この範囲の文の出力」として囲む。入れ子の文はそのまま入れ子になる *)
let with_span t ~start_offset ~end_offset f =
  add t (Enter { sp_start = start_offset; sp_end = end_offset });
  Fun.protect ~finally:(fun () -> add t Leave) f

(* ── 印字 ── *)

(* 行末の注記を始める桁 *)
let note_column = 28

let heading_string text depth = Printf.sprintf "# %s── %s" (String.make (2 * depth) ' ') text

let string_of_note_line { line; note } last_owner =
  let text = Asm.print_line line in
  match note with
  | Bare -> (text, last_owner)
  | Owner owner when owner = last_owner -> (text, last_owner)
  | Owner owner | Aside owner ->
      (Printf.sprintf "%-*s # %s" note_column text owner, owner)

(* 印字と、文ごとの出力範囲の採取を 1 回で行う。
   範囲は「その文を囲む Enter … Leave の間に実際に出た行」なので、
   注記コメントの有無（見出し行が出るかどうか）でも必ず出力と揃う。 *)
let render ~comments t =
  let buf = Buffer.create 4096 in
  let line_no = ref 0 in
  let rev_spans = ref [] in
  (* いま開いている文のスタック。first は最初に出た行（0 = まだ出ていない） *)
  let open_spans = ref [] in
  let out line =
    Buffer.add_string buf line;
    Buffer.add_char buf '\n';
    incr line_no;
    List.iter (fun (_, first) -> if !first = 0 then first := !line_no) !open_spans
  in
  let enter sp = open_spans := (sp, ref 0) :: !open_spans in
  (* 1 行も出さなかった文（空文など）は範囲を持たないので捨てる *)
  let leave () =
    match !open_spans with
    | [] -> ()
    | (sp, first) :: rest ->
        open_spans := rest;
        if !first > 0 then
          rev_spans :=
            { s_start = sp.sp_start; s_end = sp.sp_end; from_line = !first; to_line = !line_no }
            :: !rev_spans
  in
  let items = List.rev t.rev_items in
  if not comments then
    List.iter
      (function
        | Line { line; _ } -> out (Asm.print_line line)
        | Heading _ -> ()
        | Enter sp -> enter sp
        | Leave -> leave ())
      items
  else begin
    (* pending は「まだ命令が出ていない見出し」。空文のように 1 命令も出さない文が
       あるので、命令が出るまで印字を遅らせ、次の見出しが来たら黙って捨てる。 *)
    let step (pending, last_owner) = function
      | Heading { text; depth } -> (Some (text, depth), last_owner)
      | Enter sp ->
          enter sp;
          (pending, last_owner)
      | Leave ->
          leave ();
          (pending, last_owner)
      | Line nl ->
          (* 見出しをまたいだら、担当が同じでも注記を出し直す *)
          let last_owner =
            match pending with
            | None -> last_owner
            | Some (text, depth) ->
                out (heading_string text depth);
                ""
          in
          let text, last_owner = string_of_note_line nl last_owner in
          out text;
          (None, last_owner)
    in
    ignore (List.fold_left step (None, "") items)
  end;
  (Buffer.contents buf, List.rev !rev_spans)

let to_string ~comments t = fst (render ~comments t)

(* 文と命令の対応も要る呼び出し口（web の A3）。印字は to_string と同じ経路を通る *)
let to_string_with_spans ~comments t = render ~comments t

(* 標準出力へ直接書く口。ライブラリとして使うときは to_string を呼ぶ *)
let print ~comments t = print_string (to_string ~comments t)
