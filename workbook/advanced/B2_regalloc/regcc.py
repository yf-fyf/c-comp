#!/usr/bin/env python3
"""regcc — レジスタスタック版コンパイララッパー(完成済み。編集しない)

mycc.py には手を入れず、コード生成器の次のメソッドを差し替える。

    _push_a0   → regstack.push_a0
    _pop_into  → regstack.pop_into
    _gen_call  → 退避/復元つきの呼び出し生成(このファイル内)
    gen_func   → 関数ごとに depth を 0 に戻す

使い方:
    python3 regcc.py file.c [file2.c ...]
    python3 scaffold/test_runner.py --compiler advanced/B2_regalloc/regcc.py

環境変数:
    REGCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    REGCC_PASSES    regstack.py のあるディレクトリ(既定: このファイルの場所)
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
    """mycc モジュールから、_push_a0 を持つコード生成クラスを探す。"""
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "_push_a0"):
            # 継承関係があるときは最も派生したものを選ぶ
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("_push_a0 を持つコード生成クラスが見つからない")
    return best


def patch(cls, rs):
    """コード生成クラスに regstack の実装を差し込む。"""
    orig_gen_func = cls.gen_func
    orig_init = cls.__init__

    def __init__(self, *a, **kw):
        orig_init(self, *a, **kw)
        self.depth = 0

    def gen_func(self, node):
        self.depth = 0
        orig_gen_func(self, node)
        if self.depth != 0:
            raise RuntimeError(f"push と pop の数が合っていない (depth={self.depth})")

    def _push_a0(self):
        rs.push_a0(self)

    def _pop_into(self, reg):
        rs.pop_into(self, reg)

    def _gen_call(self, name, args):
        # 引数を左から評価して積み、逆順にレジスタへ戻す
        for arg in args:
            self.codegen(arg)
            self._push_a0()
        for i in reversed(range(len(args))):
            self._pop_into(f'a{i}')
        # ここで depth は呼び出し前の値に戻っている
        rs.spill_before_call(self)
        self.emit(f'  call {name}')
        rs.reload_after_call(self)

    cls.__init__ = __init__
    cls.gen_func = gen_func
    cls._push_a0 = _push_a0
    cls._pop_into = _pop_into
    cls._gen_call = _gen_call


def main():
    srcs = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 regcc.py file.c ...", file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("REGCC_PASSES", DIR))
    compiler = Path(os.environ.get("REGCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    rs = load_module("regcc_regstack", passes_dir / "regstack.py")
    mycc = load_module("mycc_under_regcc", compiler)
    patch(find_codegen_class(mycc), rs)

    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
