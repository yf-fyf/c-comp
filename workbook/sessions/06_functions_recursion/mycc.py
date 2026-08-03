"""コマ 7: 関数引数・関数呼び出し（学生用スケルトン）。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '05_loops' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session05', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen07(prev.Codegen):
    def codegen_lval_Var(self, node: Node) -> None:
        offset = self.lookup_var(node.name, node.line)
        self.emit(f'  addi a0, s0, {offset}')

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                self.codegen_lval_Var(node)
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    def codegen_Num(self, node: Node) -> None:
        self.emit(f'  li a0, {node.val}')

    def codegen_Var(self, node: Node) -> None:
        self.codegen_lval(node)
        self.emit('  ld a0, 0(a0)')

    def codegen_Assign(self, node: Node) -> None:
        self.codegen_lval(node.lhs)
        self.emit('  addi sp, sp, -8')
        self.emit('  sd a0, 0(sp)')
        self.codegen(node.rhs)
        self.emit('  ld a1, 0(sp)')
        self.emit('  addi sp, sp, 8')
        self.emit('  sd a0, 0(a1)')

    def codegen_Neg(self, node: Node) -> None:
        self.codegen(node.operand)
        self.emit('  neg a0, a0')

    def _binary_value(self, lhs: Node, rhs: Node) -> None:
        self.codegen(lhs)
        self.emit('  addi sp, sp, -8')
        self.emit('  sd a0, 0(sp)')
        self.codegen(rhs)
        self.emit('  ld a1, 0(sp)')
        self.emit('  addi sp, sp, 8')

    def codegen_Add(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  add a0, a1, a0')

    def codegen_Sub(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  sub a0, a1, a0')

    def codegen_Mul(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  mul a0, a1, a0')

    def codegen_Div(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  div a0, a1, a0')

    def codegen_Mod(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  rem a0, a1, a0')

    def codegen_Eq(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  sub a0, a1, a0')
        self.emit('  seqz a0, a0')

    def codegen_Ne(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  sub a0, a1, a0')
        self.emit('  snez a0, a0')

    def codegen_Lt(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  slt a0, a1, a0')

    def codegen_Le(self, node: Node) -> None:
        self._binary_value(node.lhs, node.rhs)
        self.emit('  slt a0, a0, a1')
        self.emit('  xori a0, a0, 1')

    def codegen_Call(self, node: Node) -> None:
        # TODO: 関数名 node.name と引数 node.args を _gen_call へ渡す。
        raise NotImplementedError("codegen_Call を実装してください")

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
            case _:
                raise RuntimeError(f'codegen: コマ6で未対応の式です (kind={node.kind!r})')

    def _gen_call(self, name: str, args: list[Node]) -> None:
        # TODO: 引数を評価して ABI の a0-a7 に並べ、call {name} を emit する。
        raise NotImplementedError("_gen_call を実装してください")

    def _alloc_params(self, node: Node) -> None:
        # TODO: node.params の各パラメータを alloc_local してスロットを確保する。
        raise NotImplementedError("_alloc_params を実装してください")

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
        # TODO: a0-a7 のパラメータ値を対応するローカル変数スロットへ保存する。
        raise NotImplementedError("パラメータのスタック退避を実装してください")

    def gen_func(self, node: Node) -> None:
        if node.kind != 'FuncDef':
            return
        frame_size = self._reset_func_state(node)
        self._emit_func_prologue(node.name, frame_size)
        self.gen_stmt(node.body)
        self.emit(f'{self._ret_label}:')
        self.emit(f'  ld s0, {frame_size}(sp)')
        self.emit(f'  ld ra, {frame_size + 8}(sp)')
        self.emit(f'  addi sp, sp, {frame_size + 16}')
        self.emit('  ret')


Codegen = Codegen07


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/06_functions_recursion/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen07()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
