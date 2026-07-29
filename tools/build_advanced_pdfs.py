#!/usr/bin/env python3
"""
発展資料の handout.pdf を Pandoc + LuaLaTeX で生成する。

使い方:
    python3 tools/build_advanced_pdfs.py
    python3 tools/build_advanced_pdfs.py F0_cyk

Markdown 原稿: materials/advanced/<ID>_xxx.md
PDF 出力:      workbook/advanced/<ID>_xxx/handout.pdf
               (原稿名とトピックディレクトリ名は一対一で対応する)

ヘッダ右上のタイトルは原稿名の先頭2文字の回 ID(F0_cyk → F0)。
handout の見出しは原稿の H1(トピック名)をそのまま使う。
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATERIALS_ROOT = ROOT / "materials"
MATERIALS = MATERIALS_ROOT / "advanced"
SESSION_MATERIALS = MATERIALS_ROOT / "sessions"
ADVANCED = ROOT / "workbook" / "advanced"

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
    f"--resource-path={ROOT}:{MATERIALS_ROOT}:{MATERIALS}:{SESSION_MATERIALS}",
]


def build_pdf(stem: str) -> bool:
    src = MATERIALS / f"{stem}.md"
    dest_dir = ADVANCED / stem
    dst = dest_dir / "handout.pdf"

    if not src.is_file():
        print(f"[SKIP] {stem}: 原稿なし: {src}")
        return False

    dest_dir.mkdir(parents=True, exist_ok=True)

    title = stem[:2]
    cmd = [
        PANDOC, str(src),
        *PANDOC_ARGS_BASE,
        f"--variable=session-title:{title}",
        "-o", str(dst),
    ]

    print(f"[BUILD] {stem}  ->  {dst}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[FAIL] {stem}:")
        print(result.stderr)
        return False

    print(f"[ OK ] {stem}")
    return True


def main():
    if len(sys.argv) >= 2:
        targets = sys.argv[1:]
    else:
        targets = sorted(p.stem for p in MATERIALS.glob("*.md"))

    if not targets:
        print("[WARN] 原稿がありません")
        return 0

    ok = 0
    fail = 0
    for name in targets:
        if build_pdf(name):
            ok += 1
        else:
            fail += 1

    print()
    print(f"  OK: {ok}  FAIL: {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
