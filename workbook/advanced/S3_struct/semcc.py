#!/usr/bin/env python3
"""semcc — 構造体コピーつきコンパイララッパー(完成済み。編集しない)

mycc.py には手を入れず、コード生成器の codegen を包んで
'Assign' が構造体同士なら structcopy.py の実装に回す。

使い方:
    python3 semcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/S3_struct/semcc.py

環境変数:
    SEMCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    SEMCC_PASSES    structcopy.py のあるディレクトリ(既定: このファイルの場所)
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


def patch(cls, sc):
    orig_codegen = cls.codegen

    def codegen(self, node):
        if node is not None and sc.is_struct_assign(self, node):
            return sc.gen_struct_copy(self, node)
        return orig_codegen(self, node)

    cls.codegen = codegen


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
    sc = load_module("semcc_structcopy", passes_dir / "structcopy.py")
    mycc = load_module("mycc_under_semcc", compiler)
    patch(find_codegen_class(mycc), sc)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
