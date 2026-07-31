#!/usr/bin/env python3
"""Build the allowlisted static site published from the main branch."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "workbook"
WEB_DIST = ROOT / "web" / "app" / "dist"
BUILD_SITE = ROOT / "tools" / "build_site.py"
EXCLUDED_PARTS = {"__pycache__", "_build", "cfg_out", "node_modules"}
# dist の鮮度を比べる相手。web/app の入力と、埋め込まれるコア（web/core）の原稿。
WEB_SOURCES = [
    ROOT / "web" / "app" / "src",
    ROOT / "web" / "app" / "public",
    ROOT / "web" / "app" / "scripts",
    ROOT / "web" / "app" / "index.html",
    ROOT / "web" / "app" / "ast.html",
    ROOT / "web" / "app" / "sim.html",
    ROOT / "web" / "app" / "vite.config.ts",
    ROOT / "web" / "app" / "tsconfig.json",
    ROOT / "web" / "app" / "package.json",
    ROOT / "web" / "core" / "lib",
    ROOT / "web" / "core" / "js",
    ROOT / "web" / "core" / "cli",
]


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


def build_site(output: Path, version: str, source_revision: str) -> None:
    """資料サイトを出力先へ直接生成する（tools/build_site.py が単一の出典）"""
    result = subprocess.run(
        [sys.executable, str(BUILD_SITE), "--output", str(output),
         "--release", version, "--revision", source_revision],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"build_site.py failed:\n{result.stdout}\n{result.stderr}")


def archive_workbook(destination: Path, version: str) -> None:
    """演習環境の配布アーカイブ。資料はサイトで配るので workbook のコードとテストだけ。"""
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


def newest_mtime(paths, *, skip_dirs=frozenset()) -> float:
    """paths 以下（ファイルなら自身）の最終更新時刻の最大値。存在しないものは無視する。"""
    newest = 0.0
    for path in paths:
        if path.is_file():
            newest = max(newest, path.stat().st_mtime)
        elif path.is_dir():
            for directory, subdirs, filenames in os.walk(path):
                subdirs[:] = [name for name in subdirs if name not in skip_dirs]
                for filename in filenames:
                    candidate = Path(directory) / filename
                    if candidate.is_file():
                        newest = max(newest, candidate.stat().st_mtime)
    return newest


def check_web_dist() -> None:
    """web/app/dist が存在し、ソースより新しいことを確かめる。

    `make web` が失敗しても古い dist が残っていれば公開物は作れてしまう。
    それでは壊れたまま exit 0 になり、破損が隠れる。ここで鮮度まで見る。
    """
    if not WEB_DIST.is_dir() or not (WEB_DIST / "index.html").is_file():
        raise RuntimeError("web/app/dist が無い（または不完全）。先に make web を実行する")
    dist_mtime = newest_mtime([WEB_DIST])
    source_mtime = newest_mtime(WEB_SOURCES, skip_dirs=EXCLUDED_PARTS | {"dist"})
    if dist_mtime < source_mtime:
        raise RuntimeError(
            "web/app/dist がソースより古い（make web が失敗しているか未実行）。"
            "先に make web を実行する"
        )


def check_skeletons() -> None:
    """各回の mycc.py がスケルトンのままか確かめる。

    完成解答は Private リポジトリだけで管理する運用なので、公開物に混ざると事故になる。
    未実装マーカーが1つも無い mycc.py は完成品の置き忘れとみなす。
    スケルトンの書き方を変えてここが誤検出するようになったら、目印の方を見直す。
    """
    complete = [
        path.relative_to(ROOT).as_posix()
        for path in sorted(WORKBOOK.glob("sessions/*/mycc.py"))
        if "NotImplementedError" not in path.read_text(encoding="utf-8")
    ]
    if complete:
        raise RuntimeError(
            "未実装マーカーの無い mycc.py がある（完成解答の混入の疑い）: "
            + ", ".join(complete)
        )


def verify_output(output: Path) -> None:
    forbidden = [path for path in output.rglob("*") if "teacher" in path.parts]
    if forbidden:
        raise RuntimeError(f"forbidden path in release output: {forbidden[0]}")
    required = [
        output / "index.html",
        output / "assets" / "style.css",
        output / "sessions" / "01_environment" / "index.html",
        output / "advanced" / "index.html",
        output / "docs" / "language_spec" / "index.html",
        output / "tools" / "index.html",
        output / ".nojekyll",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing release output: {', '.join(str(p) for p in missing)}")
    if not any((output / "figures").glob("*.svg")):
        raise RuntimeError("no figures in release output")
    for archive in (output / "downloads").glob("*.zip"):
        with zipfile.ZipFile(archive) as release:
            names = release.namelist()
            if any("teacher" in Path(name).parts for name in names):
                raise RuntimeError(f"forbidden path in release archive: {archive}")
            if any(name.endswith(".pdf") for name in names):
                raise RuntimeError(f"PDF left in release archive: {archive}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="release version used in the archive name")
    parser.add_argument("--output", type=Path, default=ROOT / ".pages", help="output directory")
    parser.add_argument("--revision", default=revision(), help="source revision displayed in the page")
    args = parser.parse_args()
    try:
        version = safe_version(args.version)
        check_web_dist()
        if args.output.resolve() == ROOT.resolve():
            raise RuntimeError("refusing to use the repository root as output")
        check_skeletons()
        shutil.rmtree(args.output, ignore_errors=True)
        args.output.mkdir(parents=True)

        build_site(args.output, version, args.revision)
        shutil.copytree(WEB_DIST, args.output / "tools")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
            copy_file(ROOT / name, args.output / name)
        archive = args.output / "downloads" / f"c-comp-workbook-{version}.zip"
        archive.parent.mkdir(parents=True)
        archive_workbook(archive, version)
        (args.output / ".nojekyll").touch()
        verify_output(args.output)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"build_pages: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
