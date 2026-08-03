(*
   必修パート（コマ1〜15）の完成版リファレンス実装のコマンドライン。

   生成されるアセンブリは lecture15 と同一である（run_tests.py の等価性テストで
   担保している）。違うのは実装の作りで、こちらは

     ast.ml / lexer.mll / parser.mly  構文木と、それを作る字句・構文解析
     layout.ml   型の大きさ・整列と struct のレイアウト
     strings.ml  文字列リテラルの通し番号
     tast.ml     型と変数の置き場を決め終えた木
     typing.ml   構文木から型付き木を作る（型・変数解決・エラー検出）
     asm.ml      アセンブリの命令・行を表す型と、その印字
     emitter.ml  注記つきの行バッファ
     codegen.ml  型付き木からアセンブリを出す
     compile.ml  これらをつなぐ駆動
     mycc_ref.ml（このファイル）コマンドラインの解釈と印字

   に分けてある。--no-comments を付けなければ、どの命令をどの生成関数が
   出したのかを示すコメントが付く。
*)

let usage () =
  prerr_endline "使い方: dune exec ./mycc_ref.exe -- [--no-comments] <source.c> [...]";
  prerr_endline "  --no-comments: 生成元を示すコメントを付けずに出力する";
  exit 1

let () =
  let args = List.tl (Array.to_list Sys.argv) in
  let comments = not (List.mem "--no-comments" args) in
  let files = List.filter (fun a -> a <> "--no-comments") args in
  if files = [] then usage ();
  let units = List.map (fun file -> (file, Utils.read_file file)) files in
  match Refcomp.Compile.compile_units ~comments units with
  | Ok asm -> print_string asm
  | Error e ->
      prerr_endline (Refcomp.Diag.to_string e);
      exit 1
