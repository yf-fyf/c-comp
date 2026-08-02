"""コマ 11: 文字列リテラルと .data セクション（学生用スケルトン）。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '10b_pointer_arith' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session10b', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen11(prev.Codegen10b):
    def __init__(self) -> None:
        super().__init__()
        self._strings: dict[str, str] = {}
        self._str_label_n: int = 0

    def _intern(self, value: str) -> str:
        # TODO: 同じ文字列を重複登録しないように .LCn ラベルを割り当てる。
        raise NotImplementedError("_intern を実装してください")

    def collect_strings_stmt(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.collect_strings_stmt_Decl(node)
            case 'ExprStmt':
                self.collect_strings_stmt_ExprStmt(node)
            case 'Return':
                self.collect_strings_stmt_Return(node)
            case 'Block':
                self.collect_strings_stmt_Block(node)
            case 'If':
                self.collect_strings_stmt_If(node)
            case 'While':
                self.collect_strings_stmt_While(node)
            case 'For':
                self.collect_strings_stmt_For(node)
            case _:
                pass

    def collect_strings_stmt_Decl(self, node: Node) -> None:
        # TODO: 宣言に初期化子はない（language_spec.md「宣言」節）ので、
        #       走査する式が無い。何もしない。
        raise NotImplementedError("collect_strings_stmt_Decl を実装してください")

    def collect_strings_stmt_ExprStmt(self, node: Node) -> None:
        # TODO: 式文の operand があれば collect_strings_expr する。
        raise NotImplementedError("collect_strings_stmt_ExprStmt を実装してください")

    def collect_strings_stmt_Return(self, node: Node) -> None:
        # TODO: return 式があれば collect_strings_expr する。
        raise NotImplementedError("collect_strings_stmt_Return を実装してください")

    def collect_strings_stmt_Block(self, node: Node) -> None:
        # TODO: ブロック内の各文を再帰的に走査する。
        raise NotImplementedError("collect_strings_stmt_Block を実装してください")

    def collect_strings_stmt_If(self, node: Node) -> None:
        # TODO: cond, then, else_ を走査する。
        raise NotImplementedError("collect_strings_stmt_If を実装してください")

    def collect_strings_stmt_While(self, node: Node) -> None:
        # TODO: cond と body を走査する。
        raise NotImplementedError("collect_strings_stmt_While を実装してください")

    def collect_strings_stmt_For(self, node: Node) -> None:
        # TODO: init, cond, step, body を走査する。
        raise NotImplementedError("collect_strings_stmt_For を実装してください")

    def collect_strings_expr(self, node: Node) -> None:
        match node.kind:
            case 'Str':
                self.collect_strings_expr_Str(node)
            case 'Num' | 'Var':
                pass
            case 'Neg':
                self.collect_strings_expr_Neg(node)
            case 'Addr':
                self.collect_strings_expr_Addr(node)
            case 'Deref':
                self.collect_strings_expr_Deref(node)
            case 'Assign':
                self.collect_strings_expr_Assign(node)
            case 'Add':
                self.collect_strings_expr_Add(node)
            case 'Sub':
                self.collect_strings_expr_Sub(node)
            case 'Mul':
                self.collect_strings_expr_Mul(node)
            case 'Div':
                self.collect_strings_expr_Div(node)
            case 'Mod':
                self.collect_strings_expr_Mod(node)
            case 'Eq':
                self.collect_strings_expr_Eq(node)
            case 'Ne':
                self.collect_strings_expr_Ne(node)
            case 'Lt':
                self.collect_strings_expr_Lt(node)
            case 'Le':
                self.collect_strings_expr_Le(node)
            case 'Index':
                self.collect_strings_expr_Index(node)
            case 'Call':
                self.collect_strings_expr_Call(node)
            case 'PreInc' | 'PreDec':
                self.collect_strings_expr_Neg(node)
            case 'Cond':
                self.collect_strings_expr_Cond(node)
            case _:
                pass

    def collect_strings_expr_Str(self, node: Node) -> None:
        # TODO: node.sval を _intern する。
        raise NotImplementedError("collect_strings_expr_Str を実装してください")

    def collect_strings_expr_Cond(self, node: Node) -> None:
        # TODO: 三項演算子の cond / then / else_ を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Cond を実装してください")

    def collect_strings_expr_Neg(self, node: Node) -> None:
        # TODO: 単項式の operand を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Neg を実装してください")

    def collect_strings_expr_Addr(self, node: Node) -> None:
        # TODO: Addr の operand を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Addr を実装してください")

    def collect_strings_expr_Deref(self, node: Node) -> None:
        # TODO: Deref の operand を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Deref を実装してください")

    def collect_strings_expr_Assign(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Assign を実装してください")

    def collect_strings_expr_Add(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Add を実装してください")

    def collect_strings_expr_Sub(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Sub を実装してください")

    def collect_strings_expr_Mul(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Mul を実装してください")

    def collect_strings_expr_Div(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Div を実装してください")

    def collect_strings_expr_Mod(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Mod を実装してください")

    def collect_strings_expr_Eq(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Eq を実装してください")

    def collect_strings_expr_Ne(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Ne を実装してください")

    def collect_strings_expr_Lt(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Lt を実装してください")

    def collect_strings_expr_Le(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Le を実装してください")

    def collect_strings_expr_Index(self, node: Node) -> None:
        # TODO: lhs と rhs を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Index を実装してください")

    def collect_strings_expr_Call(self, node: Node) -> None:
        # TODO: すべての引数を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Call を実装してください")

    def emit_data_section(self) -> None:
        # TODO: self._strings の各文字列を .data セクションに .byte 列として出力する。
        raise NotImplementedError("emit_data_section を実装してください")

    def type_of_expr_Str(self, node: Node) -> str:
        # TODO: 文字列リテラルの型を返す。
        raise NotImplementedError("type_of_expr_Str を実装してください")

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
            case 'Add':
                return self.type_of_expr_Add(node)
            case 'Sub':
                return self.type_of_expr_Sub(node)
            case 'Assign':
                return self.type_of_expr_Assign(node)
            case 'Call':
                return self.type_of_expr_Call(node)
            case 'PreInc' | 'PreDec':
                return self._type_of_lval(node.operand)
            case 'Cond':
                return self._type_of_expr(node.then)
            case _:
                return 'int'

    def codegen_Str(self, node: Node) -> None:
        # TODO: _intern したラベルを la a0, label でロードする。
        raise NotImplementedError("codegen_Str を実装してください")

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
            case 'Cond':
                self.codegen_Cond(node)
            case 'PreInc':
                self.codegen_PreInc(node)
            case 'PreDec':
                self.codegen_PreDec(node)
            case 'SizeofType':
                self.codegen_SizeofType(node)
            case _:
                raise RuntimeError(f'codegen: コマ11で未対応の式です (kind={node.kind!r})')


Codegen = Codegen11


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/11_strings_printf/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen11()
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
