(*
   簡易前処理器: #include "..." と #define NAME value のみ対応。
*)

open Printf

let starts_with s prefix =
  let n = String.length s and m = String.length prefix in
  n >= m && String.sub s 0 m = prefix

let abs_path path =
  if Filename.is_relative path then Filename.concat (Sys.getcwd ()) path else path

let dirname_realpath path = Filename.dirname (abs_path path)

let keywords =
  [ "int"; "char"; "void"; "struct"; "if"; "else"; "while"; "for";
    "break"; "continue"; "return"; "sizeof" ]

let pp_error msg filename line =
  eprintf "%s:%d: 前処理エラー: %s\n" filename line msg;
  exit 1

type map_segment = {
  generated_start : int;
  generated_end : int;
  source_start : int;
  source_end : int;
}

type mapped_source = { text : string; segments : map_segment list }

type mapped_text = { value : string; origins : int option array }

let unmapped value = { value; origins = Array.make (String.length value) None }

let mapped_line ~map_source ~source_start value =
  let origins =
    Array.init (String.length value) (fun i ->
        if map_source then Some (source_start + i) else None)
  in
  { value; origins }

(* オブジェクト形式マクロを 1 段だけ適用する。置換結果にマクロ名が残る場合は
   エラー（多段参照は言語仕様外）。挿入された展開文字列は元ソース上に
   同じ文字範囲を持たないため未対応にする。 *)
let apply_defines defines_tbl (mapped : mapped_text) filename lineno =
  if Hashtbl.length defines_tbl = 0 then mapped
  else begin
    let names = Hashtbl.fold (fun k _ acc -> k :: acc) defines_tbl [] in
    let re =
      Str.regexp ("\\b\\(" ^ String.concat "\\|" (List.map Str.quote names) ^ "\\)\\b")
    in
    let value_buf = Buffer.create (String.length mapped.value) in
    let origins_rev = ref [] in
    let replaced = ref false in
    let append_original from_pos to_pos =
      if to_pos > from_pos then
        Buffer.add_substring value_buf mapped.value from_pos (to_pos - from_pos);
      for i = from_pos to to_pos - 1 do
        origins_rev := mapped.origins.(i) :: !origins_rev
      done
    in
    let append_replacement body =
      Buffer.add_string value_buf body;
      for _ = 1 to String.length body do origins_rev := None :: !origins_rev done
    in
    let rec loop pos =
      match
        try Some (Str.search_forward re mapped.value pos) with Not_found -> None
      with
      | None -> append_original pos (String.length mapped.value)
      | Some _ ->
          let first = Str.match_beginning () and last = Str.match_end () in
          let name = Str.matched_group 1 mapped.value in
          append_original pos first;
          append_replacement (Hashtbl.find defines_tbl name);
          replaced := true;
          loop last
    in
    loop 0;
    let result =
      { value = Buffer.contents value_buf; origins = Array.of_list (List.rev !origins_rev) }
    in
    if !replaced then (
      match
        try Some (Str.search_forward re result.value 0) with Not_found -> None
      with
      | Some _ ->
          pp_error
            ("マクロの多段参照は使えない: " ^ Str.matched_group 1 result.value)
            filename lineno
      | None -> ());
    result
  end

let segments_of_origins origins =
  let n = Array.length origins in
  let rec loop generated_start source_start i acc =
    if i = n then
      match source_start with
      | Some src ->
          List.rev ({ generated_start; generated_end = i; source_start = src;
                      source_end = src + (i - generated_start) } :: acc)
      | None -> List.rev acc
    else
      match (source_start, origins.(i)) with
      | None, None -> loop (i + 1) None (i + 1) acc
      | None, Some src -> loop i (Some src) (i + 1) acc
      | Some src, Some current when current = src + (i - generated_start) ->
          loop generated_start source_start (i + 1) acc
      | Some src, next ->
          let segment =
            { generated_start; generated_end = i; source_start = src;
              source_end = src + (i - generated_start) }
          in
          (match next with
          | None -> loop (i + 1) None (i + 1) (segment :: acc)
          | Some next_src -> loop i (Some next_src) (i + 1) (segment :: acc))
  in
  loop 0 None 0 []

let rec preprocess_internal ?defines ?include_dirs ?(active = []) ~map_source source
    filename =
  let defines_tbl =
    match defines with
    | Some d -> d
    | None -> Hashtbl.create 32
  in
  let include_dirs_list =
    match include_dirs with
    | Some dirs -> dirs
    | None ->
        let file_dir = dirname_realpath filename in
        [ file_dir; "scaffold"; "."; "../scaffold"; "../../scaffold" ]
  in
  let result_rev = ref [] in
  let lines = String.split_on_char '\n' source in
  let source_offset = ref 0 in
  List.iteri
    (fun idx line ->
      let lineno = idx + 1 in
      let stripped = String.trim line in
      let output =
      if starts_with stripped "#include" then (
        let re = Str.regexp "^#include[ \t]+\"\\([^\"]+\\)\"[ \t]*$" in
        if not (Str.string_match re stripped 0) then
          pp_error "#include は #include \"file\" 形式のみ使える" filename lineno
        else
          let fname = Str.matched_group 1 stripped in
          let rec find_path = function
            | [] -> None
            | d :: rest ->
                let path = Filename.concat d fname in
                if Sys.file_exists path then Some path else find_path rest
          in
          match find_path include_dirs_list with
          | None -> pp_error ("ファイルが見つからない: " ^ fname) filename lineno
          | Some path ->
              let apath = abs_path path in
              if List.mem apath active then
                pp_error ("循環取込み: " ^ fname) filename lineno
              else
                let included_src = Utils.read_file path in
                let included =
                  preprocess_internal ~defines:defines_tbl
                    ~include_dirs:include_dirs_list ~active:(apath :: active)
                    ~map_source:false included_src path
                in
                Some (unmapped included.value))
      else if starts_with stripped "#define" then (
        let re =
          Str.regexp
            "^#define[ \t]+\\([A-Za-z_][A-Za-z0-9_]*\\)\\([ \t]+\\(.*\\)\\)?[ \t]*$"
        in
        if not (Str.string_match re stripped 0) then
          pp_error "#define はオブジェクト形式 #define NAME value のみ使える" filename
            lineno
        else begin
          let name = Str.matched_group 1 stripped in
          let body =
            try String.trim (Str.matched_group 3 stripped) with Not_found -> ""
          in
          if List.mem name keywords then
            pp_error ("キーワードはマクロ名にできない: " ^ name) filename lineno;
          (match Hashtbl.find_opt defines_tbl name with
          | Some old when old <> body ->
              pp_error ("マクロの再定義（本体が異なる）: " ^ name) filename lineno
          | _ -> Hashtbl.replace defines_tbl name body);
          None
        end)
      else if starts_with stripped "#" then
        pp_error ("対応しない前処理指令: " ^ stripped) filename lineno
      else
        let original = mapped_line ~map_source ~source_start:!source_offset line in
        Some (apply_defines defines_tbl original filename lineno)
      in
      Option.iter (fun mapped -> result_rev := mapped :: !result_rev) output;
      source_offset := !source_offset + String.length line;
      if idx < List.length lines - 1 then incr source_offset)
    lines;
  let chunks = List.rev !result_rev in
  let text_buf = Buffer.create (String.length source) in
  let total =
    List.fold_left (fun n chunk -> n + String.length chunk.value) 0 chunks
    + max 0 (List.length chunks - 1)
  in
  let origins = Array.make total None in
  let generated = ref 0 in
  List.iteri
    (fun idx chunk ->
      if idx > 0 then (
        Buffer.add_char text_buf '\n';
        incr generated);
      Buffer.add_string text_buf chunk.value;
      Array.blit chunk.origins 0 origins !generated (Array.length chunk.origins);
      generated := !generated + Array.length chunk.origins)
    chunks;
  { value = Buffer.contents text_buf; origins }

let preprocess_with_map ?defines ?include_dirs source filename =
  let active = if Sys.file_exists filename then [ abs_path filename ] else [] in
  let mapped =
    preprocess_internal ?defines ?include_dirs ~active ~map_source:true source filename
  in
  { text = mapped.value; segments = segments_of_origins mapped.origins }

let preprocess ?defines ?include_dirs source filename =
  (preprocess_with_map ?defines ?include_dirs source filename).text
