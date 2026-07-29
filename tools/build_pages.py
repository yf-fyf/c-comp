#!/usr/bin/env python3
"""Build the allowlisted static site published from the main branch."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "workbook"
WEB_DIST = ROOT / "web" / "app" / "dist"
EXCLUDED_PARTS = {"__pycache__", "_build", "cfg_out", "node_modules"}


def revision() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def safe_version(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", value):
        raise ValueError("version must contain only letters, digits, dot, underscore, or hyphen")
    return value


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def public_pdfs() -> list[Path]:
    handouts = sorted(WORKBOOK.glob("sessions/*/handout.pdf"))
    handouts += sorted(WORKBOOK.glob("advanced/*/handout.pdf"))
    handouts += sorted((WORKBOOK / "guides").glob("*.pdf"))
    if not handouts:
        raise RuntimeError("no public PDFs found under workbook/")
    return handouts


def archive_workbook(destination: Path, version: str) -> None:
    prefix = f"c-comp-workbook-{version}"
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for top_level in (ROOT / "README.md", ROOT / "LICENSE", ROOT / "THIRD_PARTY_NOTICES.md"):
            archive.write(top_level, f"{prefix}/{top_level.name}")
        for directory, subdirs, filenames in os.walk(WORKBOOK):
            path = Path(directory)
            subdirs[:] = [name for name in subdirs if name not in EXCLUDED_PARTS]
            for filename in filenames:
                source = path / filename
                if source.suffix in {".pyc", ".pyo"}:
                    continue
                relative = source.relative_to(ROOT)
                if "teacher" in relative.parts:
                    raise RuntimeError(f"forbidden path in workbook archive: {relative}")
                archive.write(source, f"{prefix}/{relative.as_posix()}")


def release_sections(pdfs: list[Path]) -> str:
    groups = {
        "通常回": [pdf for pdf in pdfs if "sessions" in pdf.parts],
        "発展課題": [pdf for pdf in pdfs if "advanced" in pdf.parts],
        "補助ガイド": [pdf for pdf in pdfs if "guides" in pdf.parts],
    }
    sections: list[str] = []
    for heading, files in groups.items():
        if not files:
            continue
        links = []
        for pdf in files:
            relative = pdf.relative_to(WORKBOOK)
            label = relative.parent.name if relative.parent != Path("guides") else pdf.stem
            href = Path("handouts") / relative
            links.append(f'<li><a href="{html.escape(href.as_posix())}">{html.escape(label)}</a></li>')
        sections.append(f"<section><h2>{heading}</h2><ul>{''.join(links)}</ul></section>")
    return "\n".join(sections)


def write_index(destination: Path, version: str, source_revision: str, pdfs: list[Path]) -> None:
    created = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    contents = f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>実践・C コンパイラ演習</title>
  <style>
    body {{ max-width: 58rem; margin: 0 auto; padding: 2rem 1rem 4rem; color: #18212f; font: 16px/1.6 system-ui, sans-serif; }}
    h1 {{ margin-bottom: .2rem; }} h2 {{ margin-top: 2rem; }} a {{ color: #0759a5; }}
    .lead {{ font-size: 1.15rem; }} .actions {{ display: flex; flex-wrap: wrap; gap: .8rem; margin: 1.5rem 0; }}
    .actions a {{ background: #0759a5; border-radius: .35rem; color: white; padding: .65rem 1rem; text-decoration: none; }}
    .meta {{ color: #52606d; font-size: .9rem; }} ul {{ padding-left: 1.3rem; }}
  </style>
</head>
<body>
  <h1>実践・C コンパイラ演習</h1>
  <p class="lead">Python で C 言語サブセットのコンパイラを段階的に作り、RISC-V RV64 で動かす演習教材です。</p>
  <div class="actions">
    <a href="downloads/c-comp-workbook-{html.escape(version)}.zip">開発環境をダウンロード</a>
    <a href="tools/">補助ツールを開く</a>
  </div>
  <p>ZIP には <code>workbook/</code> 全体（資料、starter、テスト、Docker 環境、参考実装、発展教材）を収録しています。</p>
  {release_sections(pdfs)}
  <footer class="meta"><p>Release {html.escape(version)} / source {html.escape(source_revision)} / {created}</p><p><a href="LICENSE">MIT License</a> · <a href="THIRD_PARTY_NOTICES.md">Third-party notices</a></p></footer>
</body>
</html>
"""
    destination.write_text(contents, encoding="utf-8")


def verify_output(output: Path) -> None:
    forbidden = [path for path in output.rglob("*") if "teacher" in path.parts]
    if forbidden:
        raise RuntimeError(f"forbidden path in release output: {forbidden[0]}")
    required = [output / "index.html", output / "tools" / "index.html"]
    missing = [path for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing release output: {', '.join(str(path) for path in missing)}")
    for archive in (output / "downloads").glob("*.zip"):
        with zipfile.ZipFile(archive) as release:
            if any("teacher" in Path(name).parts for name in release.namelist()):
                raise RuntimeError(f"forbidden path in release archive: {archive}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="release version used in the archive name")
    parser.add_argument("--output", type=Path, default=ROOT / ".pages", help="output directory")
    parser.add_argument("--revision", default=revision(), help="source revision displayed in the page")
    args = parser.parse_args()
    try:
        version = safe_version(args.version)
        if not WEB_DIST.is_dir():
            raise RuntimeError("web/app/dist is missing; run make web first")
        if args.output.resolve() == ROOT.resolve():
            raise RuntimeError("refusing to use the repository root as output")
        shutil.rmtree(args.output, ignore_errors=True)
        args.output.mkdir(parents=True)
        pdfs = public_pdfs()
        for pdf in pdfs:
            copy_file(pdf, args.output / "handouts" / pdf.relative_to(WORKBOOK))
        shutil.copytree(WEB_DIST, args.output / "tools")
        copy_file(WORKBOOK / "docs" / "debugging.md", args.output / "docs" / "debugging.md")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            copy_file(ROOT / name, args.output / name)
        archive = args.output / "downloads" / f"c-comp-workbook-{version}.zip"
        archive.parent.mkdir(parents=True)
        archive_workbook(archive, version)
        write_index(args.output / "index.html", version, args.revision, pdfs)
        (args.output / ".nojekyll").touch()
        verify_output(args.output)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"build_pages: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
