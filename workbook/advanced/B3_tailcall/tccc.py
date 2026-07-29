#!/usr/bin/env python3
"""tccc — 末尾呼び出し最適化つきコンパイララッパー(完成済み。編集しない)

mycc.py には手を入れず、次の2点を差し込む。

    gen_func  → 関数名・引数・本体先頭ラベルを記録し、本体の直前にラベルを置く
    gen_stmt  → 自分自身への末尾呼び出しの return を、tailcall.py の実装で生成する

使い方:
    python3 tccc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/B3_tailcall/tccc.py

環境変数:
    TCCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    TCCC_PASSES    tailcall.py のあるディレクトリ(既定: このファイルの場所)
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
        if inspect.isclass(obj) and hasattr(obj, "gen_func") and hasattr(obj, "gen_stmt"):
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("コード生成クラスが見つからない")
    return best


def patch(cls, tc):
    orig_gen_func = cls.gen_func
    orig_gen_stmt = cls.gen_stmt

    def gen_func(self, node):
        if node.kind != 'FuncDef':
            return orig_gen_func(self, node)
        self.tc_func_name = node.name
        self.tc_params = node.params
        self.tc_label = f'.Ltc_{node.name}'
        self.tc_need_label = True   # 本体の最初の文の直前でラベルを出す
        self.tc_count = getattr(self, 'tc_count', 0)
        return orig_gen_func(self, node)

    def gen_stmt(self, node):
        if getattr(self, 'tc_need_label', False):
            self.tc_need_label = False
            self.emit(f'{self.tc_label}:')
        if node.kind == 'Return' and tc.is_self_tail_call(self, node):
            self.tc_count = getattr(self, 'tc_count', 0) + 1
            tc.gen_tail_call(self, node)
            return
        return orig_gen_stmt(self, node)

    cls.gen_func = gen_func
    cls.gen_stmt = gen_stmt


def main():
    srcs = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 tccc.py file.c ...", file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("TCCC_PASSES", DIR))
    compiler = Path(os.environ.get("TCCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    tc = load_module("tccc_tailcall", passes_dir / "tailcall.py")
    mycc = load_module("mycc_under_tccc", compiler)
    patch(find_codegen_class(mycc), tc)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
