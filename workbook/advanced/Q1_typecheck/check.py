#!/usr/bin/env python3
"""Q1 確認スクリプト — typecheck.py をエラーコーパスで確認する

使い方:
    python3 check.py                      # 同じディレクトリの typecheck.py
    python3 check.py path/to/passes_dir

tests/*.c を検査し、報告された誤りが tests/*.expected と一致するか比べる。
.expected の各行は「行番号: メッセージ」の形式。空ファイルは「誤りなし」を意味する。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
TESTS = DIR / "tests"

passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("Q1_typecheck", passes_dir / "typecheck.py")
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)

sys.path.insert(0, str(SCAFFOLD))
from lexer import preprocess, tokenize   # noqa: E402
from parser import parse                 # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


def analyze(path):
    src = preprocess(path.read_text(encoding="utf-8"), str(path))
    prog = parse(tokenize(src, str(path)))
    return tc.check_program(prog)


def fmt(errors):
    return [f"{e.line}: {e.msg}" for e in errors]


def check_file(csrc):
    global pass_count, fail_count
    expected = [l for l in csrc.with_suffix(".expected")
                .read_text(encoding="utf-8").splitlines() if l.strip()]
    try:
        actual = fmt(analyze(csrc))
    except NotImplementedError:
        raise
    except Exception as e:
        print(f"  [FAIL] {csrc.name} — 検査中に例外: {e}")
        fail_count += 1
        return

    if actual == expected:
        label = "誤りなし" if not expected else f"{len(expected)} 件を検出"
        print(f"  [PASS] {csrc.name}（{label}）")
        pass_count += 1
    else:
        print(f"  [FAIL] {csrc.name}")
        for line in expected:
            if line not in actual:
                print(f"         検出できていない: {line}")
        for line in actual:
            if line not in expected:
                print(f"         余計な報告      : {line}")
        fail_count += 1


print("--- エラーコーパス ---")
try:
    for csrc in sorted(TESTS.glob("*.c")):
        check_file(csrc)
except NotImplementedError as e:
    print(f"  [SKIP] 未実装: {e}")
    skip_count += 1

# 正常系: 講義の全テスト入力が「誤りなし」と判定されること
print("--- 正常系（講義のテスト入力を素通しできるか）---")
if skip_count == 0:
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
        except SystemExit:
            continue
        except Exception:
            continue
        checked += 1
        if errs:
            noisy.append((path.relative_to(WORKBOOK), fmt(errs)))
    if noisy:
        print(f"  [FAIL] {len(noisy)} / {checked} ファイルで誤検出")
        for rel, msgs in noisy[:5]:
            print(f"         {rel}: {msgs[:2]}")
        fail_count += 1
    else:
        print(f"  [PASS] {checked} ファイルすべてで誤検出なし")
        pass_count += 1
else:
    print("  [SKIP] エラーコーパスが未実装のため省略")

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")
if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
