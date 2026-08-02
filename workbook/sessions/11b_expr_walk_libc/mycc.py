"""コマ 11b: 式の走査と libc 活用（学習者用スケルトン）。"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '11a_strings_data_section' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session11a', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node
preprocess = prev.preprocess
tokenize = prev.tokenize
parse = prev.parse


class Codegen11b(prev.Codegen11a):
    # コマ11a の dispatch は Str / Assign / Call だけを見ていた。ここでは残りの
    # 式もすべて枝に入れ、どの式の下にある文字列リテラルも拾えるようにする。
    # dispatch 自体はここに書いてあるので、実装するのは呼ばれる側だけである。
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

    def collect_strings_expr_Neg(self, node: Node) -> None:
        # TODO: 単項式の operand を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Neg を実装してください")

    def collect_strings_expr_Addr(self, node: Node) -> None:
        # TODO: Addr の operand を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Addr を実装してください")

    def collect_strings_expr_Deref(self, node: Node) -> None:
        # TODO: Deref の operand を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Deref を実装してください")

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

    def collect_strings_expr_Cond(self, node: Node) -> None:
        # TODO: 三項演算子の cond / then / else_ を再帰的に走査する。
        raise NotImplementedError("collect_strings_expr_Cond を実装してください")


Codegen = Codegen11b


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/11b_expr_walk_libc/mycc.py <source.c>", file=sys.stderr)
        sys.exit(1)
    filename = sys.argv[1]
    with open(filename, 'r', encoding='utf-8') as f:
        source = f.read()
    source = preprocess(source, filename)
    tokens = tokenize(source, filename)
    prog = parse(tokens)
    cg = Codegen()
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
