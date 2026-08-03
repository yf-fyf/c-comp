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

(*
   構文解析。menhir の incremental API（--table で生成される MenhirInterpreter）を使う。

   単に Parser.program を呼ぶのと受理する言語は同じだが、エラーになったとき
   「構文解析器がどの状態で詰まったか」の状態番号が取れる。この番号で
   parser.messages（状態ごとの日本語メッセージ）を引き、「ここには何が来るはずか」まで出す。
   parser.messages に載っていない状態は Not_found になるので、汎用の 1 文に落とす。
*)
module I = Parser.MenhirInterpreter

(* 詰まった状態の番号。スタックが空（まだ 1 つも還元・移動していない）なら初期状態 0 *)
let state_number env =
  match I.top env with None -> 0 | Some (I.Element (s, _, _, _)) -> I.number s

let syntax_error env =
  let msg =
    match String.trim (Parser_messages.message (state_number env)) with
    | "" -> "この形は構文として解釈できない"
    | m -> m
    | exception Not_found -> "この形は構文として解釈できない"
  in
  (* 位置は「読めなかったトークン」の先頭。まだ何も読んでいない場合はソース先頭になる *)
  let startp, _ = I.positions env in
  Diag.error ~phase:Diag.Parse ~line:startp.Lexing.pos_lnum ~col:(Loc.col_of startp) "%s" msg

let parse ~filename source =
  let lexbuf = init_lexbuf filename source in
  let rec run (checkpoint : Ast.program I.checkpoint) =
    match checkpoint with
    | I.InputNeeded _ ->
        let token = Lexer.token lexbuf in
        run (I.offer checkpoint (token, lexbuf.lex_start_p, lexbuf.lex_curr_p))
    | I.Shifting _ | I.AboutToReduce _ -> run (I.resume checkpoint)
    | I.HandlingError env -> syntax_error env
    | I.Accepted prog -> prog
    (* Rejected は HandlingError を resume したときにしか出ない。ここでは出ない *)
    | I.Rejected -> assert false
  in
  run (Parser.Incremental.program lexbuf.lex_curr_p)

(* units は (ファイル名, ソース) の並び。前処理は support のものをそのまま使う。
   reference/ は例外のまま受け取る preprocess_exn を使い、Diag.Preprocess に
   載せ替えて他フェーズ（Parse / Typing）と同じ経路でエラーを扱う。
   sessions/koma*.ml と web/core は従来どおり Preprocess.preprocess /
   preprocess_with_map（その場で印字して終了する）を使い続けるため、
   ここでの変更は reference/ の内部だけに閉じている。 *)
(* 文と命令の対応（Emitter.stmt_span）も一緒に返す入口。
   範囲は前処理後ソースへのバイト位置なので、元ソースへ写すのは呼んだ側の仕事である
   （web/core/js/api.ml が Preprocess の対応表で写す）。 *)
let compile_units_with_spans ~comments ?include_dirs units =
  try
    let parsed =
      List.map
        (fun (filename, source) ->
          (* 見出しに元の C を出すため、前処理後ソースも一緒に持ち回る。
             位置はこのソースへのものなので、ファイルごとに対応付けておく必要がある *)
          let preprocessed =
            try Preprocess.preprocess_exn ?include_dirs source filename with
            | Preprocess.Pp_error { line; msg; _ } ->
                (* 前処理は行までしか位置を持たないので col は 0（不明）にする *)
                Diag.error ~phase:Diag.Preprocess ~line ~col:0 "%s" msg
          in
          (preprocessed, parse ~filename preprocessed))
        units
    in
    let prog : Tast.program = Typing.type_program parsed in
    let em = Emitter.create () in
    let g = Codegen.create_genv em prog.layout in
    Codegen.gen_program g prog;
    Ok (Emitter.to_string_with_spans ~comments em)
  with Diag.Error e -> Error e

let compile_units ~comments ?include_dirs units =
  match compile_units_with_spans ~comments ?include_dirs units with
  | Ok (text, _spans) -> Ok text
  | Error e -> Error e

let compile_source ~comments ?include_dirs ?(filename = "input.c") source =
  compile_units ~comments ?include_dirs [ (filename, source) ]

let compile_source_with_spans ~comments ?include_dirs ?(filename = "input.c") source =
  compile_units_with_spans ~comments ?include_dirs [ (filename, source) ]
