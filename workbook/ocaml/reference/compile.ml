(*
   駆動。前処理 → 構文解析 → 型付け → コード生成 → 文字列化 を 1 本につなぐ。

   ここを通す限り、コマンドラインから呼んでも他のプログラムから呼んでも
   同じ順序で同じ結果になる。状態はすべて呼び出しの中で作って捨てるので、
   何度呼んでも前回の影響を受けない。
*)

let init_lexbuf filename source =
  let lexbuf = Lexing.from_string source in
  lexbuf.lex_curr_p <-
    { Lexing.pos_fname = filename; pos_lnum = 1; pos_bol = 0; pos_cnum = 0 };
  lexbuf

let parse ~filename source =
  let lexbuf = init_lexbuf filename source in
  try Parser.program Lexer.token lexbuf
  with Parser.Error ->
    Diag.error ~phase:Diag.Parse ~line:lexbuf.lex_curr_p.pos_lnum "この形は構文として解釈できない"

(* units は (ファイル名, ソース) の並び。前処理は support のものをそのまま使う
   （前処理エラーは support 側がその場で印字して終了する）。 *)
let compile_units ~comments units =
  try
    let parsed =
      List.map
        (fun (filename, source) ->
          (* 見出しに元の C を出すため、前処理後ソースも一緒に持ち回る。
             位置はこのソースへのものなので、ファイルごとに対応付けておく必要がある *)
          let preprocessed = Preprocess.preprocess source filename in
          (preprocessed, parse ~filename preprocessed))
        units
    in
    let prog : Tast.program = Typing.type_program parsed in
    let em = Emitter.create () in
    let g = Codegen.create_genv em prog.layout in
    Codegen.gen_program g prog;
    Ok (Emitter.to_string ~comments em)
  with Diag.Error e -> Error e

let compile_source ~comments ?(filename = "input.c") source =
  compile_units ~comments [ (filename, source) ]
