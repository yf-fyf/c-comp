"""
コマ 4: コード生成② — 変数・代入・シンボルテーブル（学生用スケルトン）

目標: コマ 3 のコード生成器を継承し、ローカル変数の宣言・参照・代入を追加する。
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '03_arithmetic_codegen' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session03', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen04(prev.Codegen03):
    def __init__(self) -> None:
        super().__init__()
        self._locals: dict[str, int] = {}
        self._stack_offset: int = 0

    @staticmethod
    def align_to(n: int, align: int) -> int:
        return ((n + align - 1) // align) * align

    def alloc_local(self, name: str) -> None:
        self._stack_offset += 8
        self._locals[name] = -(16 + self._stack_offset)

    def lookup_var(self, name: str, line: int) -> int:
        if name in self._locals:
            return self._locals[name]
        raise RuntimeError(f"[line {line}] 未定義の変数: '{name}'")

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                self.codegen_lval_Var(node)
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    def codegen_lval_Var(self, node: Node) -> None:
        # TODO: lookup_var で s0 からのオフセットを調べ、変数アドレスを a0 に作る。
        # 例: addi a0, s0, {offset}
        raise NotImplementedError("codegen_lval: Var を実装してください")

    def codegen_Var(self, node: Node) -> None:
        # TODO: 左辺値アドレスを作ってから、ld a0, 0(a0) で値を読み込む。
        raise NotImplementedError("codegen: Var を実装してください")

    def codegen_Assign(self, node: Node) -> None:
        # TODO: 代入先アドレスを退避し、右辺を評価してから sd a0, 0(a1) で保存する。
        raise NotImplementedError("codegen: Assign を実装してください")

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
            case _:
                raise RuntimeError(f'codegen: コマ4で未対応の式です (kind={node.kind!r})')

    def gen_stmt_Decl(self, node: Node) -> None:
        # TODO: 初期化式がある宣言は、一時的な Var/Assign ノードを作って codegen する。
        raise NotImplementedError("gen_stmt: Decl を実装してください")

    def gen_stmt_ExprStmt(self, node: Node) -> None:
        # TODO: 式文の operand が None でなければ codegen する。
        raise NotImplementedError("gen_stmt: ExprStmt を実装してください")

    def gen_stmt(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.gen_stmt_Decl(node)
            case 'ExprStmt':
                self.gen_stmt_ExprStmt(node)
            case 'Return':
                self.gen_stmt_Return(node)
            case _:
                pass

    def collect_decls(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.collect_decls_Decl(node)
            case _:
                pass

    def collect_decls_Decl(self, node: Node) -> None:
        # TODO: 宣言名を alloc_local に渡し、スタック上の保存場所を確保する。
        raise NotImplementedError("collect_decls: Decl を実装してください")

    def _reset_func_state(self, node: Node) -> int:
        # TODO: _locals/_stack_offset を初期化し、関数直下の宣言を収集して frame_size を返す。
        # frame_size は align_to(self._stack_offset, 16) で 16 バイト境界にそろえる。
        raise NotImplementedError("関数ごとの変数状態初期化を実装してください")


Codegen = Codegen04


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/04_variables/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen04()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
