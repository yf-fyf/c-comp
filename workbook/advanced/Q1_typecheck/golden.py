#!/usr/bin/env python3
"""Q1 golden test — 講義のテスト入力を1本も拒まないことを確認する

使い方:
    python3 golden.py                     # 同じディレクトリの typecheck.py
    python3 golden.py path/to/passes_dir  # 教員用参照実装で確認する
    python3 golden.py -v                  # 成功した入力も表示(既定は誤検出・除外・失敗を表示)

対象: workbook/sessions/*/tests/*.c と workbook/final/tests/*.c(fixed17)の全ファイル。
検査は厳しすぎても使えない。「正しいプログラムを1つも拒まない」ことを、
既存の資産すべてに対して確かめるのがこのテストである。

先に check.py を全 PASS にしてから回すこと。
"""

import importlib.util
import io
import sys
from contextlib import redirect_stderr
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


def parse_source(path):
    src = preprocess(path.read_text(encoding="utf-8"), str(path))
    return parse(tokenize(src, str(path)))


def fmt(errors):
    return [f"{e.line}: {e.msg}" for e in errors]


def main():
    corpus = sorted((WORKBOOK / "sessions").glob("*/tests/*.c"))
    corpus += sorted((WORKBOOK / "final" / "tests").glob("*.c"))

    noisy = []
    failures = []
    checked = 0
    skipped = 0
    for path in corpus:
        rel = path.relative_to(WORKBOOK)
        # 複数ファイルに分かれているテストは、単体では未定義参照になるため除く
        if path.with_suffix(".files").exists() or path.name.startswith("math_util"):
            print(f"  [SKIP] {rel} — 複数ファイルのテストを単体で検査しないため")
            skipped += 1
            continue
        # scaffold が受理する入力を先に確定する。学習者実装の例外はここで除外しない。
        diagnostics = io.StringIO()
        try:
            with redirect_stderr(diagnostics):
                prog = parse_source(path)
        except (SyntaxError, SystemExit) as e:
            detail = diagnostics.getvalue().strip() or f"{type(e).__name__}: {e}"
            print(f"  [SKIP] {rel} — scaffold が受理しない入力: {detail}")
            skipped += 1
            continue
        except Exception as e:
            failures.append((rel, f"scaffold の処理に失敗: {type(e).__name__}: {e}"))
            continue

        try:
            errors = fmt(tc.check_program(prog))
        except NotImplementedError as e:
            print(f"[SKIP] {rel} — 未実装: {e}")
            print("先に check.py を全 PASS にしてから golden.py を回す。")
            return 1
        except (Exception, SystemExit) as e:
            failures.append((rel, f"検査実装に例外: {type(e).__name__}: {e}"))
            continue
        checked += 1
        if errors:
            noisy.append((rel, errors))
        elif verbose:
            print(f"  [OK] {rel}")

    print("=== 正常系(講義のテスト入力を素通しできるか) ===")
    print(f"  検査: {checked} 件 / 除外: {skipped} 件 / 検査失敗: {len(failures)} 件")
    if failures:
        print(f"  [FAIL] {len(failures)} ファイルで検査を完了できなかった")
        for rel, detail in failures[:10]:
            print(f"         {rel}: {detail}")
        if len(failures) > 10:
            print(f"         ほか {len(failures) - 10} ファイル")
    if noisy:
        print(f"  [FAIL] {len(noisy)} / {checked} ファイルで誤検出")
        for rel, msgs in noisy[:10]:
            print(f"         {rel}: {msgs[:2]}")
        print()
        print("検査が厳しすぎる。正しいプログラムを拒んでいる条件を緩める。")
    if failures or noisy:
        return 1
    if checked == 0:
        print("  [FAIL] 検査できた入力が0件。テスト入力と除外理由を確認する。")
        return 1

    print(f"  [PASS] {checked} ファイルすべてで誤検出なし")
    print()
    print("正しいプログラムを1つも拒んでいない!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
