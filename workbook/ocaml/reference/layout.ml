(*
   型の大きさ・整列と、struct のレイアウト。

   レイアウトは言語仕様「実行時の意味」に従う:
   フィールドは宣言順、各オフセットはそのフィールドの整列へ切り上げ、
   struct 全体のサイズは struct の整列（最大フィールド整列）の倍数へ切り上げ。

   表は不変な Map で、定義を 1 つ足すたびに新しい表を返す。入れ子 struct の
   大きさは**その定義を足す時点の表**で解決するので、struct_def を並んだ順に
   畳み込むこと（未定義タグは整列 8・大きさ 0 として扱う）。
*)

module Tags = Map.Make (String)

type field = { offset : int; ty : Ctype.t }
type info = { fields : (string * field) list; size : int; align : int }
type t = info Tags.t

let empty : t = Tags.empty
let find (t : t) tag = Tags.find_opt tag t

let align_to n align = (n + align - 1) / align * align

let align_of t = function
  | Ctype.Int -> 4
  | Ctype.Char -> 1
  | Ctype.Void -> 1
  | Ctype.Ptr _ -> 8
  | Ctype.Struct tag -> ( match find t tag with Some i -> i.align | None -> 8)

let size_of t = function
  | Ctype.Int -> 4
  | Ctype.Char -> 1
  | Ctype.Void -> 1
  | Ctype.Ptr _ -> 8
  | Ctype.Struct tag -> ( match find t tag with Some i -> i.size | None -> 0)

(* 同じタグを 2 度定義したら後勝ち *)
let add t ~tag ~fields =
  let offset, align, rev =
    List.fold_left
      (fun (offset, align, acc) (fname, fty) ->
        let a = align_of t fty in
        let offset = align_to offset a in
        (offset + size_of t fty, max align a, (fname, { offset; ty = fty }) :: acc))
      (0, 1, []) fields
  in
  Tags.add tag { fields = List.rev rev; size = align_to offset align; align } t

(* 変数 1 個がスタックや .bss で占める大きさ。char でも 8 バイト使う *)
let slot_size t ty = align_to (size_of t ty) 8

(* 積んだ局所変数の合計から、プロローグで下げるフレームの大きさを決める *)
let frame_size stack_offset = align_to stack_offset 16

(* 呼び出し規約で引数に使えるレジスタの本数（a0–a7）。
   実際のレジスタの並びは Asm.arg_regs にある。 *)
let max_args = 8
