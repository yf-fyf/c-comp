"""
コマ 13: コード生成⑪ — sizeof（学生用スケルトン）

目標: sizeof(型名) をコンパイル時に評価し、
      アセンブリ上では即値 (li) として埋め込む。

実行方法:
    python3 sessions/13_sizeof_malloc_list/mycc.py input.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '12_struct' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session12_mycc', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen13(prev.Codegen):
    def type_of_expr_SizeofType(self, node: Node) -> str:
        # TODO: sizeof(type) の型は int。
        raise NotImplementedError("type_of_expr_SizeofType を実装してください")

    def type_of_expr_Neg(self, node: Node) -> str:
        return 'int'

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
            case 'PreInc' | 'PreDec':
                return self._type_of_lval(node.operand)
            case 'Cond':
                return self._type_of_expr(node.then)
            case 'Neg':
                return self.type_of_expr_Neg(node)
            case _:
                raise RuntimeError(f'type_of_expr: コマ13で未対応の式です (kind={node.kind!r})')

    def codegen_SizeofType(self, node: Node) -> None:
        # TODO: node.ty_str のサイズを計算し、li a0, <size> を出力する。
        raise NotImplementedError("codegen_SizeofType を実装してください")

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
            case 'Cond':
                self.codegen_Cond(node)
            case 'PreInc':
                self.codegen_PreInc(node)
            case 'PreDec':
                self.codegen_PreDec(node)
            case _:
                raise RuntimeError(f'codegen: コマ13で未対応の式です (kind={node.kind!r})')


Codegen = Codegen13


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/13_sizeof_malloc_list/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()

    source = preprocess(source, filename)
    struct_defs = Codegen13.parse_struct_defs(source)
    tokens = tokenize(source, filename)
    prog = parse(tokens)

    cg = Codegen13(struct_defs)
    for node in prog:
        if node.kind == 'FuncDef':
            cg.collect_strings_stmt(node.body)
    cg.emit_data_section()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
