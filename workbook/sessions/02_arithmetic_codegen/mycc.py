"""
コマ 2: コード生成① — 算術式 → RV64 アセンブリ（学生用スケルトン）

目標: 整数定数・四則演算・剰余・括弧・単項マイナスを含む式を
      RV64 アセンブリに変換する Codegen03 を実装する。

実行方法:
    python3 sessions/02_arithmetic_codegen/mycc.py input.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scaffold'))

from ast_def import Node
from lexer import preprocess, tokenize
from parser import parse


class Codegen03:
    """RISC-V 64 アセンブリを生成するコード生成器。"""

    def __init__(self) -> None:
        self._out: list[str] = []

    def emit(self, line: str) -> None:
        self._out.append(line)

    def output(self) -> str:
        return '\n'.join(self._out) + '\n'

    def codegen(self, node: Node) -> None:
        """式を評価し、結果を a0 レジスタに置く。"""
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
            case _:
                raise RuntimeError(f'codegen: コマ2で未対応の式です (kind={node.kind!r})')

    def _codegen_binary_value(self, node: Node, op: str) -> None:
        # TODO: 左辺を評価してスタックへ退避し、右辺を評価してから a1 op a0 を計算する。
        # 使う命令例: addi sp, sp, -8 / sd a0, 0(sp) / ld a1, 0(sp)
        raise NotImplementedError("二項演算子の共通処理を実装してください")

    def codegen_Num(self, node: Node) -> None:
        # 整数リテラルは li で a0 に直接ロードする。
        self.emit(f'  li a0, {node.val}')

    def codegen_Neg(self, node: Node) -> None:
        # TODO: node.operand を codegen し、neg 命令で a0 の符号を反転する。
        raise NotImplementedError("Neg を実装してください")

    def codegen_Add(self, node: Node) -> None:
        # TODO: _codegen_binary_value(node, 'add') を使って加算を生成する。
        raise NotImplementedError("Add を実装してください")

    def codegen_Sub(self, node: Node) -> None:
        # TODO: _codegen_binary_value(node, 'sub') を使って減算を生成する。
        raise NotImplementedError("Sub を実装してください")

    def codegen_Mul(self, node: Node) -> None:
        # TODO: _codegen_binary_value(node, 'mul') を使って乗算を生成する。
        raise NotImplementedError("Mul を実装してください")

    def codegen_Div(self, node: Node) -> None:
        # TODO: _codegen_binary_value(node, 'div') を使って除算を生成する。
        raise NotImplementedError("Div を実装してください")

    def codegen_Mod(self, node: Node) -> None:
        # TODO: _codegen_binary_value(node, 'rem') を使って剰余を生成する。
        raise NotImplementedError("Mod を実装してください")

    def gen_stmt(self, node: Node) -> None:
        match node.kind:
            case 'Return':
                self.gen_stmt_Return(node)
            case _:
                pass

    def gen_stmt_Return(self, node: Node) -> None:
        # TODO: return 式があれば codegen し、戻り値を a0 に残す。
        raise NotImplementedError("Return を実装してください")

    # ---- gen_func の hook（後続コマで差分実装しやすいように分解） ----

    def _reset_func_state(self, node: Node) -> int:
        return 0

    def _emit_func_prologue(self, name: str, frame_size: int) -> None:
        # TODO: .globl、関数ラベル、ra/s0 保存を含むプロローグを出力する。
        raise NotImplementedError("関数プロローグを実装してください")

    def _emit_func_body(self, body: Node) -> None:
        # TODO: body.stmts を先頭から順に gen_stmt する。
        raise NotImplementedError("関数本体の生成を実装してください")

    def _emit_func_epilogue(self, frame_size: int) -> None:
        # TODO: s0/ra を復元し、sp を戻して ret するエピローグを出力する。
        raise NotImplementedError("関数エピローグを実装してください")

    def gen_func(self, node: Node) -> None:
        if node.kind != 'FuncDef':
            return
        frame_size = self._reset_func_state(node)
        self._emit_func_prologue(node.name, frame_size)
        self._emit_func_body(node.body)
        self._emit_func_epilogue(frame_size)


Codegen = Codegen03


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/02_arithmetic_codegen/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()

    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)

    cg = Codegen03()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
