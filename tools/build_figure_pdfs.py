#!/usr/bin/env python3
"""
講義資料の図を LuaLaTeX で生成する。

使い方:
    python3 tools/build_figure_pdfs.py            # 全図
    python3 tools/build_figure_pdfs.py 04 13      # ファイル名の前方一致で絞り込み

TikZ ソース: materials/figures/NN_name.tex
PDF 出力:    materials/figures/NN_name.pdf

共通プリアンブル latex/figure-preamble.tex は TEXINPUTS 経由で解決する。
ソースとプリアンブルの両方が PDF より古い場合はスキップする。
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIGURES = ROOT / "materials" / "figures"
LATEX_DIR = ROOT / "latex"
PREAMBLE = LATEX_DIR / "figure-preamble.tex"

LUALATEX = "lualatex"
AUX_SUFFIXES = [".aux", ".log", ".out"]


def needs_build(tex: Path, pdf: Path) -> bool:
    if not pdf.is_file():
        return True
    src_mtime = tex.stat().st_mtime
    if PREAMBLE.is_file():
        src_mtime = max(src_mtime, PREAMBLE.stat().st_mtime)
    return pdf.stat().st_mtime < src_mtime


def build_figure(tex: Path) -> bool:
    pdf = tex.with_suffix(".pdf")
    if not needs_build(tex, pdf):
        print(f"[SKIP] {tex.name}: 最新")
        return True

    env = os.environ.copy()
    # 共通プリアンブルを latex/ から解決する(末尾の : でデフォルトパスを維持)
    env["TEXINPUTS"] = f".:{LATEX_DIR}:" + env.get("TEXINPUTS", "")

    cmd = [
        LUALATEX,
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex.name,
    ]

    print(f"[BUILD] {tex.name}  ->  {pdf.name}")
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(FIGURES), env=env,
    )

    for suffix in AUX_SUFFIXES:
        aux = tex.with_suffix(suffix)
        if aux.is_file():
            aux.unlink()

    if result.returncode != 0 or not pdf.is_file():
        print(f"[FAIL] {tex.name}:")
        tail = result.stdout.strip().splitlines()[-30:]
        print("\n".join(tail))
        return False

    print(f"[ OK ] {tex.name}")
    return True


def main():
    if not FIGURES.is_dir():
        print(f"[WARN] 図ディレクトリがありません: {FIGURES}")
        return 0

    sources = sorted(FIGURES.glob("*.tex"))
    if len(sys.argv) >= 2:
        prefixes = tuple(sys.argv[1:])
        sources = [t for t in sources if t.name.startswith(prefixes)]

    if not sources:
        print("[WARN] 対象の .tex がありません")
        return 0

    ok = 0
    fail = 0
    for tex in sources:
        if build_figure(tex):
            ok += 1
        else:
            fail += 1

    print(f"\n[DONE] 成功 {ok} / 失敗 {fail}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
