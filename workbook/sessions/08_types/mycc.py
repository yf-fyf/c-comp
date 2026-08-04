"""コマ 8: 型検査の導入（学生用スケルトン）。int / char / ポインタを型サイズで扱う。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '07_lvalue_rvalue' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session07', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen08(prev.Codegen07):
    @classmethod
    def size_of_ty_str(cls, ty_str: str) -> int:
        if ty_str.endswith('*'):
            return 8
        if ty_str == 'char':
            return 1
        if ty_str == 'void':
            return 1
        return 4

    @staticmethod
    def is_ptr_ty_str(ty_str: str) -> bool:
        return ty_str.endswith('*')

    @staticmethod
    def elem_ty_str(ty_str: str) -> str:
        if ty_str.endswith('*'):
            return ty_str[:-1]
        return ty_str

    def __init__(self) -> None:
        super().__init__()
        self._locals: dict[str, tuple[int, str]] = {}

    def alloc_local(self, name: str, ty_str: str = 'int') -> None:
        sz = self.align_to(self.size_of_ty_str(ty_str), 8)
        self._stack_offset += sz
        self._locals[name] = (-(16 + self._stack_offset), ty_str)

    def lookup_var(self, name: str, line: int) -> int:
        if name in self._locals:
            return self._locals[name][0]
        raise RuntimeError(f"[line {line}] 未定義の変数: '{name}'")

    def lookup_local_ty(self, name: str, line: int) -> str:
        if name in self._locals:
            return self._locals[name][1]
        raise RuntimeError(f"[line {line}] 未定義の変数 (type_of): '{name}'")

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
            case 'Assign':
                return self.type_of_expr_Assign(node)
            case 'Call':
                return self.type_of_expr_Call(node)
            case 'Cond':
                return self._type_of_expr(node.then)
            case _:
                return 'int'

    def type_of_expr_Num(self, node: Node) -> str:
        # TODO: 数値リテラルの型を返す。
        raise NotImplementedError("type_of_expr_Num を実装してください")

    def type_of_expr_Var(self, node: Node) -> str:
        # TODO: ローカル変数表から型を取得する。
        raise NotImplementedError("type_of_expr_Var を実装してください")

    def type_of_expr_Addr(self, node: Node) -> str:
        # TODO: 左辺値の型に * を付ける。
        raise NotImplementedError("type_of_expr_Addr を実装してください")

    def type_of_expr_Deref(self, node: Node) -> str:
        # TODO: operand の型から要素型を取り出す。
        raise NotImplementedError("type_of_expr_Deref を実装してください")

    def type_of_expr_Assign(self, node: Node) -> str:
        # TODO: 代入式は左辺値の型を返す。
        raise NotImplementedError("type_of_expr_Assign を実装してください")

    def type_of_expr_Call(self, node: Node) -> str:
        return 'int'

    def _type_of_lval(self, node: Node) -> str:
        match node.kind:
            case 'Var':
                return self.type_of_lval_Var(node)
            case 'Deref':
                return self.type_of_lval_Deref(node)
            case _:
                return 'int'

    def type_of_lval_Var(self, node: Node) -> str:
        # TODO: ローカル変数表から型を取得する。
        raise NotImplementedError("type_of_lval_Var を実装してください")

    def type_of_lval_Deref(self, node: Node) -> str:
        # TODO: *ptr が指す先の型を返す。
        raise NotImplementedError("type_of_lval_Deref を実装してください")

    def _load_ty(self, ty_str: str) -> None:
        # TODO: char/int/pointer のサイズに応じて lb/lw/ld を emit する。
        raise NotImplementedError("_load_ty を実装してください")

    def _store_ty(self, ty_str: str) -> None:
        # TODO: char/int/pointer のサイズに応じて sb/sw/sd を emit する。
        raise NotImplementedError("_store_ty を実装してください")

    def _push_a0(self) -> None:
        self.emit('  addi sp, sp, -8')
        self.emit('  sd a0, 0(sp)')

    def _pop_into(self, reg: str) -> None:
        self.emit(f'  ld {reg}, 0(sp)')
        self.emit('  addi sp, sp, 8')

    def codegen_Var(self, node: Node) -> None:
        # TODO: 変数の型に応じたロードを使う。
        raise NotImplementedError("codegen_Var を実装してください")

    def codegen_Assign(self, node: Node) -> None:
        # TODO: 左辺値の型に応じたストアを使う。
        raise NotImplementedError("codegen_Assign を実装してください")

    def codegen_Deref(self, node: Node) -> None:
        # TODO: ポインタの指す型に応じたロードを使う。
        raise NotImplementedError("codegen_Deref を実装してください")

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
            case _:
                raise RuntimeError(f'codegen: コマ8で未対応の式です (kind={node.kind!r})')

    def collect_decls_Decl(self, node: Node) -> None:
        # TODO: node.ty_str or 'int' を使って型付きで alloc_local する。
        raise NotImplementedError("collect_decls_Decl を実装してください")

    def collect_decls(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.collect_decls_Decl(node)
            case 'Block':
                for stmt in node.stmts:
                    self.collect_decls(stmt)
            case 'If':
                self.collect_decls(node.then)
                if node.else_ is not None:
                    self.collect_decls(node.else_)
            case 'While':
                self.collect_decls(node.body)
            case 'For':
                self.collect_decls(node.body)
            case _:
                pass

    def _alloc_params(self, node: Node) -> None:
        # TODO: パラメータを p.ty_str or 'int' で型付き alloc_local する。
        raise NotImplementedError("_alloc_params（型対応版）を実装してください")

    def _reset_func_state(self, node: Node) -> int:
        self._locals.clear()
        self._stack_offset = 0
        self._ret_label = self.new_label()
        self._break_stack.clear()
        self._continue_stack.clear()
        self._alloc_params(node)
        self.collect_decls(node.body)
        self._current_params = node.params
        return self.align_to(self._stack_offset, 16)

    def _emit_func_prologue(self, name: str, frame_size: int) -> None:
        self.emit(f'  .globl {name}')
        self.emit(f'{name}:')
        self.emit(f'  addi sp, sp, -{frame_size + 16}')
        self.emit(f'  sd ra, {frame_size + 8}(sp)')
        self.emit(f'  sd s0, {frame_size}(sp)')
        self.emit(f'  addi s0, sp, {frame_size + 16}')
        # TODO: パラメータ保存も型サイズを意識して実装する。
        raise NotImplementedError("パラメータのスタック退避（型対応版）を実装してください")


Codegen = Codegen08


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/08_types/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen08()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
