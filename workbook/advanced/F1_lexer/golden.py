#!/usr/bin/env python3
"""F1 golden test — 講義の全テスト入力で scaffold とトークン列を突き合わせる

使い方:
    python3 golden.py               # 同じディレクトリの mylexer.py を確認
    python3 golden.py path/to/mylexer.py
    python3 golden.py -v            # 全ファイルの結果を表示(既定は FAIL のみ)

対象: workbook/sessions/*/tests/*.c と workbook/final/tests/*.c の全ファイル。
前処理(#include / #define)は scaffold の preprocess を両者に通して条件を揃え、
純粋に字句解析だけを比較する。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"

args = sys.argv[1:]
verbose = "-v" in args
args = [a for a in args if a != "-v"]
target = Path(args[0]) if args else DIR / "mylexer.py"

spec = importlib.util.spec_from_file_location("mylexer", target)
mylexer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mylexer)

sys.path.insert(0, str(SCAFFOLD))
import lexer as scaffold_lexer  # noqa: E402


def sig(tokens):
    return [(t.kind, t.val, t.sval, t.line) for t in tokens]


def collect_sources():
    files = sorted((WORKBOOK / "sessions").glob("*/tests/*.c"))
    files += sorted((WORKBOOK / "final" / "tests").glob("*.c"))
    return files


def first_diff(expected, actual):
    for idx, (e, a) in enumerate(zip(expected, actual)):
        if e != a:
            return idx, e, a
    n = min(len(expected), len(actual))
    return n, (expected[n] if n < len(expected) else "(なし)"), \
        (actual[n] if n < len(actual) else "(なし)")


def main():
    files = collect_sources()
    if not files:
        print("[WARN] テスト用 .c ファイルが見つからない")
        return 1

    pass_count = 0
    fail_count = 0
    for path in files:
        raw = path.read_text(encoding="utf-8")
        try:
            source = scaffold_lexer.preprocess(raw, str(path))
            expected = sig(scaffold_lexer.tokenize(source, str(path)))
        except SystemExit:
            continue  # scaffold 側で解析できないファイルは対象外

        rel = path.relative_to(WORKBOOK)
        try:
            actual = sig(mylexer.tokenize(source, str(path)))
        except NotImplementedError as e:
            print(f"[SKIP] 未実装: {e}")
            return 1
        except (SyntaxError, SystemExit) as e:
            print(f"[FAIL] {rel} — 自作 lexer がエラー: {e}")
            fail_count += 1
            continue

        if actual == expected:
            pass_count += 1
            if verbose:
                print(f"[PASS] {rel}")
        else:
            idx, e, a = first_diff(expected, actual)
            print(f"[FAIL] {rel} — トークン {idx} 番目が不一致")
            print(f"       scaffold: {e}")
            print(f"       自作    : {a}")
            fail_count += 1

    print()
    print("=============================")
    print(f"  PASS: {pass_count}  FAIL: {fail_count}  (全 {pass_count + fail_count} ファイル)")
    print("=============================")
    if fail_count == 0:
        print("scaffold と完全一致。字句解析器の置き換え成功!")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
