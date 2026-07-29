#!/usr/bin/env python3
"""黄金テスト: OCaml コア astdump_cli と scaffold/parse_viewer.py のバイト一致検査。

正は Python 版（design/webapps.md 4章）。全 workbook/**/tests/*.c について
sexp / dot × 行番号の有無 の4通りを比較する。
Python 版パーサが受理しないファイルは、OCaml 側も失敗することを確認して skip に数える。

使い方:
    cd dev/web/core && dune build && python3 golden_test.py [-v]
"""

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
WORKBOOK = HERE.parents[1] / "workbook"
CLI = HERE / "_build" / "default" / "cli" / "astdump_cli.exe"

GLOBS = ["sessions/*/tests/*.c", "final/tests/*.c", "advanced/*/tests/*.c"]
VARIANTS = [("sexp", []), ("sexp", ["--show-line"]), ("dot", []), ("dot", ["--show-line"])]


def run(cmd):
    return subprocess.run(cmd, cwd=WORKBOOK, capture_output=True)


def main() -> int:
    verbose = "-v" in sys.argv
    if not CLI.exists():
        print(f"astdump_cli がない: {CLI}（先に dune build する）", file=sys.stderr)
        return 2

    files = sorted(p for g in GLOBS for p in WORKBOOK.glob(g))
    ok = 0
    skips = []       # (file, 理由)
    fails = []       # (file, variant, 差分の先頭)
    for f in files:
        rel = str(f.relative_to(WORKBOOK))
        py_probe = run(["python3", "scaffold/parse_viewer.py", rel])
        if py_probe.returncode != 0:
            oc_probe = run([str(CLI), rel])
            if oc_probe.returncode == 0:
                fails.append((rel, "(受理判定)", "Python 版は拒否したが OCaml 版は受理した"))
            else:
                skips.append((rel, py_probe.stderr.decode().strip().splitlines()[-1:]))
            continue
        for fmt, extra in VARIANTS:
            py = run(["python3", "scaffold/parse_viewer.py", rel, "--format", fmt, *extra])
            oc = run([str(CLI), rel, "--format", fmt, *extra])
            variant = f"{fmt} {' '.join(extra)}".strip()
            if oc.returncode != 0:
                fails.append((rel, variant, "OCaml 側がエラー: " + oc.stderr.decode()[:200]))
                continue
            if py.stdout == oc.stdout:
                ok += 1
            else:
                py_lines = py.stdout.decode().splitlines()
                oc_lines = oc.stdout.decode().splitlines()
                diff = next(
                    (
                        f"line {i + 1}: py={a!r} oc={b!r}"
                        for i, (a, b) in enumerate(zip(py_lines, oc_lines))
                        if a != b
                    ),
                    f"長さ差: py={len(py_lines)} oc={len(oc_lines)} 行",
                )
                fails.append((rel, variant, diff))

    print(f"一致 {ok} / 不一致 {len(fails)} / skip {len(skips)}（対象 {len(files)} ファイル × 4通り）")
    if skips and verbose:
        print("\nskip（Python 版が受理しない・OCaml 版も失敗を確認）:")
        for rel, why in skips:
            print(f"  {rel}  {why[0] if why else ''}")
    if fails:
        print("\n不一致:")
        for rel, variant, diff in fails[:30]:
            print(f"  {rel} [{variant}]\n    {diff}")
        if len(fails) > 30:
            print(f"  ... 他 {len(fails) - 30} 件")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
