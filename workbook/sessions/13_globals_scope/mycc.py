"""
コマ 14: コード生成⑫ — グローバル変数・追加演算子（学生用スケルトン）

目標: グローバル変数宣言を .bss に配置し（0 初期化保証）、残りの演算子をサポートする。

追加演算子:  !  &&  ||

実行方法:
    python3 sessions/13_globals_scope/mycc.py input.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '12_struct_malloc_list' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session12_mycc', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen14(prev.Codegen13):
    def __init__(self, struct_defs: dict[str, dict]) -> None:
        super().__init__(struct_defs)
        self._globals: dict[str, str] = {}

    @classmethod
    def parse_file(cls, filename: str) -> tuple[list[Node], dict[str, dict]]:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        source = preprocess(source, filename)
        struct_defs = cls.parse_struct_defs(source)
        tokens = tokenize(source, filename)
        return parse(tokens), struct_defs

    def _is_local(self, name: str) -> bool:
        return name in self._locals

    def lookup_var_ty(self, name: str, line: int) -> str:
        if name in self._locals:
            return self._locals[name][1]
        # TODO: グローバル変数表 self._globals から型を返す。
        raise NotImplementedError("グローバル変数の型 lookup を実装してください")

    def type_of_expr_Var(self, node: Node) -> str:
        return self.lookup_var_ty(node.name, node.line)

    def type_of_expr_Not(self, node: Node) -> str:
        return 'int'

    type_of_expr_And = type_of_expr_Not
    type_of_expr_Or = type_of_expr_Not

    def _type_of_expr(self, node: Node) -> str:
        match node.kind:
            case 'Str':
                return self.type_of_expr_Str(node)
            case 'Num':
                return self.type_of_expr_Num(node)
            case 'Var':
                return self.type_of_expr_Var(node)
            case 'Addr':
                return self.type_of_expr_Addr(node)
            case 'Deref':
                return self.type_of_expr_Deref(node)
            case 'Index':
                return self.type_of_expr_Index(node)
            case 'Member':
                return self.type_of_expr_Member(node)
            case 'Assign':
                return self.type_of_expr_Assign(node)
            case 'Call':
                return self.type_of_expr_Call(node)
            case 'Add':
                return self.type_of_expr_Add(node)
            case 'Sub':
                return self.type_of_expr_Sub(node)
            case 'Mul' | 'Div' | 'Mod' | 'Eq' | 'Ne' | 'Lt' | 'Le':
                return 'int'
            case 'SizeofType':
                return self.type_of_expr_SizeofType(node)
            case 'Neg':
                return self.type_of_expr_Neg(node)
            case 'Not':
                return self.type_of_expr_Not(node)
            case 'And':
                return self.type_of_expr_And(node)
            case 'Or':
                return self.type_of_expr_Or(node)
            case 'PreInc' | 'PreDec':
                return self._type_of_lval(node.operand)
            case 'Cond':
                return self._type_of_expr(node.then)
            case _:
                raise RuntimeError(f'type_of_expr: コマ13で未対応の式です (kind={node.kind!r})')

    def type_of_lval_Var(self, node: Node) -> str:
        return self.lookup_var_ty(node.name, node.line)

    def _type_of_lval(self, node: Node) -> str:
        match node.kind:
            case 'Var':
                return self.type_of_lval_Var(node)
            case 'Deref':
                return self.type_of_lval_Deref(node)
            case 'Index':
                return self.type_of_lval_Index(node)
            case 'Member':
                return self.type_of_lval_Member(node)
            case _:
                raise RuntimeError(f'type_of_lval: コマ13で未対応の式です (kind={node.kind!r})')

    def codegen_lval_Var(self, node: Node) -> None:
        # TODO: ローカル変数なら s0 からのオフセット、グローバル変数なら la でアドレスを作る。
        raise NotImplementedError("codegen_lval_Var のグローバル/ローカル分岐を実装してください")

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                self.codegen_lval_Var(node)
            case 'Deref':
                self.codegen_lval_Deref(node)
            case 'Index':
                self.codegen_lval_Index(node)
            case 'Member':
                self.codegen_lval_Member(node)
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    def codegen_Not(self, node: Node) -> None:
        # TODO: operand を生成し、seqz で論理否定を作る。
        raise NotImplementedError("codegen_Not を実装してください")

    def codegen_And(self, node: Node) -> None:
        # TODO: && は短絡しない（language_spec.md 例外 E3）。
        #       lhs と rhs を必ず両方評価し、それぞれ snez で 0/1 にしてから and を取る。
        raise NotImplementedError("codegen_And を実装してください")

    def codegen_Or(self, node: Node) -> None:
        # TODO: || も短絡しない。lhs と rhs を必ず両方評価し、
        #       or を取ってから snez で 0/1 にする。
        raise NotImplementedError("codegen_Or を実装してください")

    def codegen(self, node: Node) -> None:
        match node.kind:
            case 'Num':
                self.codegen_Num(node)
            case 'Neg':
                self.codegen_Neg(node)
            case 'Add':
                self.codegen_Add(node)
            case 'Sub':
                self.codegen_Sub(node)
            case 'Mul':
                self.codegen_Mul(node)
            case 'Div':
                self.codegen_Div(node)
            case 'Mod':
                self.codegen_Mod(node)
            case 'Var':
                self.codegen_Var(node)
            case 'Assign':
                self.codegen_Assign(node)
            case 'Eq':
                self.codegen_Eq(node)
            case 'Ne':
                self.codegen_Ne(node)
            case 'Lt':
                self.codegen_Lt(node)
            case 'Le':
                self.codegen_Le(node)
            case 'Call':
                self.codegen_Call(node)
            case 'Addr':
                self.codegen_Addr(node)
            case 'Deref':
                self.codegen_Deref(node)
            case 'Index':
                self.codegen_Index(node)
            case 'Str':
                self.codegen_Str(node)
            case 'Member':
                self.codegen_Member(node)
            case 'SizeofType':
                self.codegen_SizeofType(node)
            case 'Not':
                self.codegen_Not(node)
            case 'And':
                self.codegen_And(node)
            case 'Or':
                self.codegen_Or(node)
            case 'Cond':
                self.codegen_Cond(node)
            case 'PreInc':
                self.codegen_PreInc(node)
            case 'PreDec':
                self.codegen_PreDec(node)
            case _:
                raise RuntimeError(f'codegen: コマ13で未対応の式です (kind={node.kind!r})')

    def collect_globals(self, prog: list[Node]) -> None:
        # TODO: トップレベル Decl の名前と型を self._globals に登録する
        #       （初期化子はないので覚えるのは型だけでよい）。
        raise NotImplementedError("collect_globals を実装してください")

    def collect_all_strings(self, prog: list[Node]) -> None:
        # TODO: 各 FuncDef の本体から文字列を収集する。
        raise NotImplementedError("collect_all_strings を実装してください")

    def _collect_strings_binary_expr(self, node: Node) -> None:
        # TODO: 二項演算の node.lhs と node.rhs を collect_strings_expr で走査する。
        raise NotImplementedError("_collect_strings_binary_expr を実装してください")

    def collect_strings_expr_Not(self, node: Node) -> None:
        self.collect_strings_expr(node.operand)

    def collect_strings_expr_And(self, node: Node) -> None:
        self._collect_strings_binary_expr(node)

    collect_strings_expr_Or = collect_strings_expr_And

    def collect_strings_expr(self, node: Node) -> None:
        match node.kind:
            case 'Str':
                self.collect_strings_expr_Str(node)
            case 'Num' | 'Var' | 'SizeofType':
                return
            case 'Neg' | 'Addr' | 'Deref' | 'PreInc' | 'PreDec':
                self.collect_strings_expr_Neg(node)
            case 'Member':
                self.collect_strings_expr_Member(node)
            case 'Not':
                self.collect_strings_expr_Not(node)
            case 'Assign' | 'Add' | 'Sub' | 'Mul' | 'Div' | 'Mod' | 'Eq' | 'Ne' | 'Lt' | 'Le' | 'Index':
                self._collect_strings_binary_expr(node)
            case 'And':
                self.collect_strings_expr_And(node)
            case 'Or':
                self.collect_strings_expr_Or(node)
            case 'Cond':
                self.collect_strings_expr_Cond(node)
            case 'Call':
                self.collect_strings_expr_Call(node)
            case _:
                raise RuntimeError(f'collect_strings_expr: コマ13で未対応の式です (kind={node.kind!r})')

    # emit_data_section() はコマ10 で実装したものを継承して使う（この回では書き直さない）。

    def emit_bss_section(self) -> None:
        # TODO: すべてのグローバル変数を .bss に出力する（.zero で 0 初期化）。
        raise NotImplementedError("emit_bss_section を実装してください")

    def gen_program(self, prog: list[Node]) -> None:
        # TODO: data/bss/text を順に出力し、FuncDef だけ gen_func() する。
        raise NotImplementedError("gen_program を実装してください")


Codegen = Codegen14


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/13_globals_scope/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)

    # TODO: parse_file() で AST を作り、collect_globals/collect_all_strings/gen_program を呼ぶ。
    raise NotImplementedError("コマ13の main 処理を実装してください")


if __name__ == '__main__':
    main()
