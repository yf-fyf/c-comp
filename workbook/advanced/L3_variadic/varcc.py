#!/usr/bin/env python3
"""varcc — 可変長引数の定義つきコンパイララッパー(完成済み。編集しない)

scaffold と mycc.py には手を入れず、次を差し込む。

  パーサ側:
    _parse_func   引数リストに '...' があった関数名を覚えておく
                  (scaffold のパーサは '...' を読み飛ばして捨ててしまうため)

  コード生成側:
    collect_decls 可変長関数なら save area 用のスロットを先に8個確保する
    gen_stmt      本体の先頭で、引数レジスタ a0〜a7 を save area へ書き出す
    codegen       __arg(i) の呼び出しを save area からの読み出しに変換する

使い方:
    python3 varcc.py file.c
    python3 scaffold/test_runner.py --compiler advanced/L3_variadic/varcc.py

環境変数:
    VARCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    VARCC_PASSES    variadic.py のあるディレクトリ(既定: このファイルの場所)
"""

import importlib.util
import inspect
import io
import os
import sys
import types
from contextlib import redirect_stdout
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"

VARIADIC_FUNCS = set()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_codegen_class(mod):
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "gen_func") and hasattr(obj, "emit"):
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("コード生成クラスが見つからない")
    return best


def install_parser_shim(real_parser):
    """引数リストに '...' があった関数名を VARIADIC_FUNCS に記録する。"""

    class VariadicParser(real_parser.Parser):
        def _parse_func(self, ty_str, name):
            start = self.pos
            # 引数リストの終わり('{' か ';')までに '...' があるか調べる
            i = start
            while i < len(self.tokens):
                sval = self.tokens[i].sval
                if sval in ('{', ';'):
                    break
                if sval == '...':
                    VARIADIC_FUNCS.add(name)
                    break
                i += 1
            return super()._parse_func(ty_str, name)

    shim = types.ModuleType("parser")
    shim.Parser = VariadicParser
    shim.parse = lambda tokens: VariadicParser(tokens).parse_program()
    sys.modules["parser"] = shim


def patch(cls, va):
    orig_gen_func = cls.gen_func
    orig_gen_stmt = cls.gen_stmt
    orig_collect_decls = cls.collect_decls
    orig_codegen = cls.codegen

    def gen_func(self, node):
        self._va_current = (node.kind == 'FuncDef'
                            and node.name in VARIADIC_FUNCS)
        self._va_need_save = self._va_current
        return orig_gen_func(self, node)

    def collect_decls(self, node):
        # gen_func から最初に呼ばれるタイミングで save area を先に確保する
        if getattr(self, '_va_current', False) and not getattr(self, '_va_reserved', False):
            self._va_reserved = True
            va.reserve_save_area(self)
            try:
                return orig_collect_decls(self, node)
            finally:
                self._va_reserved = False
        return orig_collect_decls(self, node)

    def gen_stmt(self, node):
        if getattr(self, '_va_need_save', False):
            self._va_need_save = False
            va.gen_save_registers(self)
        return orig_gen_stmt(self, node)

    def codegen(self, node):
        if node is not None and va.is_arg_builtin(self, node):
            return va.gen_arg_access(self, node)
        return orig_codegen(self, node)

    cls.gen_func = gen_func
    cls.collect_decls = collect_decls
    cls.gen_stmt = gen_stmt
    cls.codegen = codegen


def main():
    srcs = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 varcc.py file.c ...", file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("VARCC_PASSES", DIR))
    compiler = Path(os.environ.get("VARCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    import parser as real_parser

    install_parser_shim(real_parser)
    va = load_module("varcc_variadic", passes_dir / "variadic.py")
    mycc = load_module("mycc_under_varcc", compiler)
    patch(find_codegen_class(mycc), va)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
