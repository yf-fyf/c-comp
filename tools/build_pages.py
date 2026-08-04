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
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "workbook"
WEB_DIST = ROOT / "web" / "app" / "dist"
BUILD_SITE = ROOT / "tools" / "build_site.py"
ARCHIVE = ROOT / "archive"
EXCLUDED_PARTS = {"__pycache__", "_build", "cfg_out", "node_modules"}
# 過去リリースの凍結スナップショットのうち、公開に含めるもの。
# ディレクトリ名がそのまま公開パス archive/<name>/ になる。
# 撤去するときはこのタプルを空にする（design/maintaining.md の撤去手順を参照）。
PUBLISHED_ARCHIVES = ("v0.1.0",)
# 今学期の履修者が旧版資料から現行版へ移行し終える見込みの期日（仮決め）。
# TODO(c-comp-design/tasks/TODO.md の撤去タスク): 正式な期日が決まったら更新する。
ARCHIVE_SUNSET = "2026-10-31"
# main ブランチのルート直下に置いてよいものの許可リスト（design/maintaining.md と同期させる）。
ALLOWED_TOP_LEVEL = {
    "index.html", "assets", "figures", "sessions", "advanced", "docs", "guides",
    "tools", "downloads", "archive", "LICENSE", "LICENSE-MATERIALS",
    "THIRD_PARTY_NOTICES.md", ".nojekyll",
}
ARCHIVE_NOTICE_META = '<meta name="robots" content="noindex">'
ARCHIVE_NOTICE_BANNER = """<div style="background:#fff3cd;color:#664d03;border-bottom:2px solid #ffcd39;padding:0.75em 1em;font-size:0.95em">
これは 2026-07-29 公開の<strong>旧版アーカイブ</strong>です。言語仕様は現行版（Core プロファイル v2）適用前のものです。
今学期の履修者向けの時限的な移行措置であり、移行完了後に削除されます。
最新の資料は<a href="../../">現行版のトップページ</a>を参照してください。
なお、このスナップショット当時の教材は MIT ライセンスで公開されたものです（現行の教材ライセンスは CC BY-NC-SA 4.0）。
</div>"""
# dist の鮮度を比べる相手。web/app の入力と、埋め込まれるコア（web/core）の原稿。
WEB_SOURCES = [
    ROOT / "web" / "app" / "src",
    ROOT / "web" / "app" / "public",
    ROOT / "web" / "app" / "scripts",
    ROOT / "web" / "app" / "index.html",
    ROOT / "web" / "app" / "app.html",
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


def revision_date_passed(sunset: str) -> bool:
    return date.today() >= date.fromisoformat(sunset)


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
        for top_level in (ROOT / "README.md", ROOT / "LICENSE", ROOT / "LICENSE-MATERIALS", ROOT / "THIRD_PARTY_NOTICES.md"):
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


def verify_archive_hash(name: str) -> None:
    """archive/<name>.sha256 と archive/<name>/ の内容が一致するか確かめる。

    凍結スナップショットは書き換えないはずなので、取り込み時のハッシュとの不一致は
    意図しない改変の疑いとして扱う。マニフェストが無いこと自体も設定ミスとして落とす。
    """
    manifest = ARCHIVE / f"{name}.sha256"
    if not manifest.is_file():
        raise RuntimeError(f"archive/{name}.sha256 が無い（凍結時のマニフェストが未作成）")
    result = subprocess.run(
        ["sha256sum", "--check", "--strict", str(manifest)],
        cwd=ARCHIVE / name, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"archive/{name} の内容が取り込み時のハッシュと一致しない（改変の疑い）:\n"
            f"{result.stdout}{result.stderr}"
        )


def copy_archives(output: Path) -> None:
    """過去リリースの凍結スナップショットを出力先へそのままコピーする。"""
    for name in PUBLISHED_ARCHIVES:
        source = ARCHIVE / name
        if not source.is_dir():
            raise RuntimeError(f"archive/{name} が無い（PUBLISHED_ARCHIVES の設定ミス）")
        forbidden = [path for path in source.rglob("*") if "teacher" in path.parts]
        if forbidden:
            raise RuntimeError(f"forbidden path in archive/{name}: {forbidden[0]}")
        verify_archive_hash(name)
        shutil.copytree(source, output / "archive" / name)


def overlay_archive_notice(output: Path) -> None:
    """凍結した旧版 index.html に、旧版である旨のバナーと noindex を注入する。

    コミットした archive/<name>/ 自体はバイト単位で凍結したまま保つため、
    注意書きはビルド時にコピー先へだけ書き込む。
    """
    for name in PUBLISHED_ARCHIVES:
        index = output / "archive" / name / "index.html"
        html = index.read_text(encoding="utf-8")
        if "<head>" not in html or "<body>" not in html:
            raise RuntimeError(f"archive/{name}/index.html に <head>/<body> が見つからない")
        html = html.replace("<head>", f"<head>\n{ARCHIVE_NOTICE_META}", 1)
        html = html.replace("<body>", f"<body>\n{ARCHIVE_NOTICE_BANNER}", 1)
        index.write_text(html, encoding="utf-8")


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
    top_level = {path.name for path in output.iterdir()}
    disallowed = top_level - ALLOWED_TOP_LEVEL
    if disallowed:
        raise RuntimeError(f"許可リスト外のトップレベルパス: {', '.join(sorted(disallowed))}")
    required = [
        output / "index.html",
        output / "assets" / "style.css",
        output / "assets" / "lightbox.js",
        output / "sessions" / "01_interpreter" / "index.html",
        output / "advanced" / "index.html",
        output / "docs" / "language_spec" / "index.html",
        output / "tools" / "index.html",
        output / ".nojekyll",
    ]
    required += [output / "archive" / name / "index.html" for name in PUBLISHED_ARCHIVES]
    required += [output / "archive" / name / "tools" / "index.html" for name in PUBLISHED_ARCHIVES]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing release output: {', '.join(str(p) for p in missing)}")
    if not any((output / "figures").glob("*.svg")):
        raise RuntimeError("no figures in release output")
    archive_zip_prefixes = tuple(f"archive/{name}/" for name in PUBLISHED_ARCHIVES)
    for release_zip in output.rglob("*.zip"):
        relative = release_zip.relative_to(output).as_posix()
        is_archived_release = relative.startswith(archive_zip_prefixes)
        with zipfile.ZipFile(release_zip) as release:
            names = release.namelist()
            if any("teacher" in Path(name).parts for name in names):
                raise RuntimeError(f"forbidden path in release archive: {release_zip}")
            # archive/<name>/ 配下は過去リリース時点のビルド済み配布物そのものであり、
            # 当時は handout PDF を workbook に同梱していた（現行の PDF-free 方針の適用前）。
            # 原稿から作り直す対象ではないため、この検査だけ免除する。
            if not is_archived_release and any(name.endswith(".pdf") for name in names):
                raise RuntimeError(f"PDF left in release archive: {release_zip}")


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
        for name in ("LICENSE", "LICENSE-MATERIALS", "THIRD_PARTY_NOTICES.md"):
            copy_file(ROOT / name, args.output / name)
        archive = args.output / "downloads" / f"c-comp-workbook-{version}.zip"
        archive.parent.mkdir(parents=True)
        archive_workbook(archive, version)
        copy_archives(args.output)
        overlay_archive_notice(args.output)
        (args.output / ".nojekyll").touch()
        verify_output(args.output)
        if PUBLISHED_ARCHIVES and revision_date_passed(ARCHIVE_SUNSET):
            print(
                f"build_pages: [警告] archive/ の公開期限({ARCHIVE_SUNSET})を過ぎている。"
                "撤去手順は design/maintaining.md を参照",
                file=sys.stderr,
            )
    except (OSError, RuntimeError, ValueError) as error:
        print(f"build_pages: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
