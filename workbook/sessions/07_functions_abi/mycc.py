"""
コマ 7: 再帰的な変数宣言収集（学生用スケルトン）

目標: コマ 6 のコード生成器を継承し、ブロックや制御構文の内側にある宣言も収集する。
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '06_loops' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session06', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen07(prev.Codegen06):
    def collect_decls(self, node: Node) -> None:
        match node.kind:
            case 'Decl':
                self.collect_decls_Decl(node)
            case 'Block':
                self.collect_decls_Block(node)
            case 'If':
                self.collect_decls_If(node)
            case 'While':
                self.collect_decls_While(node)
            case 'For':
                self.collect_decls_For(node)
            case _:
                pass

    def collect_decls_Block(self, node: Node) -> None:
        # TODO: ブロック内の各 stmt を collect_decls で再帰的に調べる。
        raise NotImplementedError("collect_decls: Block を実装してください")

    def collect_decls_If(self, node: Node) -> None:
        # TODO: then 側を収集し、else_ があれば else 側も収集する。
        raise NotImplementedError("collect_decls: If を実装してください")

    def collect_decls_While(self, node: Node) -> None:
        # TODO: while 本体 node.body の中にある宣言を再帰的に収集する。
        raise NotImplementedError("collect_decls: While を実装してください")

    def collect_decls_For(self, node: Node) -> None:
        # TODO: for 本体 node.body の中にある宣言を再帰的に収集する。
        raise NotImplementedError("collect_decls: For を実装してください")

    def _reset_func_state(self, node: Node) -> int:
        # TODO: 変数表・スタックサイズ・return ラベル・ループスタックを関数ごとに初期化する。
        # その後、node.body 全体を collect_decls し、align_to した frame_size を返す。
        raise NotImplementedError("再帰的な宣言収集を使う関数初期化を実装してください")

    def _emit_func_body(self, body: Node) -> None:
        # TODO: 関数本体を stmt の列としてばらさず、Block ノードとして gen_stmt に渡す。
        raise NotImplementedError("Block としての関数本体生成を実装してください")


Codegen = Codegen07


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/07_functions_abi/mycc.py <source.c>", file=sys.stderr)
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
