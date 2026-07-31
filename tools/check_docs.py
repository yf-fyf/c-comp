#!/usr/bin/env python3
"""
原稿・配布物の整合を機械的に検査する（T57）。

使い方:
    python3 tools/check_docs.py                # 全チェックを実行
    python3 tools/check_docs.py --only tests    # 1つだけ実行（tests/terms/nav）
    python3 tools/check_docs.py --list-allowed  # 除外リストの内容を一覧表示

チェック一覧:
    tests  原稿のテスト表に挙がるファイル名が workbook/**/tests/ に実在するか
    terms  旧仕様語（配列・typedef・union・enum・fixed15）の残存を検査する
    nav    site/nav.yaml に載っていない materials/ 原稿を検出する
           （design/maintaining.md のワンライナーと同じロジック）
    libh   workbook/scaffold/lib.h の宣言一覧と language_spec.md の
           「標準ライブラリ」節のコードブロックが一致しているか（T55）

除外リストは tools/doc_check_allowlist.yaml。理由は各エントリの reason に書く。
依存: PyYAML（tools/build_site.py と共通）。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site import ROOT, load_nav  # noqa: E402  (site/nav.yaml を共通で読む)

ALLOWLIST_PATH = Path(__file__).resolve().parent / "doc_check_allowlist.yaml"

MATERIALS_SESSIONS = ROOT / "materials" / "sessions"
MATERIALS_ADVANCED = ROOT / "materials" / "advanced"
WORKBOOK_SESSIONS = ROOT / "workbook" / "sessions"
WORKBOOK_ADVANCED = ROOT / "workbook" / "advanced"

SKIP_DIRNAMES = {"node_modules", "_build", ".site", ".pages", "dist", "__pycache__"}


class Violation:
    def __init__(self, path: Path, line: int, message: str):
        self.path = path
        self.line = line
        self.message = message

    @property
    def relpath(self) -> str:
        return self.path.relative_to(ROOT).as_posix()

    def __str__(self) -> str:
        return f"{self.relpath}:{self.line}: {self.message}"


def load_allowlist() -> list[dict]:
    if not ALLOWLIST_PATH.is_file():
        return []
    with ALLOWLIST_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("legacy_terms", [])


# ── チェック1: 原稿とテスト実体の突合 ──
#
# 原稿の「## テスト」節などにあるテスト表（先頭列見出しが「ファイル」「テスト」）
# の行に出てくる `xxx.c` のようなファイル名が、対応する workbook/**/tests/ に
# 実在するか調べる。表の見出しで対象を絞るのは、O1_measure.md の「ベンチマーク」
# 表（bench/ を指す。tests/ ではない）のような別種の表を誤検出しないため。

TABLE_SEP_RE = re.compile(r"^\|[-:\s|]+\|\s*$")
ROW_FILENAME_RE = re.compile(
    r"^\|\s*`(?:tests/)?([A-Za-z0-9_.]+\.(?:c|ans|stdout|s))`"
)
TEST_TABLE_HEADERS = {"ファイル", "テスト"}


def iter_test_table_rows(lines: list[str]):
    """(見出し行番号, データ行, データ行番号) を表ごとに返す。"""
    i = 0
    n = len(lines)
    while i < n - 1:
        header = lines[i]
        if header.strip().startswith("|") and TABLE_SEP_RE.match(lines[i + 1]):
            first_cell = header.strip().strip("|").split("|")[0].strip()
            j = i + 2
            while j < n and lines[j].strip().startswith("|"):
                if first_cell in TEST_TABLE_HEADERS:
                    yield lines[j], j + 1
                j += 1
            i = j
        else:
            i += 1


def check_test_tables() -> list[Violation]:
    violations: list[Violation] = []
    pairs = [
        (MATERIALS_SESSIONS, WORKBOOK_SESSIONS),
        (MATERIALS_ADVANCED, WORKBOOK_ADVANCED),
    ]
    for materials_dir, workbook_dir in pairs:
        if not materials_dir.is_dir():
            continue
        for source in sorted(materials_dir.glob("*.md")):
            stem = source.stem
            tests_dir = workbook_dir / stem / "tests"
            lines = source.read_text(encoding="utf-8").splitlines()
            for row, line_no in iter_test_table_rows(lines):
                match = ROW_FILENAME_RE.match(row)
                if not match:
                    continue
                filename = match.group(1)
                target = tests_dir / filename
                if not target.is_file():
                    violations.append(Violation(
                        source, line_no,
                        f"テスト表のファイルが実在しない: "
                        f"{target.relative_to(ROOT).as_posix()}",
                    ))
    return violations


# ── チェック2: 旧仕様語の検出 ──
#
# 対象: materials/, workbook/ 配下のテキストファイル全般。
# 構造的な除外（除外リストに載せるまでもなく恒常的に正当なもの）:
#   - materials/advanced/, workbook/advanced/  … 発展課題は仕様外機能を
#     あえて扱う題材なので、旧仕様語への言及そのものが正当
#   - workbook/docs/language_spec.md 全体      … 仕様書自身が「配列・typedef
#     などは対象外」と宣言している文書なので、出現そのものが仕様の一部
#   - materials/figures/<発展課題ID>_*.tex     … 発展課題の図（回 ID の先頭が
#     A-Z + 数字のもの）。figures/ はコマと発展課題の図を同じ階層に置くので
#     ディレクトリではなくファイル名で判定する
# 上記に当てはまらない出現は tools/doc_check_allowlist.yaml で個別に扱う。

BANNED_TERMS = [
    re.compile(r"配列"),
    re.compile(r"\btypedef\b"),
    re.compile(r"\bunion\b"),
    re.compile(r"\benum\b"),
    re.compile(r"fixed15"),
]

TEXT_SUFFIXES = {".md", ".py", ".ml", ".tex", ".txt", ".yaml", ".yml", ".ts", ".tsx"}
ADVANCED_ID_RE = re.compile(r"^[A-Z]\d+_")


def is_structurally_exempt(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if parts[:2] == ("materials", "advanced") or parts[:2] == ("workbook", "advanced"):
        return True
    if rel == Path("workbook/docs/language_spec.md"):
        return True
    if parts[:2] == ("materials", "figures") and ADVANCED_ID_RE.match(path.stem):
        return True
    return False


def check_legacy_terms() -> list[Violation]:
    violations: list[Violation] = []
    allowlist = {
        (entry["file"], entry["line"]) for entry in load_allowlist()
    }
    for top in ("materials", "workbook"):
        base = ROOT / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP_DIRNAMES for part in path.relative_to(ROOT).parts):
                continue
            if is_structurally_exempt(path):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            rel = path.relative_to(ROOT).as_posix()
            for i, line in enumerate(lines, 1):
                if any(term.search(line) for term in BANNED_TERMS):
                    if (rel, i) in allowlist:
                        continue
                    violations.append(Violation(
                        path, i, f"旧仕様語の残存の疑い: {line.strip()}",
                    ))
    return violations


# ── チェック3: nav.yaml 未掲載の検出 ──
#
# design/maintaining.md のワンライナーと同じロジック
# （materials/*/*.md のうち site/nav.yaml の pages に無いもの）。
# nav.yaml の読み込みは tools/build_site.py の load_nav() を再利用する。

def check_nav_listing() -> list[Violation]:
    nav = load_nav()
    listed = {p for section in nav["sections"] for p in section["pages"]}
    found = {
        str(p.relative_to(ROOT)) for p in (ROOT / "materials").glob("*/*.md")
    }
    missing = sorted(found - listed)
    nav_path = ROOT / "site" / "nav.yaml"
    return [
        Violation(nav_path, 1, f"nav.yaml に未掲載: {item}")
        for item in missing
    ]


# ── チェック4: lib.h と仕様書の宣言一致（T55） ──
#
# workbook/docs/language_spec.md の「標準ライブラリ」節は workbook/scaffold/lib.h
# の宣言一覧を（読みやすさのため）そのまま書き下している。二重管理なので放置
# すると乖離する。宣言の集合と順序をコメント・空白の差を無視して突き合わせる
# ことで、乖離を機械的に検出する（内容を lib.h への参照だけに変える案、
# ビルド時生成する案もあったが、仕様書の可読性を保ったままこれが最も低コスト）。

LIBH_PATH = ROOT / "workbook" / "scaffold" / "lib.h"
LANG_SPEC_PATH = ROOT / "workbook" / "docs" / "language_spec.md"
LIBH_HEADING = "## 標準ライブラリ（`lib.h`）"


def normalize_c_decl_lines(text: str) -> list[str]:
    """行末コメントと空白差を無視した宣言行の並びを返す。"""
    result = []
    for raw in text.splitlines():
        code = raw.split("//", 1)[0].strip()
        if not code:
            continue
        result.append(re.sub(r"\s+", " ", code))
    return result


def extract_libh_code_block(spec_lines: list[str]) -> tuple[list[str], int] | None:
    """「標準ライブラリ」節直後の ```c ... ``` ブロックを返す（内容, 開始行番号）。"""
    heading_idx = next(
        (i for i, line in enumerate(spec_lines) if line.strip() == LIBH_HEADING),
        None,
    )
    if heading_idx is None:
        return None
    start = next(
        (i + 1 for i in range(heading_idx, min(heading_idx + 20, len(spec_lines)))
         if spec_lines[i].strip() == "```c"),
        None,
    )
    if start is None:
        return None
    end = next(
        (i for i in range(start, len(spec_lines)) if spec_lines[i].strip() == "```"),
        None,
    )
    if end is None:
        return None
    return spec_lines[start:end], start + 1


def check_libh_sync() -> list[Violation]:
    if not LIBH_PATH.is_file() or not LANG_SPEC_PATH.is_file():
        return []
    libh_decls = normalize_c_decl_lines(LIBH_PATH.read_text(encoding="utf-8"))
    spec_lines = LANG_SPEC_PATH.read_text(encoding="utf-8").splitlines()
    block = extract_libh_code_block(spec_lines)
    if block is None:
        return [Violation(
            LANG_SPEC_PATH, 1,
            f"「{LIBH_HEADING}」直後に ```c ブロックが見つからない",
        )]
    block_lines, block_start_line = block
    spec_decls = normalize_c_decl_lines("\n".join(block_lines))
    if spec_decls == libh_decls:
        return []
    missing = [d for d in libh_decls if d not in spec_decls]
    extra = [d for d in spec_decls if d not in libh_decls]
    details = []
    if missing:
        details.append("lib.h にあって仕様書に無い: " + " / ".join(missing))
    if extra:
        details.append("仕様書にあって lib.h に無い: " + " / ".join(extra))
    if not details:
        details.append("宣言は同一集合だが並び順が異なる")
    return [Violation(
        LANG_SPEC_PATH, block_start_line,
        "lib.h の宣言と一致しない: " + "; ".join(details),
    )]


CHECKS = {
    "tests": ("原稿とテスト実体の突合", check_test_tables),
    "terms": ("旧仕様語の検出", check_legacy_terms),
    "nav": ("nav.yaml 未掲載の検出", check_nav_listing),
    "libh": ("lib.h と仕様書の宣言一致", check_libh_sync),
}


def print_allowlist() -> None:
    entries = load_allowlist()
    if not entries:
        print("除外リストは空。")
        return
    print(f"除外リスト {len(entries)} 件:")
    for entry in entries:
        status = entry.get("status", "?")
        reason = " ".join(entry.get("reason", "").split())
        print(f"  [{status}] {entry['file']}:{entry['line']}  {reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help=f"実行するチェック（カンマ区切り: {','.join(CHECKS)}）")
    parser.add_argument("--list-allowed", action="store_true",
                        help="除外リストの内容を表示して終了する")
    args = parser.parse_args()

    if args.list_allowed:
        print_allowlist()
        return 0

    names = list(CHECKS)
    if args.only:
        names = args.only.split(",")
        unknown = [n for n in names if n not in CHECKS]
        if unknown:
            print(f"未知のチェック: {', '.join(unknown)}", file=sys.stderr)
            return 2

    total = 0
    for name in names:
        title, func = CHECKS[name]
        violations = func()
        if violations:
            print(f"\n[{name}] {title}: {len(violations)} 件の違反")
            for v in violations:
                print(f"  {v}")
            total += len(violations)
        else:
            print(f"[{name}] {title}: 違反なし")

    if total:
        print(f"\n合計 {total} 件の違反")
        return 1
    print("\nすべてのチェックを通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
