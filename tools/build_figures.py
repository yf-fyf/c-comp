#!/usr/bin/env python3
"""
講義資料の図を SVG で生成する。

使い方:
    python3 tools/build_figures.py            # 全図
    python3 tools/build_figures.py 04 13      # ファイル名の前方一致で絞り込み

TikZ ソース: materials/figures/NN_name.tex   -> materials/figures/NN_name.svg
AST 図:      workbook/sessions/**/*.c        -> materials/figures/ast/NN_name.svg

TikZ は LuaLaTeX で一度 PDF にしてから SVG へ変換する。中間 PDF は残さない。
変換に poppler の pdftocairo を使うのは、dvisvgm --pdf が Ghostscript 10.01 以降で
動かないためである（mutool も要求されるが常用環境に無い）。
文字はグリフのパスとして埋まるので、閲覧側にフォントが無くても日本語が正しく出る。

依存: lualatex（TikZ 図）、poppler-utils の pdftocairo または pdf2svg、
      Graphviz の dot（AST 図）。
生成 SVG はコミット対象なので、CI ではこのスクリプトを走らせなくてよい。
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "materials" / "figures"
AST_FIGURES = FIGURES / "ast"
LATEX_DIR = ROOT / "latex"
PREAMBLE = LATEX_DIR / "figure-preamble.tex"
WORKBOOK = ROOT / "workbook"
WORKBOOK_SESSIONS = WORKBOOK / "sessions"
PARSE_VIEWER = WORKBOOK / "scaffold" / "parse_viewer.py"

LUALATEX = "lualatex"

# AST 図の生成元。ファイル名の先頭2桁がコマ番号で、絞り込みにも使う。
AST_IMAGE_SPECS = [
    ("01_add_mul_ast.svg",         "01_interpreter/tests/add_mul.c"),
    ("02_complex_ast.svg",         "02_arithmetic_codegen/tests/complex.c"),
    ("03_variables_ast.svg",       "03_variables/tests/target.c"),
    ("04_if_else_ast.svg",         "04_if_else/tests/target.c"),
    ("05_while_ast.svg",           "05_loops/tests/target.c"),
    ("05_for_ast.svg",             "05_loops/tests/for_count.c"),
    ("06_fib_ast.svg",             "06_functions_recursion/tests/target.c"),
    ("06_mutual_rec_ast.svg",      "06_functions_recursion/tests/mutual_rec.c"),
    ("07_deref_write_ast.svg",     "07_lvalue_rvalue/tests/deref_write.c"),
    ("09_ptr_sum_ast.svg",         "09_pointer_arith/tests/ptr_sum.c"),
    ("09_ptr_arith_ast.svg",       "09_pointer_arith/tests/ptr_arith.c"),
    ("10_printf_number_ast.svg",   "10_strings_data_section/tests/printf_number.c"),
    ("12_dot_access_ast.svg",      "12_struct_malloc_list/tests/dot_access.c"),
    ("12_arrow_access_ast.svg",    "12_struct_malloc_list/tests/arrow_access.c"),
    ("12_sizeof_test_ast.svg",     "12_struct_malloc_list/tests/sizeof_test.c"),
    ("12_list_min_ast.svg",        "12_struct_malloc_list/tests/list_min.c"),
    ("13_global_counter_ast.svg",  "13_globals_scope/tests/global_min.c"),
    ("13_global_shadow_ast.svg",   "13_globals_scope/tests/shadow_min.c"),
    ("14_define_min_ast.svg",      "14_preprocess_multifile/tests/define_min.c"),
]


def find_pdf_to_svg() -> list[str] | None:
    """PDF -> SVG の変換コマンドを決める。{src} {dst} を後ろに付けて使う。"""
    if shutil.which("pdftocairo"):
        return ["pdftocairo", "-svg"]
    if shutil.which("pdf2svg"):
        return ["pdf2svg"]
    return None


def needs_build(sources: list[Path], target: Path) -> bool:
    if not target.is_file():
        return True
    newest = max((p.stat().st_mtime for p in sources if p.is_file()), default=0)
    return target.stat().st_mtime < newest


def build_tikz_figure(tex: Path, converter: list[str]) -> bool:
    svg = tex.with_suffix(".svg")
    if not needs_build([tex, PREAMBLE], svg):
        print(f"[SKIP] {tex.name}: 最新")
        return True

    env = os.environ.copy()
    # 共通プリアンブルを latex/ から解決する(末尾の : でデフォルトパスを維持)
    env["TEXINPUTS"] = f".:{LATEX_DIR}:" + env.get("TEXINPUTS", "")

    print(f"[BUILD] {tex.name}  ->  {svg.name}")
    with tempfile.TemporaryDirectory() as tmp:
        # 中間 PDF と aux を materials/figures/ に散らかさないよう別ディレクトリへ出す
        result = subprocess.run(
            [LUALATEX, "-interaction=nonstopmode", "-halt-on-error",
             f"-output-directory={tmp}", tex.name],
            capture_output=True, text=True, cwd=str(FIGURES), env=env,
        )
        pdf = Path(tmp) / tex.with_suffix(".pdf").name
        if result.returncode != 0 or not pdf.is_file():
            print(f"[FAIL] {tex.name}: LuaLaTeX")
            print("\n".join(result.stdout.strip().splitlines()[-30:]))
            return False

        conv = subprocess.run(
            [*converter, str(pdf), str(svg)], capture_output=True, text=True
        )
        if conv.returncode != 0 or not svg.is_file():
            print(f"[FAIL] {tex.name}: SVG 変換 — {conv.stderr.strip()}")
            return False

    print(f"[ OK ] {tex.name}")
    return True


def build_ast_figure(name: str, c_file: str) -> bool:
    dst = AST_FIGURES / name
    src = WORKBOOK_SESSIONS / c_file
    if not src.is_file():
        print(f"[SKIP] {name}: 生成元がない: {src}")
        return True
    if not needs_build([src, PARSE_VIEWER], dst):
        print(f"[SKIP] {name}: 最新")
        return True

    print(f"[BUILD] {c_file}  ->  {name}")
    viewer = subprocess.run(
        [sys.executable, str(PARSE_VIEWER), str(src), "--format", "dot"],
        capture_output=True, text=True, cwd=str(WORKBOOK),
    )
    if viewer.returncode != 0:
        print(f"[FAIL] {name}: parse_viewer — {viewer.stderr.strip()}")
        return False

    dot = subprocess.run(
        ["dot", "-Tsvg", "-o", str(dst)], input=viewer.stdout,
        capture_output=True, text=True,
    )
    if dot.returncode != 0 or not dst.is_file():
        print(f"[FAIL] {name}: dot — {dot.stderr.strip()}")
        return False

    print(f"[ OK ] {name}")
    return True


def main() -> int:
    if not FIGURES.is_dir():
        print(f"[WARN] 図ディレクトリがありません: {FIGURES}")
        return 0

    converter = find_pdf_to_svg()
    if converter is None:
        print("pdftocairo (poppler-utils) か pdf2svg が要る", file=sys.stderr)
        return 2
    if shutil.which(LUALATEX) is None:
        print(f"{LUALATEX} が見つからない", file=sys.stderr)
        return 2
    if shutil.which("dot") is None:
        print("Graphviz の dot が見つからない", file=sys.stderr)
        return 2

    prefixes = tuple(sys.argv[1:]) if len(sys.argv) >= 2 else None

    tikz = sorted(FIGURES.glob("*.tex"))
    ast = list(AST_IMAGE_SPECS)
    if prefixes:
        tikz = [t for t in tikz if t.name.startswith(prefixes)]
        ast = [(n, c) for n, c in ast if n.startswith(prefixes)]

    if not tikz and not ast:
        print("[WARN] 対象の図がありません")
        return 0

    AST_FIGURES.mkdir(parents=True, exist_ok=True)

    ok = fail = 0
    for tex in tikz:
        if build_tikz_figure(tex, converter):
            ok += 1
        else:
            fail += 1
    for name, c_file in ast:
        if build_ast_figure(name, c_file):
            ok += 1
        else:
            fail += 1

    print(f"\n[DONE] 成功 {ok} / 失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
