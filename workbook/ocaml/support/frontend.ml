(*
   Frontend の統合入口。
   前処理 → 字句解析（ocamllex） → 構文解析（menhir） をまとめる。
*)

let init_lexbuf filename source =
  let lexbuf = Lexing.from_string source in
  lexbuf.lex_curr_p <-
    {
      Lexing.pos_fname = filename;
      Lexing.pos_lnum = 1;
      Lexing.pos_bol = 0;
      Lexing.pos_cnum = 0;
    };
  lexbuf

let parse_source ?(already_preprocessed = false) ~filename source =
  let preprocessed =
    if already_preprocessed then source else Preprocess.preprocess source filename
  in
  let lexbuf = init_lexbuf filename preprocessed in
  try Parser.program Lexer.token lexbuf with
  | Parser.Error
  | Parsing.Parse_error ->
      let line = lexbuf.Lexing.lex_curr_p.Lexing.pos_lnum in
      failwith (Printf.sprintf "構文解析エラー: line %d" line)

let parse_file filename =
  Struct_env.reset ();
  let source = Utils.read_file filename in
  parse_source ~filename source
