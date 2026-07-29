"""
コマ 14: コード生成⑫ — グローバル変数・追加演算子（学生用スケルトン）

目標: グローバル変数宣言を .data/.bss に配置し、全ての単項/二項演算子をサポートする。

追加演算子:  !  ~  &&  ||  &  |  ^  <<  >>

実行方法:
    python3 sessions/14_globals_scope/mycc.py input.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '13_sizeof_malloc_list' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session13_mycc', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
Parser = prev.Parser


class Codegen14(prev.Codegen13):
    def __init__(self, struct_defs: dict[str, dict]) -> None:
        super().__init__(struct_defs)
        self._globals: dict[str, tuple[str, int | None]] = {}

    @classmethod
    def parse_file(cls, filename: str) -> tuple[list[Node], dict[str, dict]]:
        with open(filename, 'r', encoding='utf-8') as f:
            source = f.read()
        source = preprocess(source, filename)
        typedef_names = cls.register_typedef_names(source)
        struct_defs = cls.parse_struct_defs(source)
        tokens = tokenize(source, filename)
        p = Parser(tokens)
        p.typedef_names.update(typedef_names)
        return p.parse_program(), struct_defs

    def _is_local(self, name: str) -> bool:
        return name in self._locals

    def _const_int_value(self, node: Node) -> int | None:
        # TODO: Num と単項 - だけを定数初期化子として評価する。
        raise NotImplementedError("_const_int_value を実装してください")

    def lookup_var_ty(self, name: str, line: int) -> str:
        if name in self._locals:
            return self._locals[name][1]
        # TODO: グローバル変数表 self._globals から型を返す。
        raise NotImplementedError("グローバル変数の型 lookup を実装してください")

    def type_of_expr_Var(self, node: Node) -> str:
        return self.lookup_var_ty(node.name, node.line)

    def type_of_expr_Not(self, node: Node) -> str:
        return 'int'

    type_of_expr_BitNot = type_of_expr_Not
    type_of_expr_And = type_of_expr_Not
    type_of_expr_Or = type_of_expr_Not
    type_of_expr_BitAnd = type_of_expr_Not
    type_of_expr_BitOr = type_of_expr_Not
    type_of_expr_BitXor = type_of_expr_Not
    type_of_expr_Shl = type_of_expr_Not
    type_of_expr_Shr = type_of_expr_Not

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
            case 'SizeofExpr':
                return self.type_of_expr_SizeofExpr(node)
            case 'Neg':
                return self.type_of_expr_Neg(node)
            case 'Not':
                return self.type_of_expr_Not(node)
            case 'BitNot':
                return self.type_of_expr_BitNot(node)
            case 'And':
                return self.type_of_expr_And(node)
            case 'Or':
                return self.type_of_expr_Or(node)
            case 'BitAnd':
                return self.type_of_expr_BitAnd(node)
            case 'BitOr':
                return self.type_of_expr_BitOr(node)
            case 'BitXor':
                return self.type_of_expr_BitXor(node)
            case 'Shl':
                return self.type_of_expr_Shl(node)
            case 'Shr':
                return self.type_of_expr_Shr(node)
            case _:
                raise RuntimeError(f'type_of_expr: コマ14で未対応の式です (kind={node.kind!r})')

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
                raise RuntimeError(f'type_of_lval: コマ14で未対応の式です (kind={node.kind!r})')

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

    def codegen_BitNot(self, node: Node) -> None:
        # TODO: operand を生成し、not でビット反転する。
        raise NotImplementedError("codegen_BitNot を実装してください")

    def codegen_And(self, node: Node) -> None:
        # TODO: lhs/rhs を評価し、0/1 化して and する。
        raise NotImplementedError("codegen_And を実装してください")

    def codegen_Or(self, node: Node) -> None:
        # TODO: lhs/rhs を評価し、or 後に 0/1 化する。
        raise NotImplementedError("codegen_Or を実装してください")

    def codegen_BitAnd(self, node: Node) -> None:
        # TODO: ビット AND を生成する。
        raise NotImplementedError("codegen_BitAnd を実装してください")

    def codegen_BitOr(self, node: Node) -> None:
        # TODO: ビット OR を生成する。
        raise NotImplementedError("codegen_BitOr を実装してください")

    def codegen_BitXor(self, node: Node) -> None:
        # TODO: ビット XOR を生成する。
        raise NotImplementedError("codegen_BitXor を実装してください")

    def codegen_Shl(self, node: Node) -> None:
        # TODO: 左シフトを生成する。
        raise NotImplementedError("codegen_Shl を実装してください")

    def codegen_Shr(self, node: Node) -> None:
        # TODO: 右シフトを生成する。
        raise NotImplementedError("codegen_Shr を実装してください")

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
            case 'SizeofExpr':
                self.codegen_SizeofExpr(node)
            case 'Not':
                self.codegen_Not(node)
            case 'BitNot':
                self.codegen_BitNot(node)
            case 'And':
                self.codegen_And(node)
            case 'Or':
                self.codegen_Or(node)
            case 'BitAnd':
                self.codegen_BitAnd(node)
            case 'BitOr':
                self.codegen_BitOr(node)
            case 'BitXor':
                self.codegen_BitXor(node)
            case 'Shl':
                self.codegen_Shl(node)
            case 'Shr':
                self.codegen_Shr(node)
            case _:
                raise RuntimeError(f'codegen: コマ14で未対応の式です (kind={node.kind!r})')

    def collect_globals(self, prog: list[Node]) -> None:
        # TODO: トップレベル Decl を self._globals に登録する。
        raise NotImplementedError("collect_globals を実装してください")

    def collect_all_strings(self, prog: list[Node]) -> None:
        # TODO: 関数本体とグローバル初期化式の文字列を収集する。
        raise NotImplementedError("collect_all_strings を実装してください")

    def collect_strings_expr_Not(self, node: Node) -> None:
        self.collect_strings_expr(node.operand)

    collect_strings_expr_BitNot = collect_strings_expr_Not
    collect_strings_expr_SizeofExpr = collect_strings_expr_Not

    def collect_strings_expr_And(self, node: Node) -> None:
        self._collect_strings_binary_expr(node)

    collect_strings_expr_Or = collect_strings_expr_And
    collect_strings_expr_BitAnd = collect_strings_expr_And
    collect_strings_expr_BitOr = collect_strings_expr_And
    collect_strings_expr_BitXor = collect_strings_expr_And
    collect_strings_expr_Shl = collect_strings_expr_And
    collect_strings_expr_Shr = collect_strings_expr_And

    def collect_strings_expr(self, node: Node) -> None:
        match node.kind:
            case 'Str':
                self.collect_strings_expr_Str(node)
            case 'Num' | 'Var' | 'SizeofType':
                return
            case 'Neg' | 'Addr' | 'Deref' | 'Member':
                self.collect_strings_expr_Neg(node)
            case 'Not':
                self.collect_strings_expr_Not(node)
            case 'BitNot':
                self.collect_strings_expr_BitNot(node)
            case 'SizeofExpr':
                self.collect_strings_expr_SizeofExpr(node)
            case 'Assign' | 'Add' | 'Sub' | 'Mul' | 'Div' | 'Mod' | 'Eq' | 'Ne' | 'Lt' | 'Le' | 'Index':
                self._collect_strings_binary_expr(node)
            case 'And':
                self.collect_strings_expr_And(node)
            case 'Or':
                self.collect_strings_expr_Or(node)
            case 'BitAnd':
                self.collect_strings_expr_BitAnd(node)
            case 'BitOr':
                self.collect_strings_expr_BitOr(node)
            case 'BitXor':
                self.collect_strings_expr_BitXor(node)
            case 'Shl':
                self.collect_strings_expr_Shl(node)
            case 'Shr':
                self.collect_strings_expr_Shr(node)
            case 'Call':
                self.collect_strings_expr_Call(node)
            case _:
                raise RuntimeError(f'collect_strings_expr: コマ14で未対応の式です (kind={node.kind!r})')

    def emit_data_section(self) -> None:
        # TODO: 文字列リテラルと初期値ありグローバルを .data に出力する。
        raise NotImplementedError("emit_data_section を実装してください")

    def emit_bss_section(self) -> None:
        # TODO: 初期値なしグローバルを .bss に出力する。
        raise NotImplementedError("emit_bss_section を実装してください")

    def gen_program(self, prog: list[Node]) -> None:
        # TODO: data/bss/text を順に出力し、FuncDef だけ gen_func() する。
        raise NotImplementedError("gen_program を実装してください")


Codegen = Codegen14


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/14_globals_scope/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)

    # TODO: parse_file() で AST を作り、collect_globals/collect_all_strings/gen_program を呼ぶ。
    raise NotImplementedError("コマ14の main 処理を実装してください")


if __name__ == '__main__':
    main()
