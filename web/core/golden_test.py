#!/usr/bin/env python3
"""黄金テスト: OCaml コア astdump_cli / compile() を Python 側の正と突き合わせる。

2本立て:
  1. astdump: OCaml コア astdump_cli と scaffold/parse_viewer.py のバイト一致検査。
     正は Python 版（design/webapps.md 4章）。全 workbook/**/tests/*.c について
     sexp / dot × 行番号の有無 の4通りを比較する。
     Python 版パーサが受理しないファイルは、OCaml 側も失敗することを確認して skip に数える。
  2. compile: ブラウザ向け js_of_ocaml ビルド（api.bc.js の myccCore.compile）が、
     ネイティブ CLI（reference/mycc_ref.exe --no-comments）とバイト単位で同じ
     RV64 アセンブリを出すことを、workbook/ocaml/run_tests.py と同じテストソース
     集合で確かめる。両者とも Refcomp.Compile を通るので、run_tests.py の等価性
     テスト（lecture16 との突き合わせ）と違い、正規化なしの完全一致で比較する。

使い方:
    cd dev/web/core && dune build && python3 golden_test.py [-v]
"""

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
WORKBOOK = HERE.parents[1] / "workbook"
OCAML_DIR = WORKBOOK / "ocaml"
CLI = HERE / "_build" / "default" / "cli" / "astdump_cli.exe"
MYCC_REF = OCAML_DIR / "_build" / "default" / "reference" / "mycc_ref.exe"
API_BC_JS = HERE / "_build" / "default" / "js" / "api.bc.js"
COMPILE_GOLDEN_MJS = HERE / "compile_golden.mjs"

GLOBS = ["sessions/*/tests/*.c", "final/tests/*.c", "advanced/*/tests/*.c"]
VARIANTS = [("sexp", []), ("sexp", ["--show-line"]), ("dot", []), ("dot", ["--show-line"])]

# workbook/ocaml/run_tests.py の all_test_sources() / extra_sources() をそのまま使う。
# 対象ファイル集合とコマ15 の複数ファイルコンパイルの扱いを二重に持たないため。
sys.path.insert(0, str(OCAML_DIR))
import run_tests  # noqa: E402


def run(cmd):
    return subprocess.run(cmd, cwd=WORKBOOK, capture_output=True)


def run_astdump_golden(verbose: bool) -> int:
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


def run_compile_golden(verbose: bool) -> int:
    if not MYCC_REF.exists():
        print(
            f"mycc_ref.exe がない: {MYCC_REF}（先に `cd workbook/ocaml && dune build` する）",
            file=sys.stderr,
        )
        return 2
    if not API_BC_JS.exists():
        print(
            f"api.bc.js がない: {API_BC_JS}（先に `cd web/core && dune build` する）",
            file=sys.stderr,
        )
        return 2

    sources = run_tests.all_test_sources()

    # コマ15 の複数ファイルコンパイル（.files で追加ソースを束ねる）は、
    # ブラウザ向け compile(source, comments) が単一ソース文字列しか受け取らない
    # 設計（api.ml のコメントにある「文字列を渡して JSON 文字列を受け取る」境界）
    # のため原理的に再現できない。これはバグではなく API の意図した範囲外なので、
    # 個別の skip として数え、mycc_ref 側の突き合わせからは外す。
    single_file: list[pathlib.Path] = []
    multi_file_skips: list[tuple[str, list[str]]] = []
    for src in sources:
        extras = run_tests.extra_sources(src)
        if isinstance(extras, str):
            multi_file_skips.append((str(src.relative_to(WORKBOOK)), [extras]))
            continue
        if extras:
            multi_file_skips.append(
                (str(src.relative_to(WORKBOOK)), [p.name for p in extras])
            )
            continue
        single_file.append(src)

    # mycc_ref.exe 側: workbook/ocaml/support/preprocess.ml のデフォルト include_dirs は
    # cwd 相対の "../scaffold" を含むので、run_tests.py の使い方（cd workbook/ocaml で
    # 起動する）と同じく cwd=OCAML_DIR で呼ぶ。そうしないと lib.h を include する
    # ファイルの前処理がここだけ失敗する。
    ref_results: dict[str, tuple[int, str]] = {}
    for src in single_file:
        rel = str(src.relative_to(WORKBOOK))
        proc = subprocess.run(
            [str(MYCC_REF), "--no-comments", str(src)],
            cwd=OCAML_DIR, capture_output=True, text=True,
        )
        ref_results[rel] = (proc.returncode, proc.stdout)

    # compile() 側: api.bc.js を 1 プロセスに 1 回だけロードして全ファイルをまとめて処理する
    # （100 件超をファイルごとに node -e 起動すると遅い上、起動コストのゆらぎでノイズが増える）。
    manifest = [
        {"path": str(src.relative_to(WORKBOOK)), "source": src.read_text(encoding="utf-8")}
        for src in single_file
    ]
    node_proc = subprocess.run(
        ["node", str(COMPILE_GOLDEN_MJS)],
        input=json.dumps(manifest), capture_output=True, text=True,
    )
    if node_proc.returncode != 0:
        print(f"compile_golden.mjs が失敗した:\n{node_proc.stderr}", file=sys.stderr)
        return 2
    compile_results: dict[str, tuple[bool, str | None]] = {}
    for line in node_proc.stdout.splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        compile_results[row["path"]] = (row["ok"], row["text"])

    ok = 0
    skips: list[str] = []
    fails: list[tuple[str, str]] = []
    for rel in sorted(ref_results):
        ref_code, ref_text = ref_results[rel]
        compile_ok, compile_text = compile_results.get(rel, (False, None))
        ref_ok = ref_code == 0
        if ref_ok and compile_ok:
            if ref_text == compile_text:
                ok += 1
            else:
                a_lines = ref_text.splitlines()
                b_lines = (compile_text or "").splitlines()
                diff = next(
                    (
                        f"line {i + 1}: mycc_ref={a!r} compile={b!r}"
                        for i, (a, b) in enumerate(zip(a_lines, b_lines))
                        if a != b
                    ),
                    f"長さ差: mycc_ref={len(a_lines)} compile={len(b_lines)} 行",
                )
                fails.append((rel, diff))
        elif not ref_ok and not compile_ok:
            skips.append(rel)
        elif ref_ok and not compile_ok:
            fails.append((rel, "mycc_ref は受理したが compile() は拒否した"))
        else:
            fails.append((rel, "compile() は受理したが mycc_ref は拒否した"))

    print(
        f"一致 {ok} / 不一致 {len(fails)} / skip {len(skips)}"
        f"（対象 {len(single_file)} ファイル、複数ファイルコンパイルにつき"
        f" {len(multi_file_skips)} 件を対象外）"
    )
    if verbose:
        if skips:
            print("\nskip（mycc_ref / compile() が揃って拒否）:")
            for rel in skips:
                print(f"  {rel}")
        if multi_file_skips:
            print("\nskip（複数ファイルコンパイルは compile() API の対象外）:")
            for rel, extras in multi_file_skips:
                print(f"  {rel}  (追加ソース: {', '.join(extras)})")
    if fails:
        print("\n不一致:")
        for rel, diff in fails[:30]:
            print(f"  {rel}\n    {diff}")
        if len(fails) > 30:
            print(f"  ... 他 {len(fails) - 30} 件")
        return 1
    return 0


def main() -> int:
    verbose = "-v" in sys.argv
    print("--- astdump (astdump_cli.exe == scaffold/parse_viewer.py) ---")
    astdump_code = run_astdump_golden(verbose)
    print("\n--- compile (api.bc.js の myccCore.compile == mycc_ref.exe --no-comments) ---")
    compile_code = run_compile_golden(verbose)
    if astdump_code == 2 or compile_code == 2:
        return 2
    return 1 if (astdump_code != 0 or compile_code != 0) else 0


if __name__ == "__main__":
    sys.exit(main())
