#!/usr/bin/env python3
"""semcc — 32bit int つきコンパイララッパー(完成済み。編集しない)

mycc.py には手を入れず、次を差し込む。

    codegen  いま生成中の式の型をスタックに積む(型コンテキスト)
    emit     narrow.py の narrow(line, ty) を通してから出力する

型コンテキストがあるので、int の算術だけを 32bit 版(addw など)にでき、
ポインタ演算(64bit のまま)を壊さずに済む。

使い方:
    python3 semcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/S2_int32/semcc.py

環境変数:
    SEMCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    SEMCC_PASSES    narrow.py のあるディレクトリ(既定: このファイルの場所)
"""

import importlib.util
import inspect
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"

# 型に応じて幅を変えるノード(算術・シフト・単項マイナス)
ARITH_KINDS = {'Add', 'Sub', 'Mul', 'Div', 'Mod', 'Shl', 'Shr', 'Neg'}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_codegen_class(mod):
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "codegen") and hasattr(obj, "emit"):
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("コード生成クラスが見つからない")
    return best


def patch(cls, nr):
    orig_codegen = cls.codegen
    orig_emit = cls.emit

    def codegen(self, node):
        if node is None:
            return orig_codegen(self, node)
        # 生成するノードごとに「結果の型」を積む。
        # 算術ノード以外は None を積む(= 幅を変えない)。
        # これが重要で、a[i] のアドレス計算(base + i*4)を
        # 外側の int 式の型で narrow してしまうとアドレスが壊れる。
        ty = None
        if node.kind in ARITH_KINDS:
            try:
                ty = self._type_of_expr(node)
            except Exception:
                ty = None
        stack = getattr(self, '_m2_ty_stack', None)
        if stack is None:
            stack = self._m2_ty_stack = []
        stack.append(ty)
        try:
            return orig_codegen(self, node)
        finally:
            stack.pop()

    def emit(self, line):
        stack = getattr(self, '_m2_ty_stack', None)
        ty = stack[-1] if stack else None
        return orig_emit(self, nr.narrow(line, ty))

    cls.codegen = codegen
    cls.emit = emit


def main():
    srcs = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 semcc.py file.c ...", file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("SEMCC_PASSES", DIR))
    compiler = Path(os.environ.get("SEMCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    nr = load_module("semcc_narrow", passes_dir / "narrow.py")
    mycc = load_module("mycc_under_semcc", compiler)
    patch(find_codegen_class(mycc), nr)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
