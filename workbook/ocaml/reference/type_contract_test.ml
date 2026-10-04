(* 実行値では見えない条件式の型を、構文解析・型付き木まで通して検査する。
   変数の初期化は実行検査の対象であり、この検査はコードを実行しない。 *)
open Refcomp

let prefix = "struct S { int x; }; void nop() {} int main() { char c; char d; int i; char *cp; int *p; int **pp; void *v; struct S *s; "

let cases = Ctype.[
  "char/int", "1 ? c : i", Int;
  "int/char", "0 ? i : c", Int;
  "char/char", "1 ? c : d", Int;
  "int/int", "1 ? i : 3", Int;
  "char-pointer/null", "1 ? cp : 0", Ptr Char;
  "null/char-pointer", "0 ? 0 : cp", Ptr Char;
  "int-pointer/null", "1 ? p : 0", Ptr Int;
  "null/int-pointer", "0 ? 0 : p", Ptr Int;
  "char-pointer/char-pointer", "1 ? cp : cp", Ptr Char;
  "int-pointer/int-pointer", "1 ? p : p", Ptr Int;
  "pointer-pointer/null", "1 ? pp : 0", Ptr (Ptr Int);
  "null/pointer-pointer", "0 ? 0 : pp", Ptr (Ptr Int);
  "struct-pointer/null", "1 ? s : 0", Ptr (Struct "S");
  "null/struct-pointer", "0 ? 0 : s", Ptr (Struct "S");
  "pointer/void-pointer", "1 ? p : v", Ptr Void;
  "void-pointer/pointer", "0 ? v : p", Ptr Void;
  "void-pointer/void-pointer", "1 ? v : v", Ptr Void;
  "void/void", "1 ? nop() : nop()", Void;
]

let () =
  List.iter
    (fun (name, expr, expected) ->
      let source = prefix ^ expr ^ "; return 0; }" in
      let ast = Compile.parse ~filename:"<conditional-type-test>" source in
      let prog = Typing.type_program [source, ast] in
      let main = List.find (fun f -> f.Tast.fn_name = "main") (List.hd prog.units).u_funcs in
      match main.fn_body with
      | { Tast.s_desc = Tast.Expr e; _ } :: _ when e.e_ty = expected -> ()
      | _ -> failwith ("条件式の型が一致しません: " ^ name))
    cases;
  Printf.printf "Conditional type contracts: PASS %d / FAIL 0\n" (List.length cases)
