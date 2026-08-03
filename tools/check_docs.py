#!/usr/bin/env python3
"""
原稿・配布物の整合を機械的に検査する。

使い方:
    python3 tools/check_docs.py                # 全チェックを実行
    python3 tools/check_docs.py --only tests    # 1つだけ実行（tests/terms/nav）
    python3 tools/check_docs.py --list-allowed  # 除外リストの内容を一覧表示
    python3 tools/check_docs.py --list-kinds    # 除外リストに書ける検出種別を表示

チェック一覧:
    tests     原稿のテスト表に挙がるファイル名が workbook/**/tests/ に実在するか
    terms     旧仕様語（配列・typedef・union・enum・fixed15）の残存を検査する
    nav       site/nav.yaml に載っていない materials/ 原稿を検出する
              （design/maintaining.md のワンライナーと同じロジック）
    libh      workbook/scaffold/lib.h の宣言一覧と language_spec.md の
              「標準ライブラリ」節のコードブロックが一致しているか
    style     design/maintaining.md の用語表で決めた表記に反していないか
              （第NN回・ゼロ埋め・コマとNの間の空白・「学生」表記）。
              workbook/advanced/・materials/advanced/ も対象（advanced 配下で統一した
              全角/半角括弧・「発展課題 XN」・B ファミリの呼称・「（選択制）」の
              全廃・スキャフォールド表記も、advanced 配下限定であわせて検査する）
    exc       language_spec.md の「N 件の例外」宣言と例外見出しの数の一致
    codeexec  workbook/docs/code_example.md の C コードブロックを実際に処理系へ
              通す。前段（構文）は常時、後段（実行と期待終了コードの照合）は
              処理系と RV64 ツールチェーンが揃っているときだけ走る
    ident     conventions.md / testing.md / scaffold/README.md が挙げる識別子が
              workbook/sessions/ と workbook/scaffold/ に実在するか
    grammar   materials/sessions/01〜14 の「この回までの言語仕様（EBNF）」節が
              単調に増えているか（右辺の精密化は許可リストで扱う）、コマ14 が
              language_spec.md の最終形 EBNF と一致するか、各スナップショットが
              参照閉包（現れる非終端記号が定義済み）を満たすか

除外リストは tools/doc_check_allowlist.yaml。理由は各エントリの reason に書く。
除外は「ファイル + 行の内容（match） + 検出種別（check）」の3点で指定する。
依存: PyYAML（tools/build_site.py と共通）。
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
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


# 除外リストに書ける検出種別。セクションごとに閉じた集合として持ち、
# 綴り違いをその場で違反にする。ここに無い種別を書いた除外は「効かない除外」に
# なるが、それは死んだ除外としてしか現れず原因が分かりにくいので明示的に弾く。
ALLOWLIST_KINDS: dict[str, set[str]] = {
    "legacy_terms": {"array", "typedef", "union", "enum", "fixed15"},
    "style_terms": {
        "dai-kai", "koma-zero-pad", "koma-space", "gakusei", "kurobako",
        "hatten-xn", "sentakusei", "backend-series",
        "hankaku-paren", "scaffold-hyoki",
    },
    "code_examples": {"parse", "exec"},
    "identifiers": {"missing-identifier", "missing-file"},
}


class Allowlist:
    """除外リスト。行番号ではなく「行の内容 + 検出種別」で照合する。

    行番号で留めると、上の行を1行足し引きしただけで除外が外れて誤検出になり、
    逆にずれた先に別の違反があれば黙って握り潰す。そこで `match`（その行に
    必ず含まれる文字列）で照合する。

    さらに、1行が複数の検出種別に引っかかることがある（例: `コマ 08` は
    ゼロ埋めと空白の両方）。行の内容だけで照合すると、片方を許すつもりの除外が
    もう片方まで黙らせてしまう。そこで `check`（検出種別。文字列またはその配列）
    を必須にし、名指しした種別だけを除外する。

    一度も一致しなかったエントリは「死んだ除外」として違反にする。本文を直して
    対象語が消えたのにエントリだけ残る状態を、このチェック自身が見つけるため。
    """

    def __init__(self, entries: list[dict], section: str):
        self.section = section
        self.entries = entries
        self._used: set[int] = set()
        self.malformed: list[tuple[dict, str]] = []
        known = ALLOWLIST_KINDS.get(section, set())
        self._kinds: list[set[str]] = []
        for entry in entries:
            raw = entry.get("check")
            if raw is None:
                self._kinds.append(set())
                self.malformed.append((entry, "check（検出種別）が無い"))
                continue
            kinds = {raw} if isinstance(raw, str) else set(raw)
            unknown = sorted(kinds - known)
            if unknown:
                self.malformed.append(
                    (entry, f"未知の検出種別: {', '.join(unknown)}"
                            f"（使えるのは {', '.join(sorted(known))}）"))
            self._kinds.append(kinds)

    def matches(self, rel: str, line: str, kind: str) -> bool:
        """rel の line に対する kind の検出を除外してよいか。"""
        hit = False
        for idx, entry in enumerate(self.entries):
            if entry.get("file") != rel:
                continue
            if kind not in self._kinds[idx]:
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

# (検出種別, 正規表現)。検出種別は除外リストの check: に書く名前と対応する。
BANNED_TERMS = [
    ("array", re.compile(r"配列")),
    ("typedef", re.compile(r"\btypedef\b")),
    ("union", re.compile(r"\bunion\b")),
    ("enum", re.compile(r"\benum\b")),
    ("fixed15", re.compile(r"fixed15")),
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
    """書式不備の除外と、一度も一致しなかった除外エントリを違反として返す。"""
    out: list[Violation] = []
    allow_path = ROOT / ALLOWLIST_PATH.relative_to(ROOT)
    for entry, why in allowlist.malformed:
        out.append(Violation(
            allow_path, 0,
            f"除外エントリの書式不備（{allowlist.section}）: "
            f"{entry.get('file', '?')} / 「{entry.get('match', '')}」: {why}",
        ))
    for entry in allowlist.unused():
        rel = entry.get("file", "?")
        needle = entry.get("match", "")
        kind = entry.get("check", "?")
        out.append(Violation(
            allow_path, 0,
            f"死んだ除外（{allowlist.section}）: {rel} の検出種別 {kind} に "
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
                for kind, term in BANNED_TERMS:
                    if not term.search(line):
                        continue
                    if allowlist.matches(rel, line, kind):
                        continue
                    violations.append(Violation(
                        path, i,
                        f"旧仕様語の残存の疑い（{kind}）: {line.strip()}",
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


# ── チェック4: lib.h と仕様書の宣言一致 ──
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


# ── チェック5: 用語・表記の統一 ──
#
# design/maintaining.md の「用語と表記の統一」節が定める規約のうち、機械的に
# 検出できるものを検査する: 回の呼称は「コマN」（ゼロ埋めなし・空白なし）に
# 統一し「第NN回」は使わない。人の呼称は「学習者」に統一し「学生」は使わない。
# 「black box」の訳語は「ブラックボックス」に統一し「黒箱」は使わない。
#
# 対象: materials/, workbook/ 配下の Markdown（*.md）のみ。原稿とスケルトン
# コード（*.py / *.ml）のコメント・docstring は対象外（コード中の記述であり、
# 進行中の授業で既に配布済みのファイルを書き換える実利が薄いため）。
#
# materials/advanced/, workbook/advanced/ も対象に含める。ただし
# 「第N回」チェックだけは advanced 側で除外する: advanced の「Xシリーズの
# 第N回」（F/O/S/R/Q/B の各ファミリ内での位置）は、コマ1〜15 を指す「第NN回」
# とは無関係な別の数え方であり、正当な出現のため。
#
# advanced 配下限定の追加規約:
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
STYLE_KUROBAKO_RE = re.compile(r"黒箱")

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


# ── チェック6: ISO C 例外の宣言件数と見出し数の一致 ──
#
# language_spec.md の冒頭は「N 件の例外(後述)を除き」と件数を宣言している。
# 例外を1つ足したのに冒頭の件数を直し忘れると、規範文書が自分自身と矛盾する
# （実際に例外を1つ追加した際、冒頭の件数表記が古いまま取り残されたことがあった）。
# 両者を突き合わせる。

EXC_COUNT_RE = re.compile(r"(\d+)\s*件の例外")
EXC_HEADING_RE = re.compile(r"^\*\*例外 E(\d+) —")


def check_exception_count() -> list[Violation]:
    violations: list[Violation] = []
    if not LANG_SPEC_PATH.is_file():
        return violations
    lines = LANG_SPEC_PATH.read_text(encoding="utf-8").splitlines()

    declared: list[tuple[int, int]] = []
    headings: list[tuple[int, int]] = []
    for i, line in enumerate(lines, 1):
        m = EXC_COUNT_RE.search(line)
        if m:
            declared.append((i, int(m.group(1))))
        h = EXC_HEADING_RE.match(line)
        if h:
            headings.append((i, int(h.group(1))))

    if not headings:
        return violations

    ids = [n for _, n in headings]
    expected = list(range(1, len(ids) + 1))
    if ids != expected:
        violations.append(Violation(
            LANG_SPEC_PATH, headings[0][0],
            f"例外の番号が連番でない: E{ids} （E{expected} のはず）",
        ))

    for line_no, count in declared:
        if count != len(headings):
            violations.append(Violation(
                LANG_SPEC_PATH, line_no,
                f"宣言された例外の件数 {count} が、実際の見出し数 "
                f"{len(headings)} と一致しない",
            ))
    return violations


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
        if (STYLE_HATTEN_XN_RE.search(line)
                and not allowlist.matches(rel, line, "hatten-xn")):
            violations.append(Violation(
                path, i,
                f"「発展 XN」表記の残存（「発展課題 XN」を使う）: {line.strip()}",
            ))
        if (STYLE_SENTAKUSEI_RE.search(line)
                and not allowlist.matches(rel, line, "sentakusei")):
            violations.append(Violation(
                path, i, f"「（選択制）」の残存（索引で既に宣言済みなので削る）: {line.strip()}",
            ))
        if (STYLE_BACKEND_SERIES_RE.search(line)
                and not allowlist.matches(rel, line, "backend-series")):
            violations.append(Violation(
                path, i,
                "「バックエンド発展シリーズ」の残存"
                f"（「最適化入門発展シリーズ」を使う）: {line.strip()}",
            ))
        masked = _style_mask_protected(line)
        if (("(" in masked or ")" in masked)
                and not allowlist.matches(rel, line, "hankaku-paren")):
            violations.append(Violation(
                path, i, f"半角括弧の残存（全角（）を使う）: {line.strip()}",
            ))
        masked_scaffold = _STYLE_SPAN_RE.sub(
            lambda m: "\x00" * len(m.group(0)), line
        )
        if (_STYLE_SCAFFOLD_RE.search(masked_scaffold)
                and not allowlist.matches(rel, line, "scaffold-hyoki")):
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
        if (not advanced and STYLE_DAI_KAI_RE.search(line)
                and not allowlist.matches(rel, line, "dai-kai")):
            violations.append(Violation(
                path, i, f"「第NN回」表記の残存（「コマN」を使う）: {line.strip()}",
            ))
        if (STYLE_KOMA_ZERO_RE.search(line)
                and not allowlist.matches(rel, line, "koma-zero-pad")):
            violations.append(Violation(
                path, i, f"「コマN」のゼロ埋めの残存: {line.strip()}",
            ))
        if (STYLE_KOMA_SPACE_RE.search(line)
                and not allowlist.matches(rel, line, "koma-space")):
            violations.append(Violation(
                path, i, f"「コマ」と数字の間の空白の残存: {line.strip()}",
            ))
        if (STYLE_GAKUSEI_RE.search(line)
                and not allowlist.matches(rel, line, "gakusei")):
            violations.append(Violation(
                path, i, f"「学生」表記の残存（「学習者」を使う）: {line.strip()}",
            ))
        if (STYLE_KUROBAKO_RE.search(line)
                and not allowlist.matches(rel, line, "kurobako")):
            violations.append(Violation(
                path, i, f"「黒箱」表記の残存（「ブラックボックス」を使う）: {line.strip()}",
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


# ── チェック7: code_example.md の C コードブロックを処理系に通す ──
#
# code_example.md は「各コマ終了時点でコンパイルできる最も複雑なプログラム」を
# 示す文書で、各例に期待する終了コード・標準出力まで書いてある。人手では検算
# されないので、仕様から外れた構文（かつてのブロックコメントなど）や、書き換えの
# ときに直し忘れた期待値が残る。ここでは文書からコードブロックを取り出し、
#
#   前段（parse）: 提供物の Lexer/Parser（workbook/scaffold）に通す。追加の
#                  依存が要らないので CI でも常に走る。仕様外の構文はここで落ちる
#   後段（exec）:  処理系でアセンブリまで落とし、riscv64 gcc と qemu で実行して
#                  期待する終了コード・標準出力と突き合わせる。処理系と RV64
#                  ツールチェーンが揃っているときだけ走り、無ければスキップする
#
# を行う。後段の処理系は既定で公開されている OCaml 参考実装
# （workbook/ocaml/reference/mycc_ref.exe。`cd workbook/ocaml && dune build` で
# 作る）を使う。CHECK_DOCS_COMPILER 環境変数で別の処理系（例: 非公開の Python
# 完成版 mycc.py）を指定できる。標準トラックの workbook/final/mycc.py は
# 統合先のプレースホルダーで動く処理系ではないため、既定にはしない。

CODE_EXAMPLE_PATH = ROOT / "workbook" / "docs" / "code_example.md"
SCAFFOLD_DIR = ROOT / "workbook" / "scaffold"
OCAML_REF_EXE = ROOT / "workbook" / "ocaml" / "_build" / "default" / "reference" / "mycc_ref.exe"

CE_FENCE_RE = re.compile(r"^```(\w*)\s*$")
CE_FILENAME_RE = re.compile(r"^//\s*([A-Za-z0-9_]+\.[ch])\s*$")
CE_EXIT_RE = re.compile(r"期待する終了コード:\s*`(-?\d+)`")
CE_STDOUT_INLINE_RE = re.compile(r"期待する標準出力:\s*`([^`]*)`")
CE_STDOUT_BLOCK_RE = re.compile(r"期待する標準出力:\s*$")

# 実行検証に必要な外部コマンド
CE_ASSEMBLER = "riscv64-linux-gnu-gcc"
CE_RUNNER = "qemu-riscv64"

# 各チェックが出す補足（違反ではないが伝えたいこと）。main() が結果行の下に出す。
NOTES: list[str] = []


class CodeBlock:
    def __init__(self, section: str, lang: str, start: int, end: int, body: list[str]):
        self.section = section
        self.lang = lang
        self.start = start        # 開始フェンスの行番号（1 始まり）
        self.end = end            # 終了フェンスの行番号
        self.body = body
        self.name: str | None = None
        self.exit_code: int | None = None
        self.stdout: str | None = None


def extract_code_blocks(lines: list[str]) -> list[CodeBlock]:
    """フェンス付きコードブロックを文書順に取り出す。"""
    blocks: list[CodeBlock] = []
    section = ""
    i, n = 0, len(lines)
    while i < n:
        if lines[i].startswith("## "):
            section = lines[i][3:].strip()
            i += 1
            continue
        m = CE_FENCE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        j = i + 1
        while j < n and lines[j].strip() != "```":
            j += 1
        blocks.append(CodeBlock(section, m.group(1), i + 1, j + 1, lines[i + 1:j]))
        i = j + 1
    return blocks


def annotate_code_blocks(blocks: list[CodeBlock], lines: list[str]) -> None:
    """C ブロックに仮想ファイル名と期待値を付ける。

    ブロック先頭の `// name.c` 行はファイル名の宣言として扱う（コマ14 の
    複数ファイル例がこの形）。期待値は、そのブロックの後から次のブロック
    （または次の見出し・区切り線）までの範囲に書かれたものを拾う。
    """
    n = len(lines)
    for idx, block in enumerate(blocks):
        if block.lang != "c":
            continue
        if block.body:
            m = CE_FILENAME_RE.match(block.body[0].strip())
            if m:
                block.name = m.group(1)
        stop = blocks[idx + 1].start - 1 if idx + 1 < len(blocks) else n
        k = block.end
        while k < stop:
            text = lines[k]
            if text.startswith("## ") or text.strip() == "---":
                break
            m = CE_EXIT_RE.search(text)
            if m:
                block.exit_code = int(m.group(1))
            m = CE_STDOUT_INLINE_RE.search(text)
            if m:
                block.stdout = m.group(1) + "\n"
            elif CE_STDOUT_BLOCK_RE.search(text):
                # 直後の言語指定なしフェンスが期待する標準出力そのもの
                if idx + 1 < len(blocks) and blocks[idx + 1].lang == "":
                    block.stdout = "\n".join(blocks[idx + 1].body) + "\n"
            k += 1


def group_code_blocks(blocks: list[CodeBlock]) -> list[list[CodeBlock]]:
    """1つのプログラムを成すブロックをまとめる。

    ファイル名を宣言したブロックは、同じ節にある限り1つのプログラム
    （コマ14 の math_util.h / math_util.c / main.c）として束ねる。
    """
    groups: list[list[CodeBlock]] = []
    current: list[CodeBlock] | None = None
    for block in blocks:
        if block.lang != "c":
            continue
        if block.name and current and current[0].name and current[0].section == block.section:
            current.append(block)
            continue
        current = [block]
        groups.append(current)
    return groups


def _exec_compiler_argv() -> list[str] | None:
    """後段（実行検証）で使う処理系のコマンド。使えなければ None。"""
    override = os.environ.get("CHECK_DOCS_COMPILER")
    if override:
        return shlex.split(override)
    if OCAML_REF_EXE.is_file():
        return [str(OCAML_REF_EXE), "--no-comments"]
    return None


def _write_group(tmpdir: Path, group: list[CodeBlock]) -> list[Path]:
    """グループのブロックを一時ディレクトリに書き出す。lib.h も同居させる。"""
    libh = SCAFFOLD_DIR / "lib.h"
    if libh.is_file():
        shutil.copy(libh, tmpdir / "lib.h")
    paths = []
    for block in group:
        name = block.name or f"block_{block.start}.c"
        path = tmpdir / name
        path.write_text("\n".join(block.body) + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def _parse_code_block(path: Path) -> str | None:
    """提供物の Lexer/Parser に通す。通れば None、落ちればその理由を返す。"""
    sys.path.insert(0, str(SCAFFOLD_DIR))
    try:
        from lexer import preprocess, tokenize  # noqa: PLC0415
        from parser import parse                # noqa: PLC0415
        source = path.read_text(encoding="utf-8")
        parse(tokenize(preprocess(source, str(path)), str(path)))
    except SystemExit:
        # scaffold の字句・構文エラーは exit(1) で落ちる。直前に stderr へ
        # 詳細を出しているので、ここでは種別だけ伝える
        return "Lexer/Parser が受理しなかった（詳細は直前の標準エラー出力）"
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"
    finally:
        if sys.path and sys.path[0] == str(SCAFFOLD_DIR):
            sys.path.pop(0)
    return None


def _run_code_group(tmpdir: Path, paths: list[Path], compiler: list[str]) -> tuple[int, str] | str:
    """処理系 → アセンブル → 実行。(終了コード, 標準出力) か、失敗理由を返す。"""
    sources = [str(p) for p in paths if p.suffix == ".c"]
    asm = tmpdir / "out.s"
    exe = tmpdir / "out.bin"
    r = subprocess.run([*compiler, *sources], capture_output=True, text=True)
    if r.returncode != 0:
        return f"処理系が失敗した: {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ''}"
    asm.write_text(r.stdout, encoding="utf-8")
    r = subprocess.run(
        [CE_ASSEMBLER, "-x", "assembler", "-static", str(asm), "-o", str(exe)],
        capture_output=True, text=True)
    if r.returncode != 0:
        return f"アセンブルに失敗した: {r.stderr.strip()[:200]}"
    try:
        r = subprocess.run([CE_RUNNER, str(exe)], capture_output=True, text=True,
                           timeout=30)
    except subprocess.TimeoutExpired:
        return "実行がタイムアウトした（30 秒）"
    return (r.returncode, r.stdout)


def check_code_examples() -> list[Violation]:
    violations: list[Violation] = []
    if not CODE_EXAMPLE_PATH.is_file():
        return violations
    allowlist = Allowlist(_load_allowlist_section("code_examples"), "code_examples")
    rel = CODE_EXAMPLE_PATH.relative_to(ROOT).as_posix()
    lines = CODE_EXAMPLE_PATH.read_text(encoding="utf-8").splitlines()
    blocks = extract_code_blocks(lines)
    annotate_code_blocks(blocks, lines)
    groups = group_code_blocks(blocks)

    compiler = _exec_compiler_argv()
    can_exec = bool(compiler) and all(
        shutil.which(cmd) for cmd in (CE_ASSEMBLER, CE_RUNNER))
    if not can_exec:
        missing = []
        if not compiler:
            missing.append(
                "処理系（workbook/ocaml で dune build するか CHECK_DOCS_COMPILER を指定）")
        missing += [c for c in (CE_ASSEMBLER, CE_RUNNER) if not shutil.which(c)]
        NOTES.append(
            f"C ブロック {len(groups)} 本の構文だけ検査した。"
            f"実行検証は未実施（不足: {' / '.join(missing)}）")

    executed = 0
    for group in groups:
        head = group[0]
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            paths = _write_group(tmpdir, group)
            broken = False
            for path, block in zip(paths, group):
                reason = _parse_code_block(path)
                if reason and not allowlist.matches(rel, block.body[0] if block.body else "", "parse"):
                    violations.append(Violation(
                        CODE_EXAMPLE_PATH, block.start,
                        f"C コードブロックが処理系のフロントエンドを通らない: {reason}"))
                    broken = True
            if broken or not can_exec:
                continue
            last = group[-1]
            if last.exit_code is None and last.stdout is None:
                continue
            result = _run_code_group(tmpdir, paths, compiler)
            if isinstance(result, str):
                violations.append(Violation(
                    CODE_EXAMPLE_PATH, head.start,
                    f"C コードブロックを実行できない: {result}"))
                continue
            code, out = result
            executed += 1
            if last.exit_code is not None and code != last.exit_code:
                violations.append(Violation(
                    CODE_EXAMPLE_PATH, last.start,
                    f"期待する終了コード {last.exit_code} に対し実際は {code}"))
            if last.stdout is not None and out != last.stdout:
                violations.append(Violation(
                    CODE_EXAMPLE_PATH, last.start,
                    f"期待する標準出力 {last.stdout!r} に対し実際は {out!r}"))
    if can_exec:
        NOTES.append(
            f"C ブロック {len(groups)} 本を構文検査し、"
            f"うち期待値の書かれた {executed} 本を実行して終了コード・標準出力を照合した")
    violations.extend(_dead_allowlist_violations(allowlist))
    return violations


# ── チェック8: 規約文書が挙げる識別子の実在確認 ──
#
# conventions.md の「命名の目安」表・testing.md の症状表・scaffold/README.md の
# ファイル一覧は、実装側の名前を名指しする。名前が変わったのに文書が古いままだと、
# 学習者は存在しないヘルパーを探すことになる。conventions.md:77 は `_push_a0` /
# `_pop_into` の名前固定を発展課題の動作条件にしているので、実利もある。
#
# 拾うのはインラインコード（`...`）のうち、Python の識別子として書かれたと
# 判断できるものだけに絞る:
#   - スネークケース（`size_of_ty_str`、`align_to`）
#   - 先頭アンダースコア（`_locals`）
#   - 呼び出しの形（`emit()`、`align_to(n, 16)` → 呼び出し先の名前を見る）
# レジスタ名（`a0`、`sp`）・引用符つきの過去の名前（`'_align_to'`）・パスを
# 含む表記（`sessions/NN_xxx/mycc.py`）は、この形に当てはまらないので拾わない。
# コードフェンスの中は対象外（説明用の擬似コードが混ざるため）。

IDENT_DOCS = [
    Path("workbook/docs/conventions.md"),
    Path("workbook/docs/testing.md"),
    Path("workbook/scaffold/README.md"),
]
IDENT_SOURCE_DIRS = [Path("workbook/sessions"), Path("workbook/scaffold")]

IDENT_SPAN_RE = re.compile(r"`([^`\n]+)`")
IDENT_CALL_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\([^()]*\)$")
IDENT_SNAKE_RE = re.compile(r"^_?[a-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+$")
IDENT_UNDER_RE = re.compile(r"^_[a-z][a-z0-9]*$")
IDENT_BARE_RE = re.compile(r"^[a-z][a-z0-9]*$")
IDENT_FILE_RE = re.compile(r"^([A-Za-z0-9_]+\.(?:py|h))$")


def _identifier_candidates(line: str) -> tuple[set[str], set[str]]:
    """1行から (識別子名, ファイル名) の候補を返す。"""
    idents: set[str] = set()
    files: set[str] = set()
    for span in IDENT_SPAN_RE.findall(line):
        m = IDENT_FILE_RE.match(span)
        if m:
            files.add(m.group(1))
            continue
        m = IDENT_CALL_RE.match(span)
        name, called = (m.group(1), True) if m else (span, False)
        if (IDENT_SNAKE_RE.match(name) or IDENT_UNDER_RE.match(name)
                or (called and IDENT_BARE_RE.match(name))):
            idents.add(name)
    return idents, files


def check_identifiers() -> list[Violation]:
    violations: list[Violation] = []
    allowlist = Allowlist(_load_allowlist_section("identifiers"), "identifiers")

    sources: list[str] = []
    scaffold_files: set[str] = set()
    for base in IDENT_SOURCE_DIRS:
        d = ROOT / base
        if not d.is_dir():
            continue
        for path in sorted(d.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRNAMES for part in path.relative_to(ROOT).parts):
                continue
            scaffold_files.add(path.name)
            if path.suffix in {".py", ".h"}:
                try:
                    sources.append(path.read_text(encoding="utf-8"))
                except UnicodeDecodeError:
                    continue
    if not sources:
        return violations
    corpus = "\n".join(sources)

    checked = 0
    for rel_doc in IDENT_DOCS:
        doc = ROOT / rel_doc
        if not doc.is_file():
            continue
        rel = rel_doc.as_posix()
        in_fence = False
        for i, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            idents, files = _identifier_candidates(line)
            for name in sorted(idents):
                checked += 1
                if re.search(r"\b" + re.escape(name) + r"\b", corpus):
                    continue
                if allowlist.matches(rel, line, "missing-identifier"):
                    continue
                violations.append(Violation(
                    doc, i,
                    f"文書が挙げる識別子 `{name}` が "
                    "workbook/sessions/・workbook/scaffold/ に存在しない"))
            for name in sorted(files):
                checked += 1
                if name in scaffold_files:
                    continue
                if allowlist.matches(rel, line, "missing-file"):
                    continue
                violations.append(Violation(
                    doc, i,
                    f"文書が挙げるファイル `{name}` が "
                    "workbook/sessions/・workbook/scaffold/ に存在しない"))
    NOTES.append(f"{len(IDENT_DOCS)} 文書から {checked} 個の名前を突き合わせた")
    violations.extend(_dead_allowlist_violations(allowlist))
    return violations


# ── チェック9: 各コマの EBNF スナップショットの単調性 ──
#
# materials/sessions/01〜14 の「### この回までの言語仕様（EBNF）」節にある
# ```ebnf ブロックは「その回までに書ける文法」の累積スナップショットである。
# 回を追うごとに単調に増えるはずで、後の回で選択肢が消えるのは誤りである
# （例外は下の GRAMMAR_REFINEMENTS に列挙した「右辺の精密化」だけ）。
# 次の3点を検査する:
#   (a) 単調性     コマN の選択肢集合 ⊆ コマN+1 の選択肢集合
#                  （消えてよいのは GRAMMAR_REFINEMENTS の 12 件のみ）
#   (b) 最終形一致 コマ14 の集合が language_spec.md「## 形式文法（EBNF）」節と
#                  一致する（字句トークン節は各コマが省略するため対象外）。
#                  T156 分割書は前処理指令 include_dir / define_dir の差分を
#                  許容してよいとしたが、実際にはコマ13 の全文＋コマ14 の差分が
#                  前処理指令まで含めて最終形と完全一致するため、例外を設けず
#                  厳密一致で検査する（例外を設けるとコマ14 の差分ブロックが
#                  丸ごと検査対象外になってしまう）
#   (c) 参照閉包   スナップショットの右辺に現れる非終端記号（小文字始まり）が
#                  すべて同じスナップショット内で定義されている
#
# コマ14 は差分だけを載せる（前処理指令のみ）ため、コマ13 の集合に対して
# コマ14 のブロックが定義する規則を差し替えたものを「コマ14 の集合」とする。

GRAMMAR_HEADING = "### この回までの言語仕様（EBNF）"
GRAMMAR_SPEC_HEADING = "## 形式文法（EBNF）"
GRAMMAR_SPEC_SKIP_SUBHEADINGS = {"### 字句トークン"}
GRAMMAR_LAST_SESSION = 14
# コマ14 は差分掲載（下記コマの番号は「ブロックが全文ではない回」）
GRAMMAR_DIFF_SESSIONS = {14}

# 回をまたいで右辺が「置き換わる」箇所。素朴な部分集合判定では削除と
# 誤検知されるため、(消える回, 規則名, 精密化前, 精密化後) を許可リストに置く。
# 出典: c-comp-design/tasks/T156_ebnf_snapshot_breakdown.md「精密化許可リスト」。
GRAMMAR_REFINEMENTS: tuple[tuple[int, str, str, str], ...] = (
    (2, "func_body", "'{' { stmt } '}'", "'{' { var_decl } { stmt } '}'"),
    (2, "expr", "add_expr", "assign_expr"),
    (6, "stmt", "'return' expr ';'", "'return' [ expr ] ';'"),
    (5, "func_def", "'int' 'main' '(' ')' func_body",
     "ret_type IDENT '(' [ param_list ] ')' func_body"),
    (4, "expr_stmt", "expr ';'", "[ expr ] ';'"),
    (6, "scalar_type", "'int'", "'int' [ stars ]"),
    (8, "stars", "'*'", "'*' { '*' }"),
    (12, "cond_expr", "eq_expr [ '?' expr ':' cond_expr ]",
     "lor_expr [ '?' expr ':' cond_expr ]"),
    (8, "unary_expr", "primary_expr", "postfix_expr"),
    (3, "assign_expr", "add_expr", "cond_expr"),
    (5, "program", "func_def", "external_decl { external_decl }"),
    (9, "func_proto", "ret_type IDENT '(' [ param_list ] ')' ';'",
     "ret_type IDENT '(' [ param_list [ ',' '...' ] ] ')' ';'"),
)

GRAMMAR_COMMENT_RE = re.compile(r"/\*.*?\*/")
GRAMMAR_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
GRAMMAR_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _grammar_normalize(text: str) -> str:
    """コメントを落とし空白を正規化した右辺の文字列を返す。"""
    return re.sub(r"\s+", " ", GRAMMAR_COMMENT_RE.sub(" ", text)).strip()


def parse_ebnf_block(body: list[str], start_line: int) -> tuple[
        list[tuple[str, str]], dict[str, int], list[str]]:
    """```ebnf ブロックから (規則名, 選択肢) の並び・定義行番号・書式違反を返す。"""
    alts: list[tuple[str, str]] = []
    defined: dict[str, int] = {}
    problems: list[str] = []
    current: str | None = None
    for offset, raw in enumerate(body):
        line = _grammar_normalize(raw)
        if not line:
            continue
        lineno = start_line + offset
        if "::=" in line:
            lhs, rhs = line.split("::=", 1)
            current = lhs.strip()
            if not current or " " in current:
                problems.append(f"{lineno}: 規則名として解釈できない `{lhs.strip()}`")
                current = None
                continue
            defined.setdefault(current, lineno)
            rhs = rhs.strip()
            if rhs:
                alts.append((current, rhs))
            continue
        if line.startswith("|"):
            if current is None:
                problems.append(f"{lineno}: 規則名の無い選択肢行 `{line}`")
                continue
            rhs = line[1:].strip()
            if rhs:
                alts.append((current, rhs))
            continue
        problems.append(f"{lineno}: `::=` でも行頭 `|` でもない行 `{line}`")
    return alts, defined, problems


def _grammar_nonterminals(alt: str) -> set[str]:
    """選択肢の右辺に現れる非終端記号（小文字始まり）を返す。"""
    stripped = GRAMMAR_QUOTED_RE.sub(" ", alt)
    return {w for w in GRAMMAR_WORD_RE.findall(stripped) if w[:1].islower()}


def _grammar_session_paths() -> dict[int, Path]:
    paths: dict[int, Path] = {}
    if not MATERIALS_SESSIONS.is_dir():
        return paths
    for path in sorted(MATERIALS_SESSIONS.glob("*.md")):
        m = re.match(r"^(\d\d)_", path.name)
        if not m:
            continue
        n = int(m.group(1))
        if 1 <= n <= GRAMMAR_LAST_SESSION:
            paths[n] = path
    return paths


def _extract_ebnf_after(lines: list[str], heading_idx: int,
                        stop_pred=None) -> tuple[list[str], int] | None:
    """heading_idx の次から最初に現れる ```ebnf ブロックを返す（内容, 開始行番号）。"""
    i = heading_idx + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if stop_pred is not None and stop_pred(stripped):
            return None
        if stripped == "```ebnf":
            end = next((j for j in range(i + 1, len(lines))
                        if lines[j].strip() == "```"), None)
            if end is None:
                return None
            return lines[i + 1:end], i + 2
        i += 1
    return None


def _grammar_spec_alternatives() -> tuple[list[tuple[str, str]], dict[str, int],
                                          list[str]] | None:
    """language_spec.md の最終形 EBNF（字句トークン節を除く）を返す。"""
    if not LANG_SPEC_PATH.is_file():
        return None
    lines = LANG_SPEC_PATH.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines)
                  if line.strip() == GRAMMAR_SPEC_HEADING), None)
    if start is None:
        return None
    alts: list[tuple[str, str]] = []
    defined: dict[str, int] = {}
    problems: list[str] = []
    subheading = ""
    i = start + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("### "):
            subheading = stripped
        if stripped == "```ebnf":
            end = next((j for j in range(i + 1, len(lines))
                        if lines[j].strip() == "```"), None)
            if end is None:
                break
            if subheading not in GRAMMAR_SPEC_SKIP_SUBHEADINGS:
                b_alts, b_defined, b_problems = parse_ebnf_block(
                    lines[i + 1:end], i + 2)
                alts.extend(b_alts)
                for name, lineno in b_defined.items():
                    defined.setdefault(name, lineno)
                problems.extend(b_problems)
            i = end
        i += 1
    return alts, defined, problems


def check_grammar_snapshots() -> list[Violation]:
    violations: list[Violation] = []
    paths = _grammar_session_paths()
    missing = [n for n in range(1, GRAMMAR_LAST_SESSION + 1) if n not in paths]
    if missing:
        return violations  # 原稿が揃っていない環境では検査しない

    blocks: dict[int, tuple[list[tuple[str, str]], dict[str, int]]] = {}
    for n in range(1, GRAMMAR_LAST_SESSION + 1):
        path = paths[n]
        lines = path.read_text(encoding="utf-8").splitlines()
        heading_idx = next((i for i, line in enumerate(lines)
                            if line.strip() == GRAMMAR_HEADING), None)
        if heading_idx is None:
            violations.append(Violation(
                path, 1, f"「{GRAMMAR_HEADING}」の節が無い"))
            continue
        block = _extract_ebnf_after(
            lines, heading_idx,
            stop_pred=lambda s: s.startswith("## ") or s.startswith("### "))
        if block is None:
            violations.append(Violation(
                path, heading_idx + 1,
                f"「{GRAMMAR_HEADING}」の直後に ```ebnf ブロックが見つからない"))
            continue
        body, start_line = block
        alts, defined, problems = parse_ebnf_block(body, start_line)
        for problem in problems:
            lineno, _, msg = problem.partition(": ")
            violations.append(Violation(path, int(lineno), "EBNF の書式違反: " + msg))
        blocks[n] = (alts, defined)

    if len(blocks) != GRAMMAR_LAST_SESSION:
        return violations

    # 累積集合を作る（コマ14 は差分掲載なのでコマ13 の集合へ重ねる）。
    # 規則の定義位置は (ファイル, 行) で持つ。コマ14 が引き継いだ規則の違反を
    # コマ14 の原稿の無関係な行に貼り付けないため。
    cumulative: dict[int, set[tuple[str, str]]] = {}
    cum_defined: dict[int, dict[str, tuple[Path, int]]] = {}
    for n in range(1, GRAMMAR_LAST_SESSION + 1):
        alts, defined = blocks[n]
        own = {rule: (paths[n], lineno) for rule, lineno in defined.items()}
        if n in GRAMMAR_DIFF_SESSIONS and n - 1 in cumulative:
            merged = {(r, a) for (r, a) in cumulative[n - 1] if r not in defined}
            merged |= set(alts)
            merged_defined = dict(cum_defined[n - 1])
            merged_defined.update(own)
        else:
            merged = set(alts)
            merged_defined = own
        cumulative[n] = merged
        cum_defined[n] = merged_defined

    def where(n: int, rule: str) -> tuple[Path, int]:
        return cum_defined[n].get(rule, (paths[n], 1))

    # (c) 参照閉包
    for n in range(1, GRAMMAR_LAST_SESSION + 1):
        defined = cum_defined[n]
        for rule, alt in sorted(cumulative[n]):
            for name in sorted(_grammar_nonterminals(alt)):
                if name in defined:
                    continue
                path, lineno = where(n, rule)
                violations.append(Violation(
                    path, lineno,
                    f"参照閉包の違反: コマ{n} のスナップショットの "
                    f"`{rule} ::= {alt}` が参照する非終端記号 `{name}` が "
                    "そのスナップショットに定義されていない"))

    # (a) 単調性
    refinements = {(n, rule, before): after
                   for (n, rule, before, after) in GRAMMAR_REFINEMENTS}
    used: set[tuple[int, str, str]] = set()
    for n in range(1, GRAMMAR_LAST_SESSION):
        removed = sorted(cumulative[n] - cumulative[n + 1])
        for rule, alt in removed:
            key = (n, rule, alt)
            after = refinements.get(key)
            path, lineno = where(n + 1, rule)
            if after is None:
                violations.append(Violation(
                    path, lineno,
                    f"単調性の違反: コマ{n} にある `{rule} ::= {alt}` が "
                    f"コマ{n + 1} で消えている（精密化許可リストに無い）"))
                continue
            if (rule, after) not in cumulative[n + 1]:
                violations.append(Violation(
                    path, lineno,
                    f"精密化の違反: コマ{n} の `{rule} ::= {alt}` は "
                    f"コマ{n + 1} で `{after}` に精密化されるはずだが見当たらない"))
                continue
            used.add(key)
    for key in sorted(set(refinements) - used):
        n, rule, before = key
        violations.append(Violation(
            paths.get(n, MATERIALS_SESSIONS), 1,
            f"精密化許可リストの死んだ項目: コマ{n} → コマ{n + 1} の "
            f"`{rule} ::= {before}` の置換が実際には起きていない"))

    # (b) コマ14 と最終形 EBNF の一致
    spec = _grammar_spec_alternatives()
    if spec is None:
        violations.append(Violation(
            LANG_SPEC_PATH, 1, f"「{GRAMMAR_SPEC_HEADING}」節の EBNF を読み取れない"))
    else:
        spec_alts, spec_defined, spec_problems = spec
        for problem in spec_problems:
            lineno, _, msg = problem.partition(": ")
            violations.append(Violation(
                LANG_SPEC_PATH, int(lineno), "EBNF の書式違反: " + msg))
        spec_set = set(spec_alts)
        last = cumulative[GRAMMAR_LAST_SESSION]
        for rule, alt in sorted(spec_set - last):
            violations.append(Violation(
                LANG_SPEC_PATH, spec_defined.get(rule, 1),
                f"最終形との不一致: `{rule} ::= {alt}` が最終形にあって "
                f"コマ{GRAMMAR_LAST_SESSION} のスナップショットに無い"))
        for rule, alt in sorted(last - spec_set):
            path, lineno = where(GRAMMAR_LAST_SESSION, rule)
            violations.append(Violation(
                path, lineno,
                f"最終形との不一致: `{rule} ::= {alt}` がコマ"
                f"{GRAMMAR_LAST_SESSION} のスナップショットにあって最終形に無い"))
        NOTES.append(f"最終形 EBNF の選択肢 {len(spec_set)} 個と突き合わせた")

    NOTES.append(
        f"{GRAMMAR_LAST_SESSION} コマのスナップショットから "
        f"{sum(len(cumulative[n]) for n in cumulative)} 個の選択肢を抽出し、"
        f"精密化 {len(used)}/{len(refinements)} 件を確認した")
    return violations


CHECKS = {
    "tests": ("原稿とテスト実体の突合", check_test_tables),
    "terms": ("旧仕様語の検出", check_legacy_terms),
    "nav": ("nav.yaml 未掲載の検出", check_nav_listing),
    "libh": ("lib.h と仕様書の宣言一致", check_libh_sync),
    "style": ("用語・表記の統一", check_style_terms),
    "exc": ("ISO C 例外の件数と見出しの一致", check_exception_count),
    "codeexec": ("code_example.md のコード実行", check_code_examples),
    "ident": ("規約文書が挙げる識別子の実在", check_identifiers),
    "grammar": ("各コマの EBNF スナップショットの単調性", check_grammar_snapshots),
}


def print_allowlist() -> None:
    empty = True
    for section in ALLOWLIST_KINDS:
        entries = _load_allowlist_section(section)
        if not entries:
            continue
        empty = False
        print(f"{section} 除外リスト {len(entries)} 件:")
        for entry in entries:
            status = entry.get("status", "?")
            check = entry.get("check", "?")
            if not isinstance(check, str):
                check = ",".join(check)
            reason = " ".join(entry.get("reason", "").split())
            print(f"  [{status}] <{check}> {entry['file']}  "
                  f"{entry.get('match', '')}  {reason}")
    if empty:
        print("除外リストは空。")


def print_allowlist_kinds() -> None:
    print("除外リストの check: に書ける検出種別:")
    for section, kinds in ALLOWLIST_KINDS.items():
        print(f"  {section}: {', '.join(sorted(kinds))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help=f"実行するチェック（カンマ区切り: {','.join(CHECKS)}）")
    parser.add_argument("--list-allowed", action="store_true",
                        help="除外リストの内容を表示して終了する")
    parser.add_argument("--list-kinds", action="store_true",
                        help="除外リストに書ける検出種別を表示して終了する")
    args = parser.parse_args()

    if args.list_allowed:
        print_allowlist()
        return 0

    if args.list_kinds:
        print_allowlist_kinds()
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
        NOTES.clear()
        violations = func()
        if violations:
            print(f"\n[{name}] {title}: {len(violations)} 件の違反")
            for v in violations:
                print(f"  {v}")
            total += len(violations)
        else:
            print(f"[{name}] {title}: 違反なし")
        for note in NOTES:
            print(f"       … {note}")

    if total:
        print(f"\n合計 {total} 件の違反")
        return 1
    print("\nすべてのチェックを通過")
    return 0


if __name__ == "__main__":
    sys.exit(main())
