"""
コマ 5: 制御構文② — while / for / break / continue（学生用スケルトン）

目標: コマ 5 のコード生成器を継承し、ループと break/continue のジャンプ先管理を追加する。
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '04_if_else' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session04', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen06(prev.Codegen05):
    def __init__(self) -> None:
        super().__init__()
        self._break_stack: list[str] = []
        self._continue_stack: list[str] = []

    def codegen_PreInc(self, node: Node) -> None:
        # TODO: 前置 ++。codegen_lval で左辺値のアドレスを 1 回だけ求め、
        #       ld → +1 → sd で書き戻し、増やした後の値を a0 に残す。
        raise NotImplementedError("PreInc（前置 ++）を実装してください")

    def codegen_PreDec(self, node: Node) -> None:
        # TODO: 前置 --。PreInc と同様に -1 する。
        raise NotImplementedError("PreDec（前置 --）を実装してください")

    def codegen(self, node: Node) -> None:
        match node.kind:
            case 'PreInc':
                self.codegen_PreInc(node)
            case 'PreDec':
                self.codegen_PreDec(node)
            case _:
                super().codegen(node)

    def gen_stmt_While(self, node: Node) -> None:
        # TODO: 条件ラベルと終了ラベルを作り、cond が 0 なら終了へ分岐するループを生成する。
        # break 用に終了ラベル、continue 用に条件ラベルをそれぞれスタックへ積む。
        raise NotImplementedError("While を実装してください")

    def gen_stmt_For(self, node: Node) -> None:
        # TODO: init、cond、body、step の順に実行される for ループをラベルで生成する。
        # continue は step ラベルへ、break は終了ラベルへ飛ぶようにする。
        raise NotImplementedError("For を実装してください")

    def gen_stmt_Break(self, node: Node) -> None:
        # TODO: _break_stack の末尾にある最内ループの終了ラベルへジャンプする。
        raise NotImplementedError("Break を実装してください")

    def gen_stmt_Continue(self, node: Node) -> None:
        # TODO: _continue_stack の末尾にある最内ループの継続ラベルへジャンプする。
        raise NotImplementedError("Continue を実装してください")

    def gen_stmt(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.gen_stmt_Decl(node)
            case 'ExprStmt':
                self.gen_stmt_ExprStmt(node)
            case 'Return':
                self.gen_stmt_Return(node)
            case 'Block':
                self.gen_stmt_Block(node)
            case 'If':
                self.gen_stmt_If(node)
            case 'While':
                self.gen_stmt_While(node)
            case 'For':
                self.gen_stmt_For(node)
            case 'Break':
                self.gen_stmt_Break(node)
            case 'Continue':
                self.gen_stmt_Continue(node)
            case _:
                pass

    def _reset_func_state(self, node: Node) -> int:
        # TODO: 関数ごとに break/continue スタックを空にしてから、親クラスの初期化へ進む。
        raise NotImplementedError("ループ状態の初期化を実装してください")


Codegen = Codegen06


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/05_loops/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen06()
    cg.emit('  .text')
    for node in prog:
        cg.gen_func(node)
    sys.stdout.write(cg.output())


if __name__ == '__main__':
    main()
