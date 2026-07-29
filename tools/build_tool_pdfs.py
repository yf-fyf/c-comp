#!/usr/bin/env python3
"""
ツールガイド PDF を Pandoc + LuaLaTeX で生成する。

使い方:
    python3 tools/build_tool_pdfs.py

Markdown 原稿: materials/tools/*.md
PDF 出力:      workbook/guides/*.pdf
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MATERIALS_TOOLS = ROOT / "materials" / "tools"
WORKBOOK_GUIDES = ROOT / "workbook" / "guides"
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
    f"--resource-path={ROOT}:{MATERIALS_TOOLS}:{WORKBOOK_GUIDES}",
]

TOOL_TITLES = {
    "opencode": "OpenCode 導入ガイド",
}


def build_tool_pdf(name: str) -> bool:
    src = MATERIALS_TOOLS / f"{name}.md"
    dst = WORKBOOK_GUIDES / f"{name}.pdf"

    if not src.is_file():
        print(f"[SKIP] {name}: 原稿なし: {src}")
        return False

    WORKBOOK_GUIDES.mkdir(parents=True, exist_ok=True)

    title = TOOL_TITLES.get(name, name)
    cmd = [
        PANDOC, str(src),
        *PANDOC_ARGS_BASE,
        f"--variable=session-title:{title}",
        "-o", str(dst),
    ]

    print(f"[BUILD] {name}  ->  {dst}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[FAIL] {name}:")
        print(result.stderr)
        return False

    print(f"[ OK ] {name}")
    return True


def main():
    targets = sorted(p.stem for p in MATERIALS_TOOLS.glob("*.md"))

    if not targets:
        print("[INFO] ツール原稿がありません")
        return

    ok = 0
    fail = 0
    for name in targets:
        if build_tool_pdf(name):
            ok += 1
        else:
            fail += 1

    print()
    print(f"  OK: {ok}  FAIL: {fail}")
    if fail > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
