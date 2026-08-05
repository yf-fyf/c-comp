"""コマ 7: lvalue / rvalue と & / *（学生用スケルトン）。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '06_functions_recursion' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session06', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen07(prev.Codegen06):
    def codegen_lval_Deref(self, node: Node) -> None:
        # TODO: *ptr の左辺値は ptr の値そのもの。operand を rvalue として評価する。
        raise NotImplementedError("codegen_lval_Deref を実装してください")

    def codegen_lval(self, node: Node) -> None:
        match node.kind:
            case 'Var':
                self.codegen_lval_Var(node)
            case 'Deref':
                self.codegen_lval_Deref(node)
            case _:
                raise RuntimeError(f"lvalue でない式です (kind={node.kind!r})")

    def codegen_Addr(self, node: Node) -> None:
        # TODO: &expr は expr の左辺値アドレスを a0 に入れる。
        raise NotImplementedError("codegen_Addr を実装してください")

    def codegen_Deref(self, node: Node) -> None:
        # TODO: *ptr は ptr を評価し、そのアドレスから値をロードする。
        raise NotImplementedError("codegen_Deref を実装してください")

    def codegen(self, node: Node) -> None:
        # コマ7で増えるのは Addr と Deref だけ。それ以外はコマ6までのディスパッチへ委譲する。
        # （ここで全 case を並べ直すと、コマ4の Cond やコマ5の PreInc/PreDec が落ちる）
        match node.kind:
            case 'Addr':
                self.codegen_Addr(node)
            case 'Deref':
                self.codegen_Deref(node)
            case _:
                super().codegen(node)


Codegen = Codegen07


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/07_lvalue_rvalue/mycc.py <source.c>", file=sys.stderr)
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
