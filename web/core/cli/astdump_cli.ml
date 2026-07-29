(*
   黄金テスト用 CLI。
   parse_viewer.py --format sexp / dot と同じ出力をネイティブで出す。
   include の解決は support/preprocess.ml の既定（ファイルのディレクトリ →
   scaffold/ → . など）に従うため、workbook/ から実行する。
*)

let usage () : 'a =
  prerr_endline "usage: astdump_cli FILE [--format sexp|dot|json] [--show-line]";
  exit 2

let () =
  let file = ref None in
  let fmt = ref "sexp" in
  let show_line = ref false in
  let rec parse_args = function
    | [] -> ()
    | "--format" :: v :: rest ->
        fmt := v;
        parse_args rest
    | "--show-line" :: rest ->
        show_line := true;
        parse_args rest
    | a :: rest when !file = None && String.length a > 0 && a.[0] <> '-' ->
        file := Some a;
        parse_args rest
    | _ -> usage ()
  in
  parse_args (List.tl (Array.to_list Sys.argv));
  match !file with
  | None -> usage ()
  | Some f -> (
      try
        let prog = Core_lib.Frontend.parse_file f in
        let out =
          match !fmt with
          | "sexp" -> Core_lib.Astdump.program_sexp ~show_line:!show_line prog
          | "dot" -> Core_lib.Astdump.program_dot ~show_line:!show_line prog
          | "json" -> Core_lib.Astdump.(json_to_string (program_json prog))
          | _ -> usage ()
        in
        print_endline out
      with Failure msg ->
        prerr_endline msg;
        exit 1)
