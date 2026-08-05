"""
コマ 4: コード生成③ — if/else・比較演算子（学生用スケルトン）

目標: コマ 3 のコード生成器を継承し、比較演算子、複文、if/else、return ラベルを追加する。
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '03_variables' / 'mycc.py'
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
        self._label_n: int = 0
        self._ret_label: str = ''

    def new_label(self) -> str:
        self._label_n += 1
        return f'.L{self._label_n}'

    def _binary(self, lhs: Node, rhs: Node) -> None:
        # 一時値の退避・復元はコマ2の _push_a0 / _pop_into を通す。
        self.codegen(lhs)
        self._push_a0()
        self.codegen(rhs)
        self._pop_into('a1')

    def codegen_Eq(self, node: Node) -> None:
        # TODO: 左右を _binary で評価し、sub + seqz で == の 0/1 を a0 に作る。
        raise NotImplementedError("Eq を実装してください")

    def codegen_Ne(self, node: Node) -> None:
        # TODO: 左右を _binary で評価し、sub + snez で != の 0/1 を a0 に作る。
        raise NotImplementedError("Ne を実装してください")

    def codegen_Lt(self, node: Node) -> None:
        # TODO: 左右を _binary で評価し、slt a0, a1, a0 で < の結果を作る。
        raise NotImplementedError("Lt を実装してください")

    def codegen_Le(self, node: Node) -> None:
        # TODO: b < a を slt で調べ、xori で反転して <= の結果を作る。
        raise NotImplementedError("Le を実装してください")

    def codegen_Cond(self, node: Node) -> None:
        # TODO: 三項演算子 a ? b : c。if/else と同じ分岐を作り、
        #       選ばれた腕の値を a0 に残す（式なので値が残るのがポイント）。
        raise NotImplementedError("Cond（三項演算子）を実装してください")

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
            case 'Cond':
                self.codegen_Cond(node)
            case _:
                raise RuntimeError(f'codegen: コマ4で未対応の式です (kind={node.kind!r})')

    def gen_stmt_Return(self, node: Node) -> None:
        # TODO: return 式を評価した後、ret せず関数共通の _ret_label へジャンプする。
        raise NotImplementedError("Return のジャンプ化を実装してください")

    def gen_stmt_Block(self, node: Node) -> None:
        # TODO: node.stmts を順番に gen_stmt する。
        raise NotImplementedError("Block を実装してください")

    def gen_stmt_If(self, node: Node) -> None:
        # TODO: cond を評価し、beqz と new_label で then/else/end の制御フローを作る。
        # else_ が None の場合は then を抜けた直後に else ラベルだけを置く。
        raise NotImplementedError("If を実装してください")

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
            case _:
                pass

    def _reset_func_state(self, node: Node) -> int:
        # TODO: 親クラスで変数状態を初期化した後、この関数専用の return ラベルを作る。
        # 例: frame_size = super()._reset_func_state(node); self._ret_label = self.new_label()
        raise NotImplementedError("return ラベルの初期化を実装してください")

    def _emit_func_epilogue(self, frame_size: int) -> None:
        # TODO: エピローグ本体の前に _ret_label を出力する。
        # その後の s0/ra 復元は親クラスの hook を呼んでもよい。
        raise NotImplementedError("return ラベル付きエピローグを実装してください")


Codegen = Codegen04


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/04_if_else/mycc.py <source.c>", file=sys.stderr)
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
