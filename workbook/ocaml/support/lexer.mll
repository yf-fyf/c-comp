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

(* 予約語は使用する 12 語のみ（言語仕様「字句」参照） *)
let keyword_or_ident = function
  | "int" -> KW_INT
  | "char" -> KW_CHAR
  | "void" -> KW_VOID
  | "struct" -> KW_STRUCT
  | "if" -> IF
  | "else" -> ELSE
  | "while" -> WHILE
  | "for" -> FOR
  | "return" -> RETURN
  | "break" -> BREAK
  | "continue" -> CONTINUE
  | "sizeof" -> SIZEOF
  | s -> IDENT s

(* エスケープは 6 種のみ（言語仕様「リテラル」参照） *)
let decode_escape = function
  | 'n' -> 10
  | 't' -> 9
  | '\\' -> 92
  | '\'' -> 39
  | '"' -> 34
  | '0' -> 0
  | c -> failwith (Printf.sprintf "字句解析エラー: 不正なエスケープ: \\%c" c)

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

let int_max = 2147483647
}

let digit = ['0'-'9']
let ident_start = ['a'-'z' 'A'-'Z' '_']
let ident_char = ['a'-'z' 'A'-'Z' '0'-'9' '_']

rule token = parse
  | [' ' '\t' '\r'] { token lexbuf }
  | '\n' { newline lexbuf; token lexbuf }
  | "//" [^ '\n']* { token lexbuf }

  | "..." { ELLIPSIS }

  | "==" { EQEQ }
  | "!=" { NE }
  | "<=" { LE }
  | ">=" { GE }
  | "&&" { ANDAND }
  | "||" { OROR }
  | "->" { ARROW }
  | "++" { PLUSPLUS }
  | "--" { MINUSMINUS }

  | '+' { PLUS }
  | '-' { MINUS }
  | '*' { STAR }
  | '/' { SLASH }
  | '%' { PERCENT }
  | '&' { AMP }
  | '!' { BANG }
  | '<' { LT }
  | '>' { GT }
  | '=' { ASSIGN }
  | '?' { QUESTION }
  | ':' { COLON }
  | ';' { SEMI }
  | ',' { COMMA }
  | '.' { DOT }
  | '(' { LPAREN }
  | ')' { RPAREN }
  | '{' { LBRACE }
  | '}' { RBRACE }
  | '[' { LBRACKET }
  | ']' { RBRACKET }

  | digit+ as num {
      (* 10 進のみ。'0' 単独を除き先頭 0 は不可、上限は INT_MAX *)
      if String.length num > 1 && num.[0] = '0' then
        lex_error lexbuf
          (Printf.sprintf "整数リテラルの先頭を 0 にはできない（8進表記はない）: %s" num)
      else
        match int_of_string_opt num with
        | Some v when v <= int_max -> NUM v
        | _ ->
            lex_error lexbuf
              (Printf.sprintf "整数リテラルが上限 %d を超えている: %s" int_max num) }
  | '\'' ("\\" _ | [^ '\\' '\'']) '\'' as c { CHAR_LIT (parse_char_literal c) }
  | '"' (("\\" _) | [^ '"' '\\'])* '"' as s { STR (parse_string_literal s) }
  | ident_start ident_char* as id { keyword_or_ident id }

  | eof { EOF }
  | _ as c { lex_error lexbuf (Printf.sprintf "予期しない文字: %C" c) }
