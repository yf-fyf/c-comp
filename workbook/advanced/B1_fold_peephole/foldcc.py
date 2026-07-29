#!/usr/bin/env python3
"""foldcc — 最適化パスつきコンパイララッパー(完成済み。編集しない)

mycc.py には一切手を入れずに、
  1. Parser の結果(AST)に fold.py の定数畳み込みを適用し、
  2. mycc.py が出力したアセンブリに peephole.py を適用する。

使い方:
    python3 foldcc.py file.c [file2.c ...]
    python3 foldcc.py --no-fold file.c        # 畳み込みを外す
    python3 foldcc.py --no-peephole file.c    # ピープホールを外す

test_runner からも普通のコンパイラとして使える:
    python3 scaffold/test_runner.py --compiler advanced/B1_fold_peephole/foldcc.py

環境変数:
    OPTCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    OPTCC_PASSES    fold.py / peephole.py のあるディレクトリ(既定: このファイルの場所)

仕組み: mycc.py は `from parser import parse` で scaffold のパーサを読む。
foldcc は mycc を読み込む前に、sys.modules['parser'] を
「本物の parse の結果に fold_program をかけて返す」シムに差し替える。
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
    use_fold = "--no-fold" not in args
    use_peephole = "--no-peephole" not in args
    srcs = [a for a in args if not a.startswith("--")]
    if not srcs:
        print("使い方: python3 foldcc.py [--no-fold] [--no-peephole] file.c ...",
              file=sys.stderr)
        raise SystemExit(2)

    passes_dir = Path(os.environ.get("OPTCC_PASSES", DIR))
    compiler = Path(os.environ.get("OPTCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    if not compiler.is_file():
        print(f"ベースのコンパイラが見つからない: {compiler}", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(SCAFFOLD))
    import parser as real_parser  # scaffold の本物のパーサ

    fold = load_module("foldcc_fold", passes_dir / "fold.py") if use_fold else None
    peephole = (load_module("foldcc_peephole", passes_dir / "peephole.py")
                if use_peephole else None)

    # parser モジュールのシムを差し込む
    # (`from parser import parse` と `Parser` クラス直接利用の両方に対応する)
    shim = types.ModuleType("parser")
    if fold is not None:
        class FoldingParser(real_parser.Parser):
            def parse_program(self):
                return fold.fold_program(super().parse_program())

        shim.parse = lambda tokens: fold.fold_program(real_parser.parse(tokens))
        shim.Parser = FoldingParser
    else:
        shim.parse = real_parser.parse
        shim.Parser = real_parser.Parser
    sys.modules["parser"] = shim

    # mycc を読み込み、アセンブリ出力を捕まえる
    mycc = load_module("mycc_under_foldcc", compiler)
    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    with redirect_stdout(buf):
        mycc.main()
    asm = buf.getvalue()

    if peephole is not None:
        asm = peephole.optimize(asm)
    sys.stdout.write(asm)


if __name__ == "__main__":
    main()
