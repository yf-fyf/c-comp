#!/usr/bin/env python3
"""F4 golden test — 講義の全テスト入力で scaffold と AST を突き合わせる

使い方:
    python3 golden.py               # 同じディレクトリの myparser.py を確認
    python3 golden.py path/to/myparser.py
    python3 golden.py -v            # 全ファイルの結果を表示(既定は FAIL のみ)

対象: workbook/sessions/*/tests/*.c と workbook/final/tests/*.c の全ファイル。
前処理と字句解析は scaffold のものを両者に使い、構文解析だけを比較する
(F1 を終えていれば、字句解析も自作に差し替えて試せる)。

全ファイル一致 = scaffold の Parser の完全な置き換え達成。
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
target = Path(args[0]) if args else DIR / "myparser.py"

spec = importlib.util.spec_from_file_location("myparser_f4", target)
myparser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(myparser)

sys.path.insert(0, str(SCAFFOLD))
import lexer as scaffold_lexer            # noqa: E402
import parser as scaffold_parser          # noqa: E402


def sig(n):
    if n is None:
        return None
    return (n.kind, n.val, n.sval, n.name, n.is_arrow, n.ty_str,
            sig(n.lhs), sig(n.rhs), sig(n.operand),
            sig(n.cond), sig(n.then), sig(n.else_),
            sig(n.init), sig(n.step), sig(n.body),
            tuple(sig(a) for a in n.args),
            tuple(sig(s) for s in n.stmts),
            tuple(sig(p) for p in n.params))


def collect_sources():
    files = sorted((WORKBOOK / "sessions").glob("*/tests/*.c"))
    files += sorted((WORKBOOK / "final" / "tests").glob("*.c"))
    return files


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
            tokens = scaffold_lexer.tokenize(source, str(path))
            expected = [sig(n) for n in scaffold_parser.parse(list(tokens))]
        except SystemExit:
            continue  # scaffold 側で解析できないファイルは対象外

        rel = path.relative_to(WORKBOOK)
        try:
            actual = [sig(n) for n in myparser.parse(list(tokens))]
        except NotImplementedError as e:
            print(f"[SKIP] 未実装: {e}")
            return 1
        except (SyntaxError, SystemExit) as e:
            print(f"[FAIL] {rel} — 自作パーサがエラー: {e}")
            fail_count += 1
            continue

        if actual == expected:
            pass_count += 1
            if verbose:
                print(f"[PASS] {rel}")
        else:
            # 最初に食い違ったトップレベル宣言を特定する
            idx = next((i for i, (e, a) in enumerate(zip(expected, actual))
                        if e != a), min(len(expected), len(actual)))
            print(f"[FAIL] {rel} — トップレベル {idx} 番目の宣言が不一致")
            fail_count += 1

    print()
    print("=============================")
    print(f"  PASS: {pass_count}  FAIL: {fail_count}  (全 {pass_count + fail_count} ファイル)")
    print("=============================")
    if fail_count == 0:
        print("scaffold と完全一致。Lexer(F1)とあわせて、ブラックボックスの完全な置き換え達成!")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
