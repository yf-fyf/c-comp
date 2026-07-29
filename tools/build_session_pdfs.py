#!/usr/bin/env python3
"""
セッション handout.pdf を Pandoc + LuaLaTeX で生成する。

使い方:
    python3 tools/build_session_pdfs.py
    python3 tools/build_session_pdfs.py 04_variables
    python3 tools/build_session_pdfs.py 02_interpreter 08_functions_recursion

Markdown 原稿: materials/sessions/NN_xxx.md
PDF 出力:      workbook/sessions/NN_xxx/handout.pdf
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATERIALS_ROOT = ROOT / "materials"
MATERIALS = MATERIALS_ROOT / "sessions"
WORKBOOK = ROOT / "workbook"
WORKBOOK_SESSIONS = WORKBOOK / "sessions"
WORKBOOK_SCAFFOLD = WORKBOOK / "scaffold"
AST_IMAGES = MATERIALS_ROOT / "figures" / "ast"
TEMPLATE = ROOT / "latex" / "session-template.tex"
METADATA = ROOT / "latex" / "session-metadata.yaml"
LUAFILTER = ROOT / "latex" / "session-boxes.lua"

PANDOC = "pandoc"
PANDOC_ARGS_BASE = [
    "--from", "markdown+pipe_tables+fenced_code_blocks+backtick_code_blocks+fenced_divs",
    "--pdf-engine=lualatex",
    f"--template={TEMPLATE}",
    f"--metadata-file={METADATA}",
    f"--lua-filter={LUAFILTER}",
    f"--resource-path={ROOT}:{MATERIALS_ROOT}:{MATERIALS}:{WORKBOOK_SESSIONS}",
]

SESSION_NUMBERS = {
    "01": "1",
    "02": "2", "03": "3", "04": "4", "05": "5",
    "06": "6", "07": "7", "08": "8", "09": "9", "10": "10",
    "11": "11", "12": "12", "13": "13", "14": "14", "15": "15", "16": "16",
}

AST_IMAGE_SPECS = [
    ("02_add_mul_ast.pdf",         "02_interpreter/tests/add_mul.c"),
    ("03_complex_ast.pdf",         "03_arithmetic_codegen/tests/complex.c"),
    ("04_variables_ast.pdf",       "04_variables/tests/target.c"),
    ("05_if_else_ast.pdf",         "05_if_else/tests/target.c"),
    ("06_while_ast.pdf",           "06_loops/tests/target.c"),
    ("06_for_ast.pdf",             "06_loops/tests/for_count.c"),
    ("08_fib_ast.pdf",             "08_functions_recursion/tests/target.c"),
    ("08_mutual_rec_ast.pdf",      "08_functions_recursion/tests/mutual_rec.c"),
    ("09_deref_write_ast.pdf",     "09_lvalue_rvalue/tests/deref_write.c"),
    ("10_array_sum_ast.pdf",       "10_types_arrays/tests/array_sum.c"),
    ("10_ptr_arith_ast.pdf",       "10_types_arrays/tests/ptr_arith.c"),
    ("11_printf_number_ast.pdf",   "11_strings_printf/tests/printf_number.c"),
    ("12_dot_access_ast.pdf",      "12_struct_typedef/tests/dot_access.c"),
    ("12_arrow_access_ast.pdf",    "12_struct_typedef/tests/arrow_access.c"),
    ("13_sizeof_test_ast.pdf",     "13_sizeof_malloc_list/tests/sizeof_test.c"),
    ("13_list_min_ast.pdf",        "13_sizeof_malloc_list/tests/list_min.c"),
    ("14_global_counter_ast.pdf",  "14_globals_scope/tests/global_min.c"),
    ("14_global_shadow_ast.pdf",   "14_globals_scope/tests/shadow_min.c"),
    ("15_define_min_ast.pdf",      "15_preprocess_multifile/tests/define_min.c"),
]


def dot_available() -> bool:
    try:
        subprocess.run(["dot", "-V"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def generate_ast_images(targets=None) -> bool:
    """AST 画像を materials/figures/ast/ に生成する。"""
    if not dot_available():
        print("[WARN] Graphviz 'dot' が見つからないため AST 画像は生成されません")
        return False

    parse_viewer = WORKBOOK_SCAFFOLD / "parse_viewer.py"
    if not parse_viewer.is_file():
        print("[WARN] parse_viewer.py が見つかりません")
        return False

    AST_IMAGES.mkdir(parents=True, exist_ok=True)

    all_ok = True
    target_prefixes = {target[:2] for target in targets} if targets else None
    for image_name, c_file in AST_IMAGE_SPECS:
        if target_prefixes is not None and c_file[:2] not in target_prefixes:
            continue
        dst = AST_IMAGES / image_name
        src = WORKBOOK_SESSIONS / c_file
        if not src.is_file():
            print(f"[SKIP] AST 画像材料なし: {src}")
            continue

        print(f"[DOT] {c_file}  ->  {dst}")
        p1 = subprocess.run(
            [sys.executable, str(parse_viewer), str(src), "--format", "dot"],
            capture_output=True, text=True, cwd=str(WORKBOOK),
        )
        if p1.returncode != 0:
            print(f"[FAIL] parse_viewer: {c_file}")
            print(p1.stderr)
            all_ok = False
            continue

        p2 = subprocess.run(
            ["dot", "-Tpdf", "-o", str(dst)],
            input=p1.stdout, capture_output=True, text=True,
        )
        if p2.returncode != 0:
            print(f"[FAIL] dot: {c_file}")
            print(p2.stderr)
            all_ok = False
            continue

    return all_ok


def session_number(dirname: str) -> str:
    num = SESSION_NUMBERS.get(dirname[:2], dirname[:2])
    return num


def build_pdf(session_dirname: str) -> bool:
    src = MATERIALS / f"{session_dirname}.md"
    session_dst = WORKBOOK_SESSIONS / session_dirname
    dst = session_dst / "handout.pdf"

    if not src.is_file():
        print(f"[SKIP] {session_dirname}: 原稿なし: {src}")
        return False

    session_dst.mkdir(parents=True, exist_ok=True)

    title = f"コマ{session_number(session_dirname)}"
    cmd = [
        PANDOC, str(src),
        *PANDOC_ARGS_BASE,
        f"--variable=session-title:{title}",
        "-o", str(dst),
    ]

    print(f"[BUILD] {session_dirname}  ->  {dst}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[FAIL] {session_dirname}:")
        print(result.stderr)
        return False

    print(f"[ OK ] {session_dirname}")
    return True


def main():
    if len(sys.argv) >= 2:
        targets = sys.argv[1:]
    else:
        targets = sorted(
            p.stem for p in MATERIALS.glob("*.md")
            if p.stem[:2].isdigit()
        )

    print("[INFO] AST 画像を生成します...")
    generate_ast_images(targets)

    ok = 0
    fail = 0
    for name in targets:
        if build_pdf(name):
            ok += 1
        else:
            fail += 1

    print()
    print(f"  OK: {ok}  FAIL: {fail}")
    if fail > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
