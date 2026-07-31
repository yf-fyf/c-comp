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
    style  design/maintaining.md の用語表（T59）で決めた表記に反していないか
           （第NN回・ゼロ埋め・コマとNの間の空白・「学生」表記）。
           workbook/advanced/・materials/advanced/ も対象（T59 後半で統一した
           全角/半角括弧・「発展課題 XN」・B ファミリの呼称・「（選択制）」の
           全廃・スキャフォールド表記も、advanced 配下限定であわせて検査する）

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


def _load_allowlist_section(section: str) -> list[dict]:
    if not ALLOWLIST_PATH.is_file():
        return []
    with ALLOWLIST_PATH.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get(section, [])


def load_allowlist() -> list[dict]:
    return _load_allowlist_section("legacy_terms")


def load_style_allowlist() -> list[dict]:
    return _load_allowlist_section("style_terms")


class Allowlist:
    """除外リスト。行番号ではなく行の内容で照合する。

    行番号で留めると、上の行を1行足し引きしただけで除外が外れて誤検出になり、
    逆にずれた先に別の違反があれば黙って握り潰す。そこで `match`（その行に
    必ず含まれる文字列）で照合する。

    一度も一致しなかったエントリは「死んだ除外」として違反にする。本文を直して
    対象語が消えたのにエントリだけ残る状態を、このチェック自身が見つけるため。
    """

    def __init__(self, entries: list[dict], section: str):
        self.section = section
        self.entries = entries
        self._used: set[int] = set()

    def matches(self, rel: str, line: str) -> bool:
        hit = False
        for idx, entry in enumerate(self.entries):
            if entry.get("file") != rel:
                continue
            needle = entry.get("match")
            if not needle or needle not in line:
                continue
            self._used.add(idx)
            hit = True
        return hit

    def unused(self) -> list[dict]:
        return [e for i, e in enumerate(self.entries) if i not in self._used]


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


def _dead_allowlist_violations(allowlist: "Allowlist") -> list[Violation]:
    """一度も一致しなかった除外エントリを違反として返す。"""
    out: list[Violation] = []
    for entry in allowlist.unused():
        rel = entry.get("file", "?")
        needle = entry.get("match", "")
        out.append(Violation(
            ROOT / ALLOWLIST_PATH.relative_to(ROOT), 0,
            f"死んだ除外（{allowlist.section}）: {rel} に "
            f"「{needle}」が見つからない。本文を直したならこのエントリを消す",
        ))
    return out


def check_legacy_terms() -> list[Violation]:
    violations: list[Violation] = []
    allowlist = Allowlist(load_allowlist(), "legacy_terms")
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
                    if allowlist.matches(rel, line):
                        continue
                    violations.append(Violation(
                        path, i, f"旧仕様語の残存の疑い: {line.strip()}",
                    ))
    violations.extend(_dead_allowlist_violations(allowlist))
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


# ── チェック5: 用語・表記の統一（T59） ──
#
# design/maintaining.md の「用語と表記の統一」節が定める規約のうち、機械的に
# 検出できるものを検査する: 回の呼称は「コマN」（ゼロ埋めなし・空白なし）に
# 統一し「第NN回」は使わない。人の呼称は「学習者」に統一し「学生」は使わない。
#
# 対象: materials/, workbook/ 配下の Markdown（*.md）のみ。原稿とスケルトン
# コード（*.py / *.ml）のコメント・docstring は対象外（コード中の記述であり、
# 進行中の授業で既に配布済みのファイルを書き換える実利が薄いため）。
#
# materials/advanced/, workbook/advanced/ も対象に含める（T59 後半）。ただし
# 「第N回」チェックだけは advanced 側で除外する: advanced の「Xシリーズの
# 第N回」（F/O/S/R/Q/B の各ファミリ内での位置）は、コマ1〜16 を指す「第NN回」
# とは無関係な別の数え方であり、正当な出現のため。
#
# advanced 配下限定の追加規約（T59 後半でこの節から統一したもの）:
#   - 全角/半角括弧: 地の文の丸括弧は全角（）に統一する。ただし Big-O 記法
#     （例: O(n³)）・LL(1) のような確立した記法、Markdown リンク／画像の
#     `](...)`、インラインコード・コードブロックの中身は対象外
#   - 「発展 XN」は使わない。他トピックを指すときは「発展課題 XN」に統一する
#     （各資料末尾の見出し「## 発展課題」はトピック内の節見出しであり対象外）
#   - 「（選択制）」は使わない（索引が既に「いずれも選択制」と宣言している）
#   - 「バックエンド発展シリーズ」は使わない（B ファミリの呼称は索引と同じ
#     「最適化入門」に統一し、「最適化入門発展シリーズ」と書く）
#   - 地の文の「scaffold」は「スキャフォールド」（カタカナ）に統一する。
#     ディレクトリ名・ファイルパス（`scaffold/`）・コマンド例・インライン
#     コード・コードブロックの中身は対象外

STYLE_DAI_KAI_RE = re.compile(r"第[0-9]{1,2}回")
STYLE_KOMA_ZERO_RE = re.compile(r"コマ0[0-9]")
STYLE_KOMA_SPACE_RE = re.compile(r"コマ[ 　][0-9]")
STYLE_GAKUSEI_RE = re.compile(r"学生")

STYLE_HATTEN_XN_RE = re.compile(r"発展 [A-Z][0-9]")
STYLE_SENTAKUSEI_RE = re.compile(r"（選択制）")
STYLE_BACKEND_SERIES_RE = re.compile(r"バックエンド発展シリーズ")

# 半角括弧の統一（advanced 限定）: インラインコード・Markdown リンク／画像・
# Big-O 記法・LL(1) を保護してから、残った半角 ( ) を検出する。
_STYLE_LINK_RE = re.compile(r"\]\([^)]*\)")
_STYLE_SPAN_RE = re.compile(r"`[^`]*`")
_STYLE_BIGO_RE = re.compile(r"(?<![A-Za-z0-9_])O\([^()]*\)")
_STYLE_LL1_RE = re.compile(r"LL\(1\)")
_STYLE_PROTECT_PATTERNS = (_STYLE_LINK_RE, _STYLE_SPAN_RE, _STYLE_BIGO_RE, _STYLE_LL1_RE)

# スキャフォールドの地の文表記（advanced 限定）: インラインコード・コード
# ブロックの中身と、`scaffold/` のようなパス表記は対象外にする。
_STYLE_SCAFFOLD_RE = re.compile(r"\bscaffold\b(?!/)")


def is_advanced_target(path: Path) -> bool:
    parts = path.relative_to(ROOT).parts
    return parts[:2] in {("materials", "advanced"), ("workbook", "advanced")}


def _style_mask_protected(line: str) -> str:
    """保護対象（リンク・インラインコード・Big-O・LL(1)）を除いた残りを返す。"""
    out = line
    for pat in _STYLE_PROTECT_PATTERNS:
        out = pat.sub(lambda m: "\x00" * len(m.group(0)), out)
    return out


def _check_advanced_style_in_file(
    path: Path, lines: list[str], violations: list[Violation],
    allowlist: "Allowlist", rel: str,
) -> None:
    in_fence = False
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if allowlist.matches(rel, line):
            continue
        if STYLE_HATTEN_XN_RE.search(line):
            violations.append(Violation(
                path, i,
                f"「発展 XN」表記の残存（「発展課題 XN」を使う）: {line.strip()}",
            ))
        if STYLE_SENTAKUSEI_RE.search(line):
            violations.append(Violation(
                path, i, f"「（選択制）」の残存（索引で既に宣言済みなので削る）: {line.strip()}",
            ))
        if STYLE_BACKEND_SERIES_RE.search(line):
            violations.append(Violation(
                path, i,
                "「バックエンド発展シリーズ」の残存"
                f"（「最適化入門発展シリーズ」を使う）: {line.strip()}",
            ))
        masked = _style_mask_protected(line)
        if "(" in masked or ")" in masked:
            violations.append(Violation(
                path, i, f"半角括弧の残存（全角（）を使う）: {line.strip()}",
            ))
        masked_scaffold = _STYLE_SPAN_RE.sub(
            lambda m: "\x00" * len(m.group(0)), line
        )
        if _STYLE_SCAFFOLD_RE.search(masked_scaffold):
            violations.append(Violation(
                path, i,
                f"地の文の「scaffold」の残存（「スキャフォールド」を使う）: {line.strip()}",
            ))


def _check_style_terms_in_file(
    path: Path, violations: list[Violation], allowlist: "Allowlist"
) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return
    rel = path.relative_to(ROOT).as_posix()
    advanced = is_advanced_target(path)
    for i, line in enumerate(lines, 1):
        if allowlist.matches(rel, line):
            continue
        if not advanced and STYLE_DAI_KAI_RE.search(line):
            violations.append(Violation(
                path, i, f"「第NN回」表記の残存（「コマN」を使う）: {line.strip()}",
            ))
        if STYLE_KOMA_ZERO_RE.search(line):
            violations.append(Violation(
                path, i, f"「コマN」のゼロ埋めの残存: {line.strip()}",
            ))
        if STYLE_KOMA_SPACE_RE.search(line):
            violations.append(Violation(
                path, i, f"「コマ」と数字の間の空白の残存: {line.strip()}",
            ))
        if STYLE_GAKUSEI_RE.search(line):
            violations.append(Violation(
                path, i, f"「学生」表記の残存（「学習者」を使う）: {line.strip()}",
            ))
    if advanced:
        _check_advanced_style_in_file(path, lines, violations, allowlist, rel)


def check_style_terms() -> list[Violation]:
    violations: list[Violation] = []
    allowlist = Allowlist(load_style_allowlist(), "style_terms")
    for top in ("materials", "workbook"):
        base = ROOT / top
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            if any(part in SKIP_DIRNAMES for part in path.relative_to(ROOT).parts):
                continue
            _check_style_terms_in_file(path, violations, allowlist)
    # README.md（リポジトリ直下）と design/ も対象に含める。
    readme = ROOT / "README.md"
    if readme.is_file():
        _check_style_terms_in_file(readme, violations, allowlist)
    design_dir = ROOT / "design"
    if design_dir.is_dir():
        for path in sorted(design_dir.rglob("*.md")):
            if any(part in SKIP_DIRNAMES for part in path.relative_to(ROOT).parts):
                continue
            _check_style_terms_in_file(path, violations, allowlist)
    violations.extend(_dead_allowlist_violations(allowlist))
    return violations


CHECKS = {
    "tests": ("原稿とテスト実体の突合", check_test_tables),
    "terms": ("旧仕様語の検出", check_legacy_terms),
    "nav": ("nav.yaml 未掲載の検出", check_nav_listing),
    "libh": ("lib.h と仕様書の宣言一致", check_libh_sync),
    "style": ("用語・表記の統一（T59）", check_style_terms),
}


def print_allowlist() -> None:
    entries = load_allowlist()
    style_entries = load_style_allowlist()
    if not entries and not style_entries:
        print("除外リストは空。")
        return
    if entries:
        print(f"legacy_terms 除外リスト {len(entries)} 件:")
        for entry in entries:
            status = entry.get("status", "?")
            reason = " ".join(entry.get("reason", "").split())
            print(f"  [{status}] {entry['file']}  {entry.get('match', '')}  {reason}")
    if style_entries:
        print(f"style_terms 除外リスト {len(style_entries)} 件:")
        for entry in style_entries:
            status = entry.get("status", "?")
            reason = " ".join(entry.get("reason", "").split())
            print(f"  [{status}] {entry['file']}  {entry.get('match', '')}  {reason}")


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
