(*
   必修パート（コマ2〜16）の完成版リファレンス実装。

   生成されるアセンブリは koma16 と同一である（run_tests.py の等価性テストで
   担保している）。違うのは実装の作りで、こちらは

     asm.ml     アセンブリの命令・行を表す型と、その印字
     emitter.ml 注記つきの行バッファ
     codegen.ml コンパイラ本体
     mycc_ref.ml（このファイル）コマンドラインとパースの駆動

   に分けてある。--no-comments を付けなければ、どの命令をどの生成関数が
   出したのかを示すコメントが付く。
*)

(* 見出しに元の C を出すため、前処理後ソースも一緒に返す。
   span はこのソースへの位置なので、ファイルごとに対応付けておく必要がある。 *)
let parse_file filename =
  let source = Utils.read_file filename in
  let preprocessed = Preprocess.preprocess source filename in
  let prog = Frontend.parse_source ~already_preprocessed:true ~filename preprocessed in
  (preprocessed, prog)

let usage () =
  prerr_endline "使い方: dune exec ./mycc_ref.exe -- [--no-comments] <source.c> [...]";
  prerr_endline "  --no-comments: 生成元を示すコメントを付けずに出力する";
  exit 1

let () =
  let args = List.tl (Array.to_list Sys.argv) in
  let comments = not (List.mem "--no-comments" args) in
  let files = List.filter (fun a -> a <> "--no-comments") args in
  if files = [] then usage ();
  Struct_env.reset ();
  let em = Emitter.create () in
  let g = Codegen.create_genv em in
  match Codegen.gen_program g (List.map parse_file files) with
  | () -> Emitter.print ~comments em
  | exception Codegen.Error { line; msg } ->
      prerr_endline (Codegen.error_message line msg);
      exit 1
