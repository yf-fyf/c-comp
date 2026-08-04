"""
コマ 14: コード生成⑬ — 複数ファイル・前処理 (#include / #define)（学生用スケルトン）

目標: 複数の .c ファイルを一度にコンパイルできるようにする。
      main() を変更して sys.argv[1:] の全ファイルを parse_file() し、
      prog と all_struct_defs を統合する。

実行方法:
    python3 sessions/14_preprocess_multifile/mycc.py main.c lib.c \
        | riscv64-linux-gnu-gcc -x assembler -static - -o out
    qemu-riscv64 ./out; echo $?
"""

import importlib.util
import sys
from pathlib import Path

_PREV = Path(__file__).resolve().parents[1] / '13_globals_scope' / 'mycc.py'
_SPEC = importlib.util.spec_from_file_location('_session13_mycc', _PREV)
prev = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(prev)

Node = prev.Node


class Codegen15(prev.Codegen14):
    pass


Codegen = Codegen15


def main() -> None:
    if len(sys.argv) < 2:
        print("使い方: python3 sessions/14_preprocess_multifile/mycc.py <source.c> [...]", file=sys.stderr)
        sys.exit(1)

    # TODO: sys.argv[1:] の各ファイルを Codegen15.parse_file() で読み、
    #       prog と all_struct_defs に統合してから gen_program() する。
    raise NotImplementedError("複数ファイル対応の main ループを実装してください")


if __name__ == '__main__':
    main()
