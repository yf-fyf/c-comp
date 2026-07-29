{
open Parser

let lex_error lexbuf msg =
  let line = lexbuf.Lexing.lex_curr_p.Lexing.pos_lnum in
  failwith (Printf.sprintf "字句解析エラー(line %d): %s" line msg)

let newline lexbuf =
  let p = lexbuf.Lexing.lex_curr_p in
  lexbuf.Lexing.lex_curr_p <-
    { p with
      Lexing.pos_lnum = p.Lexing.pos_lnum + 1;
      Lexing.pos_bol = p.Lexing.pos_cnum }

let keyword_or_ident = function
  | "int" -> KW_INT
  | "char" -> KW_CHAR
  | "void" -> KW_VOID
  | "struct" -> KW_STRUCT
  | "typedef" -> TYPEDEF
  | "if" -> IF
  | "else" -> ELSE
  | "while" -> WHILE
  | "for" -> FOR
  | "return" -> RETURN
  | "break" -> BREAK
  | "continue" -> CONTINUE
  | "sizeof" -> SIZEOF
  | s -> if Typedef_env.mem s then TYPE_NAME s else IDENT s

let decode_escape = function
  | 'n' -> 10
  | 't' -> 9
  | '\\' -> 92
  | '\'' -> 39
  | '"' -> 34
  | '0' -> 0
  | 'r' -> 13
  | c -> Char.code c

let parse_char_literal s =
  if String.length s < 3 then invalid_arg "char literal";
  if s.[1] = '\\' then decode_escape s.[2] else Char.code s.[1]

let parse_string_literal s =
  let n = String.length s in
  let buf = Buffer.create (max 0 (n - 2)) in
  let i = ref 1 in
  while !i < n - 1 do
    if s.[!i] = '\\' then (
      if !i + 1 >= n - 1 then invalid_arg "string literal";
      incr i;
      Buffer.add_char buf (Char.chr (decode_escape s.[!i]));
      incr i)
    else (
      Buffer.add_char buf s.[!i];
      incr i)
  done;
  Buffer.contents buf
}

let digit = ['0'-'9']
let ident_start = ['a'-'z' 'A'-'Z' '_']
let ident_char = ['a'-'z' 'A'-'Z' '0'-'9' '_']

rule token = parse
  | [' ' '\t' '\r'] { token lexbuf }
  | '\n' { newline lexbuf; token lexbuf }
  | "//" [^ '\n']* { token lexbuf }
  | "/*" { block_comment lexbuf; token lexbuf }

  | "..." { ELLIPSIS }

  | "==" { EQEQ }
  | "!=" { NE }
  | "<=" { LE }
  | ">=" { GE }
  | "&&" { ANDAND }
  | "||" { OROR }
  | "<<" { SHL }
  | ">>" { SHR }
  | "->" { ARROW }

  | '+' { PLUS }
  | '-' { MINUS }
  | '*' { STAR }
  | '/' { SLASH }
  | '%' { PERCENT }
  | '&' { AMP }
  | '|' { PIPE }
  | '^' { CARET }
  | '~' { TILDE }
  | '!' { BANG }
  | '<' { LT }
  | '>' { GT }
  | '=' { ASSIGN }
  | ';' { SEMI }
  | ',' { COMMA }
  | '.' { DOT }
  | '(' { LPAREN }
  | ')' { RPAREN }
  | '{' { LBRACE }
  | '}' { RBRACE }
  | '[' { LBRACKET }
  | ']' { RBRACKET }

  | digit+ as num { NUM (int_of_string num) }
  | '\'' ("\\" _ | [^ '\\' '\'']) '\'' as c { CHAR_LIT (parse_char_literal c) }
  | '"' (("\\" _) | [^ '"' '\\'])* '"' as s { STR (parse_string_literal s) }
  | ident_start ident_char* as id { keyword_or_ident id }

  | eof { EOF }
  | _ as c { lex_error lexbuf (Printf.sprintf "予期しない文字: %C" c) }

and block_comment = parse
  | "*/" { () }
  | '\n' { newline lexbuf; block_comment lexbuf }
  | eof { lex_error lexbuf "ブロックコメントが閉じていません" }
  | _ { block_comment lexbuf }
