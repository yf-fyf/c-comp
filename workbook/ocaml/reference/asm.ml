(*
   出力するアセンブリの表現。

   コード生成側が組み立てるのは「ニーモニックを埋め込んだ文字列」ではなく、
   この型の値である。文字列にするのは print_line だけなので、
   命令の綴りや書式を直したいときに触る場所が 1 箇所で済む。
*)

(* ── レジスタ ──
   この教材のコード生成が触るのは、引数・戻り値用の a0–a7 と、
   スタックポインタ sp・フレームポインタ s0・戻り番地 ra だけである。 *)

type reg = A0 | A1 | A2 | A3 | A4 | A5 | A6 | A7 | Sp | S0 | Ra

let arg_regs = [| A0; A1; A2; A3; A4; A5; A6; A7 |]

(* 第 i 引数のレジスタ。呼び出し規約で使えるのは 8 本まで。 *)
let arg_reg i = arg_regs.(i)

let reg_name = function
  | A0 -> "a0"
  | A1 -> "a1"
  | A2 -> "a2"
  | A3 -> "a3"
  | A4 -> "a4"
  | A5 -> "a5"
  | A6 -> "a6"
  | A7 -> "a7"
  | Sp -> "sp"
  | S0 -> "s0"
  | Ra -> "ra"

(* ── ラベルと名前 ──
   .L は制御構造の飛び先、.LC は文字列リテラルの置き場。
   関数名・グローバル変数名はソース由来の名前なので別に扱う。 *)

type label = L of int | Lc of int

let label_name = function
  | L n -> Printf.sprintf ".L%d" n
  | Lc n -> Printf.sprintf ".LC%d" n

(* la の対象やラベル定義の左辺になれるもの *)
type target = Label of label | Symbol of string

let target_name = function Label l -> label_name l | Symbol s -> s

(* ── 番地 ──
   この教材が出すメモリ参照は、すべて「ベースレジスタ + 変位」である。 *)

type addr = { base : reg; disp : int }

let at base disp = { base; disp }

let addr_string { base; disp } = Printf.sprintf "%d(%s)" disp (reg_name base)

(* ── 命令 ── *)

type binop = Add | Sub | Mul | Div | Rem | And | Or | Slt

let binop_mnemonic = function
  | Add -> "add"
  | Sub -> "sub"
  | Mul -> "mul"
  | Div -> "div"
  | Rem -> "rem"
  | And -> "and"
  | Or -> "or"
  | Slt -> "slt"

type unop = Neg | Seqz | Snez

let unop_mnemonic = function Neg -> "neg" | Seqz -> "seqz" | Snez -> "snez"

(* Load / Store の int はアクセス幅（バイト）。1 → lb/sb、4 → lw/sw、8 → ld/sd。 *)
type insn =
  | Li of reg * int
  | La of reg * target
  | Load of int * reg * addr
  | Store of int * reg * addr
  | Addi of reg * reg * int
  | Xori of reg * reg * int
  | Binop of binop * reg * reg * reg
  | Unop of unop * reg * reg
  | Beqz of reg * label
  | J of label
  | Call of string
  | Ret

let load_mnemonic = function 1 -> "lb" | 4 -> "lw" | _ -> "ld"
let store_mnemonic = function 1 -> "sb" | 4 -> "sw" | _ -> "sd"

(* ── ディレクティブ ── *)

type directive =
  | Text
  | Data
  | Bss
  | Globl of string
  | Byte of int
  | Zero of int

(* ── 出力の 1 行 ── *)

type line =
  | Insn of insn
  | Def of target (* "main:" や ".L3:" のようなラベル定義 *)
  | Directive of directive

(* ── 印字 ──
   命令とディレクティブは 2 桁字下げ、ラベル定義だけ行頭から書く。 *)

let insn_string = function
  | Li (rd, imm) -> Printf.sprintf "li %s, %d" (reg_name rd) imm
  | La (rd, t) -> Printf.sprintf "la %s, %s" (reg_name rd) (target_name t)
  | Load (size, rd, a) ->
      Printf.sprintf "%s %s, %s" (load_mnemonic size) (reg_name rd) (addr_string a)
  | Store (size, rs, a) ->
      Printf.sprintf "%s %s, %s" (store_mnemonic size) (reg_name rs) (addr_string a)
  | Addi (rd, rs, imm) -> Printf.sprintf "addi %s, %s, %d" (reg_name rd) (reg_name rs) imm
  | Xori (rd, rs, imm) -> Printf.sprintf "xori %s, %s, %d" (reg_name rd) (reg_name rs) imm
  | Binop (op, rd, rs1, rs2) ->
      Printf.sprintf "%s %s, %s, %s" (binop_mnemonic op) (reg_name rd) (reg_name rs1)
        (reg_name rs2)
  | Unop (op, rd, rs) -> Printf.sprintf "%s %s, %s" (unop_mnemonic op) (reg_name rd) (reg_name rs)
  | Beqz (rs, l) -> Printf.sprintf "beqz %s, %s" (reg_name rs) (label_name l)
  | J l -> "j " ^ label_name l
  | Call name -> "call " ^ name
  | Ret -> "ret"

let directive_string = function
  | Text -> ".text"
  | Data -> ".data"
  | Bss -> ".bss"
  | Globl name -> ".globl " ^ name
  | Byte n -> Printf.sprintf ".byte %d" n
  | Zero n -> Printf.sprintf ".zero %d" n

let print_line = function
  | Insn i -> "  " ^ insn_string i
  | Directive d -> "  " ^ directive_string d
  | Def t -> target_name t ^ ":"

(* ── 組み立て用の短縮形 ──
   コード生成側は `Asm.(addi a0 s0 offset)` のように局所 open で使う。
   Ast_def の Add / Sub / Neg などと綴りがぶつかるので、
   コード生成側でモジュール全体を open してはいけない。 *)

let a0 = A0
let a1 = A1
let sp = Sp
let s0 = S0
let ra = Ra
let li rd imm = Insn (Li (rd, imm))
let la rd t = Insn (La (rd, t))
let load size rd a = Insn (Load (size, rd, a))
let store size rs a = Insn (Store (size, rs, a))
let addi rd rs imm = Insn (Addi (rd, rs, imm))
let xori rd rs imm = Insn (Xori (rd, rs, imm))
let binop op rd rs1 rs2 = Insn (Binop (op, rd, rs1, rs2))
let unop op rd rs = Insn (Unop (op, rd, rs))
let beqz rs l = Insn (Beqz (rs, l))
let j l = Insn (J l)
let call name = Insn (Call name)
let ret = Insn Ret
let deflabel l = Def (Label l)
let defsym name = Def (Symbol name)
let text = Directive Text
let data = Directive Data
let bss = Directive Bss
let globl name = Directive (Globl name)
let byte n = Directive (Byte n)
let zero n = Directive (Zero n)
