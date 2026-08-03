"""コマ 10: ポインタ演算とスケーリング（学生用スケルトン）。連続領域は malloc + sizeof で確保する。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '08_types' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session08', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen10(prev.Codegen09):
    def _type_of_expr(self, node: Node) -> str:
        match node.kind:
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

    def type_of_expr_Index(self, node: Node) -> str:
        # TODO: a[i] の結果型を左辺値型として求める。
        raise NotImplementedError("type_of_expr_Index を実装してください")

    def type_of_expr_Add(self, node: Node) -> str:
        # TODO: ポインタ + 整数ならポインタ型、それ以外は int。
        raise NotImplementedError("type_of_expr_Add を実装してください")

    def type_of_expr_Sub(self, node: Node) -> str:
        # TODO: ポインタ - 整数ならポインタ型、それ以外は int。
        raise NotImplementedError("type_of_expr_Sub を実装してください")

    def _type_of_lval(self, node: Node) -> str:
        match node.kind:
            case 'Var':
                return self.type_of_lval_Var(node)
            case 'Deref':
                return self.type_of_lval_Deref(node)
            case 'Index':
                return self.type_of_lval_Index(node)
            case _:
                return 'int'

    def type_of_lval_Index(self, node: Node) -> str:
        # TODO: ポインタの要素型（指し先型）を返す。
        raise NotImplementedError("type_of_lval_Index を実装してください")

    def _scale_index(self, elem_ty: str) -> None:
        # TODO: 添字 a0 に要素サイズを掛ける。
        raise NotImplementedError("_scale_index を実装してください")

    def codegen_lval_Index(self, node: Node) -> None:
        # TODO: base + index * elem_size のアドレスを a0 に作る。
        raise NotImplementedError("codegen_lval_Index を実装してください")

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                self.codegen_lval_Var(node)
            case 'Deref':
                self.codegen_lval_Deref(node)
            case 'Index':
                self.codegen_lval_Index(node)
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    def codegen_Index(self, node: Node) -> None:
        # TODO: Index の左辺値アドレスを作り、型付きロードする。
        raise NotImplementedError("codegen_Index を実装してください")

    def codegen_Add(self, node: Node) -> None:
        # TODO: ポインタ + 整数のとき整数側を要素サイズでスケールする。
        raise NotImplementedError("codegen_Add を実装してください")

    def codegen_Sub(self, node: Node) -> None:
        # TODO: ポインタ - 整数のとき整数側を要素サイズでスケールする。
        raise NotImplementedError("codegen_Sub を実装してください")

    def codegen_SizeofType(self, node: Node) -> None:
        # TODO: sizeof(型名) は翻訳時定数。size_of_ty_str の値を li で a0 に置く。
        raise NotImplementedError("codegen_SizeofType を実装してください")

    def codegen_PreInc(self, node: Node) -> None:
        # TODO: コマ 6 の前置 ++ を型対応にする。ポインタは指し先サイズ、
        #       int/char は 1 を加算し、_load_ty/_store_ty で読み書きする。
        raise NotImplementedError("codegen_PreInc（型対応版）を実装してください")

    def codegen_PreDec(self, node: Node) -> None:
        # TODO: PreInc と同様に、型に応じた幅で減算する。
        raise NotImplementedError("codegen_PreDec（型対応版）を実装してください")

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
            case 'Cond':
                self.codegen_Cond(node)
            case 'PreInc':
                self.codegen_PreInc(node)
            case 'PreDec':
                self.codegen_PreDec(node)
            case 'SizeofType':
                self.codegen_SizeofType(node)
            case _:
                raise RuntimeError(f'codegen: コマ9で未対応の式です (kind={node.kind!r})')


Codegen = Codegen10


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/09_pointer_arith/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen10()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
