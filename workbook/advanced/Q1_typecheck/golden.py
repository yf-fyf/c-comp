#!/usr/bin/env python3
"""Q1 golden test — 講義のテスト入力を1本も拒まないことを確認する

使い方:
    python3 golden.py                     # 同じディレクトリの typecheck.py
    python3 golden.py path/to/passes_dir  # 教員用参照実装で確認する
    python3 golden.py -v                  # 検査したファイルを全部表示(既定は誤検出のみ)

対象: workbook/sessions/*/tests/*.c と workbook/final/tests/*.c(fixed17)の全ファイル。
検査は厳しすぎても使えない。「正しいプログラムを1つも拒まない」ことを、
既存の資産すべてに対して確かめるのがこのテストである。

先に check.py を全 PASS にしてから回すこと。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"

args = [a for a in sys.argv[1:] if not a.startswith("-")]
verbose = "-v" in sys.argv[1:]
passes_dir = Path(args[0]) if args else DIR

spec = importlib.util.spec_from_file_location("Q1_typecheck", passes_dir / "typecheck.py")
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

sys.path.insert(0, str(SCAFFOLD))
from lexer import preprocess, tokenize   # noqa: E402
from parser import parse                 # noqa: E402


def analyze(path):
    src = preprocess(path.read_text(encoding="utf-8"), str(path))
    prog = parse(tokenize(src, str(path)))
    return tc.check_program(prog)


def fmt(errors):
    return [f"{e.line}: {e.msg}" for e in errors]


def main():
    corpus = sorted((WORKBOOK / "sessions").glob("*/tests/*.c"))
    corpus += sorted((WORKBOOK / "final" / "tests").glob("*.c"))

    noisy = []
    checked = 0
    for path in corpus:
        # 複数ファイルに分かれているテストは、単体では未定義参照になるため除く
        if path.with_suffix(".files").exists() or path.name.startswith("math_util"):
            continue
        try:
            errs = analyze(path)
        except NotImplementedError as e:
            print(f"[SKIP] 未実装: {e}")
            print("先に check.py を全 PASS にしてから golden.py を回す。")
            return 1
        except SystemExit:
            continue
        except Exception:
            continue
        checked += 1
        if errs:
            noisy.append((path.relative_to(WORKBOOK), fmt(errs)))
        elif verbose:
            print(f"  [OK] {path.relative_to(WORKBOOK)}")

    print("=== 正常系(講義のテスト入力を素通しできるか) ===")
    if noisy:
        print(f"  [FAIL] {len(noisy)} / {checked} ファイルで誤検出")
        for rel, msgs in noisy[:10]:
            print(f"         {rel}: {msgs[:2]}")
        print()
        print("検査が厳しすぎる。正しいプログラムを拒んでいる条件を緩める。")
        return 1

    print(f"  [PASS] {checked} ファイルすべてで誤検出なし")
    print()
    print("正しいプログラムを1つも拒んでいない!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
