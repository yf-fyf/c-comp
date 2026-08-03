(*
   ブラウザ向け API（webapps.md 3.3）。
   境界は「文字列を渡して JSON 文字列を受け取る」に限定する。

   公開: myccCore.parse(source) / astSexp(source, showLine) / astDot(source, showLine)
        / compile(source, comments)
   typeInfo は B2（struct レイアウト可視化）に着手する時点で足す。
*)

open Js_of_ocaml
module C = Core_lib
open C.Astdump

(* ブラウザの擬似ファイルシステムに lib.h を置き、#include "lib.h" を解決する。
   node 実行時など登録できない環境では include なしのソースだけが通る。 *)
let vfs_dir = "/static"
let () =
  try Sys_js.create_file ~name:(Filename.concat vfs_dir "lib.h") ~content:Lib_h.content
  with _ -> ()

let include_dirs = [ vfs_dir ]
let filename = "input.c"

let error_line msg =
  try
    ignore (Str.search_forward (Str.regexp "line \\([0-9]+\\)") msg 0);
    int_of_string (Str.matched_group 1 msg)
  with Not_found -> 0

let error_json e =
  let msg =
    match e with Failure m -> m | e -> Printexc.to_string e
  in
  JObj [ ("message", JStr msg); ("line", JInt (error_line msg)) ]

(* 前処理 + 構文解析を行い、成功時は f を呼ぶ。失敗はエラー JSON に変換する *)
let with_parse source f =
  try
    Struct_env.reset ();
    let mapped = Preprocess.preprocess_with_map ~include_dirs source filename in
    Struct_env.reset ();
    let prog = Frontend.parse_source ~already_preprocessed:true ~filename mapped.text in
    f mapped prog
  with e -> JObj [ ("ok", JBool false); ("errors", JList [ error_json e ]) ]

let parse_json source =
  with_parse source (fun mapped prog ->
      let map_span = source_range_mapper source mapped.segments in
      JObj
        [ ("ok", JBool true);
          ("tokens", tokens_json ~filename mapped.text);
          ("ast", program_json ~map_span prog);
          ("lineMap", line_map_json source include_dirs) ])

let text_json render source show_line =
  with_parse source (fun _mapped prog ->
      JObj [ ("ok", JBool true); ("text", JStr (render ?show_line:(Some show_line) prog)) ])

let phase_string = function
  | Refcomp.Diag.Preprocess -> "preprocess"
  | Refcomp.Diag.Parse -> "parse"
  | Refcomp.Diag.Typing -> "typing"

(* 文と命令の対応（A3）。参考実装は「前処理後ソースのバイト範囲 → 出力の行番号」で返すので、
   ここで範囲を元ソースの UTF-16 位置へ写す（AST ノードの sourceRanges と同じ土俵に載せる）。
   マクロ展開や include 由来で元ソースへ写せない文は落とす。 *)
let stmt_map_json source (spans : Refcomp.Emitter.stmt_span list) =
  let map_span =
    match Preprocess.preprocess_with_map_exn ~include_dirs source filename with
    | mapped -> source_range_mapper source mapped.segments
    | exception _ -> fun _ -> []
  in
  JList
    (List.filter_map
       (fun (s : Refcomp.Emitter.stmt_span) ->
         match map_span (Some { Ast_def.start_offset = s.s_start; end_offset = s.s_end }) with
         | [] -> None
         | ranges ->
             Some
               (JObj
                  [ ("sourceRanges",
                      JList
                        (List.map
                           (fun (from_pos, to_pos) ->
                             JObj [ ("from", JInt from_pos); ("to", JInt to_pos) ])
                           ranges));
                    (* 出力アセンブリの行番号（1 起点の閉区間）。comments の有無で変わる *)
                    ("fromLine", JInt s.from_line);
                    ("toLine", JInt s.to_line) ]))
       spans)

let compile_json source comments =
  try
    match Refcomp.Compile.compile_source_with_spans ~comments ~include_dirs ~filename source with
    | Ok (text, spans) ->
        JObj
          [ ("ok", JBool true);
            ("text", JStr text);
            ("stmtMap", stmt_map_json source spans) ]
    | Error (diag : Refcomp.Diag.t) ->
        JObj
          [ ("ok", JBool false);
            ("errors",
              JList
                [ JObj
                    [ ("message", JStr diag.msg);
                      ("line", JInt diag.line);
                      (* 列は行頭からの UTF-8 バイト数（1 起点）。0 = 取れなかった *)
                      ("col", JInt diag.col);
                      ("phase", JStr (phase_string diag.phase)) ]
                ]) ]
  with e -> JObj [ ("ok", JBool false); ("errors", JList [ error_json e ]) ]

let () =
  Js.export "myccCore"
    (object%js
       method parse (s : Js.js_string Js.t) =
         Js.string (json_to_string (parse_json (Js.to_string s)))

       method astSexp (s : Js.js_string Js.t) (show_line : bool Js.t) =
         Js.string
           (json_to_string (text_json program_sexp (Js.to_string s) (Js.to_bool show_line)))

       method astDot (s : Js.js_string Js.t) (show_line : bool Js.t) =
         Js.string
           (json_to_string (text_json program_dot (Js.to_string s) (Js.to_bool show_line)))

       method compile (s : Js.js_string Js.t) (comments : bool Js.t) =
         Js.string
           (json_to_string (compile_json (Js.to_string s) (Js.to_bool comments)))
    end)
