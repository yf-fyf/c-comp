#!/usr/bin/env python3
"""checkcc — 型検査つきコンパイララッパー(完成済み。編集しない)

コンパイルの前に typecheck.py を走らせ、誤りがあれば報告して終了する。
誤りがなければ、いつも通りアセンブリを出力する。

使い方:
    python3 checkcc.py file.c
    python3 checkcc.py --check-only file.c    # 検査だけして出力しない

環境変数:
    CHECKCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    CHECKCC_PASSES    typecheck.py のあるディレクトリ(既定: このファイルの場所)
"""

import importlib.util
import io
import os
import sys
import types
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


def main():
    args = sys.argv[1:]
    check_only = "--check-only" in args
    srcs = [a for a in args if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 checkcc.py [--check-only] file.c ...", file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("CHECKCC_PASSES", DIR))
    compiler = Path(os.environ.get("CHECKCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    import parser as real_parser

    tc = load_module("checkcc_typecheck", passes_dir / "typecheck.py")
    found = []

    # Parser の出口で検査を挟む
    shim = types.ModuleType("parser")

    def parse(tokens):
        prog = real_parser.parse(tokens)
        found.extend(tc.check_program(prog))
        return prog

    class CheckingParser(real_parser.Parser):
        def parse_program(self):
            prog = super().parse_program()
            found.extend(tc.check_program(prog))
            return prog

    shim.parse = parse
    shim.Parser = CheckingParser
    sys.modules["parser"] = shim

    mycc = load_module("mycc_under_checkcc", compiler)
    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    crash = None
    try:
        with redirect_stdout(buf):
            mycc.main()
    except SystemExit:
        pass
    except Exception as e:
        # 型検査で誤りを見つけていれば、そちらを報告する。
        # (型検査がないと、コード生成がこうして内部エラーで落ちる)
        crash = e

    if found:
        for e in found:
            print(f"{srcs[0]}:{e.line}: エラー: {e.msg}", file=sys.stderr)
        print(f"{len(found)} 件の誤りが見つかりました。", file=sys.stderr)
        raise SystemExit(1)

    if crash is not None:
        raise crash

    if not check_only:
        sys.stdout.write(buf.getvalue())


if __name__ == "__main__":
    main()
