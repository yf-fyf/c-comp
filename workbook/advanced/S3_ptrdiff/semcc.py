#!/usr/bin/env python3
"""semcc — ポインタ差つきコンパイララッパー(完成済み。編集しない)

mycc.py には手を入れず、次を差し込む。

    codegen        'Sub' がポインタ同士なら ptrdiff.py の実装に回す
    _type_of_expr  ポインタ同士の引き算の型を int にする
    size_of_ty_str クラスから呼べるようにする(ptrdiff.py 用)

使い方:
    python3 semcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/S3_ptrdiff/semcc.py

環境変数:
    SEMCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    SEMCC_PASSES    ptrdiff.py のあるディレクトリ(既定: このファイルの場所)
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


def patch(cls, mycc, pd):
    orig_codegen = cls.codegen
    orig_type_of_expr = cls._type_of_expr

    # ptrdiff.py から型サイズを引けるようにする
    cls.size_of_ty_str = staticmethod(mycc.size_of_ty_str)

    def codegen(self, node):
        if node is not None and pd.is_ptr_diff(self, node):
            return pd.gen_ptr_diff(self, node)
        return orig_codegen(self, node)

    def _type_of_expr(self, node):
        # p - q の型は int(ポインタではない)
        if node is not None and node.kind == 'Sub':
            lt = orig_type_of_expr(self, node.lhs)
            rt = orig_type_of_expr(self, node.rhs)
            if lt.endswith('*') and rt.endswith('*'):
                return 'int'
        return orig_type_of_expr(self, node)

    cls.codegen = codegen
    cls._type_of_expr = _type_of_expr


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
    pd = load_module("semcc_ptrdiff", passes_dir / "ptrdiff.py")
    mycc = load_module("mycc_under_semcc", compiler)
    patch(find_codegen_class(mycc), mycc, pd)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
