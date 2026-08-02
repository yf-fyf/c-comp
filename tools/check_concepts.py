#!/usr/bin/env python3
"""概念導入台帳（design/curriculum.md）と各回の原稿 frontmatter の整合を検査する。

使い方:
    python3 tools/check_concepts.py           # 検査する
    python3 tools/check_concepts.py --show    # 各回の introduces / requires を表示する

検査内容:
    1. 台帳の概念IDが一意で、識別子として妥当であること
    2. 台帳の前提概念がすべて台帳に存在し、導入コマが後戻りしていないこと
    3. 台帳の導入コマが実在する回であること（07 は欠番）
    4. 全回の原稿に YAML frontmatter があり、introduces / requires を持つこと
    5. 原稿の introduces が、台帳でその回に割り当てられた概念と順序まで一致すること
    6. 原稿の requires が、introduces の前提概念から導出した値と一致すること
       （導出 = 各概念の前提概念の和集合 − 同じ回で導入する概念）
    7. requires の各概念が、より前の回で導入済みであること

分割回・統合回（`10a_types.md` や `12plus13_struct_malloc_list.md` のように、
数字2桁のあとが `_` で始まらない原稿）は上の 4〜7 の対象外で、代わりに次を検査する。
台帳は元のコマ番号のままで、分割・統合の割り当ては原稿の frontmatter が持つ。

    8. 分割回の introduces を合わせると、元のコマの概念とちょうど一致すること
       （欠落・重複が無く、それぞれの並びが台帳の順であること）
    9. 統合回の introduces が、統合元のコマの概念を台帳の順に連結したものであること
   10. 分割回・統合回の requires が 6 と同じ規則で導出した値と一致すること
   11. 分割・統合を反映した並び（… → 10a → 10b → 11a → 11b → 12+13 → 14 …）でも
       requires が先行導入になっていること

台帳が単一の出典である。原稿の frontmatter は台帳から導出できる値しか持たない。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "design" / "curriculum.md"
SESSIONS = ROOT / "materials" / "sessions"
LEDGER_HEADING = "## 9. 概念導入台帳"

ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CODE_RE = re.compile(r"`([^`]+)`")
# 分割回 `10a_types.md` / 統合回 `12plus13_struct_malloc_list.md` のファイル名。
VARIANT_RE = re.compile(r"^(\d{2})(?:([a-z])|plus(\d{2}))_")


class Problem:
    def __init__(self, where: str, message: str):
        self.where = where
        self.message = message

    def __str__(self) -> str:
        return f"{self.where}: {self.message}"


class Concept:
    def __init__(self, cid: str, name: str, session: int, prereqs: list[str], line: int):
        self.cid = cid
        self.name = name
        self.session = session
        self.prereqs = prereqs
        self.line = line


class Variant:
    """分割回・統合回の原稿1本。`parents` は元のコマ番号。"""

    def __init__(self, vid: str, parents: list[int], suffix: str, path: Path):
        self.vid = vid
        self.parents = parents
        self.suffix = suffix
        self.path = path
        self.introduces: list[str] = []


def session_files() -> dict[int, Path]:
    """コマ番号 -> 原稿。ファイル名の先頭2桁を番号とする。"""
    found: dict[int, Path] = {}
    for path in sorted(SESSIONS.glob("*.md")):
        m = re.match(r"^(\d{2})_", path.name)
        if m:
            found[int(m.group(1))] = path
    return found


def variant_files() -> list[Variant]:
    """分割回・統合回の原稿。元のコマ番号の昇順・接尾辞の昇順で返す。"""
    found: list[Variant] = []
    for path in sorted(SESSIONS.glob("*.md")):
        m = VARIANT_RE.match(path.name)
        if not m:
            continue
        head = int(m.group(1))
        if m.group(2):
            found.append(Variant(f"{head:02d}{m.group(2)}", [head], m.group(2), path))
        else:
            parents = sorted({head, int(m.group(3))})
            found.append(Variant(f"{head:02d}plus{m.group(3)}", parents, "", path))
    found.sort(key=lambda v: (v.parents[0], v.suffix))
    return found


def parse_ledger(problems: list[Problem]) -> list[Concept]:
    lines = LEDGER.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith(LEDGER_HEADING):
            start = i
            break
    if start is None:
        problems.append(Problem(LEDGER.name, f"台帳の見出しが無い: {LEDGER_HEADING}"))
        return []

    concepts: list[Concept] = []
    seen: dict[str, Concept] = {}
    for offset, line in enumerate(lines[start:], start=start):
        if offset > start and line.startswith("## "):
            break
        if not line.startswith("| `"):
            continue
        # 表の中の `\|` はセル区切りではない（`||` 等をコード表記するための書き方）
        body = line.strip()
        body = body[1:] if body.startswith("|") else body
        body = body[:-1] if body.endswith("|") and not body.endswith("\\|") else body
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]
        if len(cells) != 4:
            problems.append(Problem(f"{LEDGER.name}:{offset + 1}", f"列数が4でない: {line}"))
            continue
        cid_cell, name, session_cell, prereq_cell = cells
        cid_m = CODE_RE.fullmatch(cid_cell)
        if not cid_m:
            problems.append(Problem(f"{LEDGER.name}:{offset + 1}", f"概念IDの書式が不正: {cid_cell}"))
            continue
        cid = cid_m.group(1)
        if not ID_RE.match(cid):
            problems.append(Problem(f"{LEDGER.name}:{offset + 1}", f"概念IDに使えない文字がある: {cid}"))
            continue
        if cid in seen:
            problems.append(Problem(
                f"{LEDGER.name}:{offset + 1}",
                f"概念IDが重複している: {cid}（{LEDGER.name}:{seen[cid].line} と同じ）"))
            continue
        if not session_cell.isdigit():
            problems.append(Problem(f"{LEDGER.name}:{offset + 1}", f"導入コマが数値でない: {session_cell}"))
            continue
        prereqs = [] if prereq_cell == "—" else CODE_RE.findall(prereq_cell)
        if prereq_cell != "—" and not prereqs:
            problems.append(Problem(f"{LEDGER.name}:{offset + 1}", f"前提概念の書式が不正: {prereq_cell}"))
            continue
        concept = Concept(cid, name, int(session_cell), prereqs, offset + 1)
        concepts.append(concept)
        seen[cid] = concept
    if not concepts:
        problems.append(Problem(LEDGER.name, "台帳に1行も無い"))
    return concepts


def check_ledger(concepts: list[Concept], sessions: dict[int, Path],
                 problems: list[Problem]) -> None:
    by_id = {c.cid: c for c in concepts}
    for c in concepts:
        where = f"{LEDGER.name}:{c.line}"
        if c.session not in sessions:
            problems.append(Problem(where, f"{c.cid}: 導入コマ {c.session} の原稿が無い"))
        for p in c.prereqs:
            if p not in by_id:
                problems.append(Problem(where, f"{c.cid}: 前提概念が台帳に無い: {p}"))
            elif by_id[p].session > c.session:
                problems.append(Problem(
                    where,
                    f"{c.cid}（コマ{c.session}）の前提 {p} が後のコマ{by_id[p].session}で導入されている"))
    order = [c.session for c in concepts]
    if order != sorted(order):
        problems.append(Problem(LEDGER.name, "台帳が導入コマの昇順に並んでいない"))


def parse_frontmatter(path: Path, problems: list[Problem]) -> dict[str, list[str]] | None:
    """`introduces:` / `requires:` だけを読む最小の YAML frontmatter パーサ。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        problems.append(Problem(path.name, "先頭に YAML frontmatter が無い"))
        return None
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        problems.append(Problem(path.name, "frontmatter が閉じていない"))
        return None

    data: dict[str, list[str]] = {}
    key = None
    for offset, raw in enumerate(lines[1:end], start=2):
        line = raw.rstrip()
        if not line:
            continue
        if re.match(r"^[a-z_]+:", line):
            key, _, rest = line.partition(":")
            rest = rest.strip()
            if rest == "[]":
                data[key] = []
                key = None
            elif rest:
                problems.append(Problem(f"{path.name}:{offset}", f"値はリストで書く: {line}"))
                key = None
            else:
                data[key] = []
        elif line.startswith("  - "):
            if key is None:
                problems.append(Problem(f"{path.name}:{offset}", f"キーの外に項目がある: {line}"))
                continue
            item = line[4:].strip()
            if not ID_RE.match(item):
                problems.append(Problem(f"{path.name}:{offset}", f"概念IDの書式が不正: {item}"))
                continue
            data[key].append(item)
        else:
            problems.append(Problem(f"{path.name}:{offset}", f"解釈できない行: {line}"))
    for required_key in ("introduces", "requires"):
        if required_key not in data:
            problems.append(Problem(path.name, f"frontmatter に {required_key}: が無い"))
            return None
    if lines[end + 1:end + 2] and lines[end + 1].strip() != "":
        problems.append(Problem(path.name, "frontmatter の直後に空行が無い"))
    return data


def derive_requires(concepts: list[Concept], introduces: list[str]) -> list[str]:
    """introduces から requires を導出する（前提概念の和集合 − 自身が導入する概念）。"""
    order = {c.cid: i for i, c in enumerate(concepts)}
    by_id = {c.cid: c for c in concepts}
    own = set(introduces)
    requires: set[str] = set()
    for cid in introduces:
        if cid not in by_id:
            continue
        for p in by_id[cid].prereqs:
            if p not in own and p in by_id:
                requires.add(p)
    return sorted(requires, key=lambda cid: order[cid])


def expected(concepts: list[Concept], session: int) -> tuple[list[str], list[str]]:
    introduces = [c.cid for c in concepts if c.session == session]
    return introduces, derive_requires(concepts, introduces)


def check_sessions(concepts: list[Concept], sessions: dict[int, Path],
                   problems: list[Problem]) -> None:
    by_id = {c.cid: c for c in concepts}
    for number, path in sorted(sessions.items()):
        data = parse_frontmatter(path, problems)
        if data is None:
            continue
        want_intro, want_req = expected(concepts, number)
        if data["introduces"] != want_intro:
            problems.append(Problem(
                path.name,
                "introduces が台帳と一致しない\n"
                f"    台帳: {want_intro}\n"
                f"    原稿: {data['introduces']}"))
        if data["requires"] != want_req:
            problems.append(Problem(
                path.name,
                "requires が台帳からの導出値と一致しない\n"
                f"    導出: {want_req}\n"
                f"    原稿: {data['requires']}"))
        for cid in data["requires"]:
            if cid not in by_id:
                problems.append(Problem(path.name, f"requires が台帳に無い概念を指している: {cid}"))
            elif by_id[cid].session >= number:
                problems.append(Problem(
                    path.name,
                    f"requires の {cid} はコマ{by_id[cid].session}導入で、先行していない"))


def new_track(sessions: dict[int, Path], variants: list[Variant]) -> list[str]:
    """分割・統合を反映した回の並び。分割回は元の位置に、統合回は最小の元の位置に置く。"""
    anchored: dict[int, list[Variant]] = {}
    replaced: set[int] = set()
    for v in variants:
        anchored.setdefault(v.parents[0], []).append(v)
        replaced.update(v.parents)
    order: list[str] = []
    for number in sorted(sessions):
        if number in anchored:
            order.extend(v.vid for v in anchored[number])
        elif number not in replaced:
            order.append(f"{number:02d}")
    return order


def check_variants(concepts: list[Concept], sessions: dict[int, Path],
                   variants: list[Variant], problems: list[Problem]) -> None:
    if not variants:
        return
    order = {c.cid: i for i, c in enumerate(concepts)}

    # 各原稿の introduces / requires を読み、requires の導出値と突き合わせる。
    frontmatter: dict[str, dict[str, list[str]]] = {}
    for v in variants:
        data = parse_frontmatter(v.path, problems)
        if data is None:
            continue
        frontmatter[v.vid] = data
        v.introduces = data["introduces"]
        want_req = derive_requires(concepts, v.introduces)
        if data["requires"] != want_req:
            problems.append(Problem(
                v.path.name,
                "requires が台帳からの導出値と一致しない\n"
                f"    導出: {want_req}\n"
                f"    原稿: {data['requires']}"))
        if sorted(v.introduces, key=lambda cid: order.get(cid, -1)) != v.introduces:
            problems.append(Problem(v.path.name, "introduces が台帳の順に並んでいない"))

    # 元のコマの概念を、分割回・統合回がちょうど覆っているか。
    groups: dict[tuple[int, ...], list[Variant]] = {}
    for v in variants:
        groups.setdefault(tuple(v.parents), []).append(v)
    for parents, members in sorted(groups.items()):
        want = [c.cid for c in concepts if c.session in parents]
        got: list[str] = []
        for v in members:
            got.extend(v.introduces)
        where = " / ".join(v.path.name for v in members)
        label = "+".join(str(p) for p in parents)
        missing = [cid for cid in want if cid not in set(got)]
        extra = [cid for cid in got if cid not in set(want)]
        dupes = sorted({cid for cid in got if got.count(cid) > 1})
        if missing:
            problems.append(Problem(where, f"コマ{label} の概念が割り当てられていない: {missing}"))
        if extra:
            problems.append(Problem(where, f"コマ{label} に無い概念が入っている: {extra}"))
        if dupes:
            problems.append(Problem(where, f"複数の回が同じ概念を導入している: {dupes}"))

    # 分割・統合を反映した並びでも requires が先行導入になっているか。
    track = new_track(sessions, variants)
    position = {vid: i for i, vid in enumerate(track)}
    owner: dict[str, str] = {}
    for v in variants:
        for cid in v.introduces:
            owner[cid] = v.vid
    for c in concepts:
        owner.setdefault(c.cid, f"{c.session:02d}")
    for v in variants:
        for cid in frontmatter.get(v.vid, {}).get("requires", []):
            home = owner.get(cid)
            if home is None or home not in position:
                problems.append(Problem(
                    v.path.name, f"requires の {cid} の導入回を特定できない"))
            elif position[home] >= position[v.vid]:
                problems.append(Problem(
                    v.path.name,
                    f"requires の {cid} は {home} 導入で、分割後の並びで先行していない"))
    # 分割・統合の影響を受けない回も、新しい並びで前提が満たされるか確かめる。
    for number, path in sorted(sessions.items()):
        vid = f"{number:02d}"
        if vid not in position:
            continue
        _, want_req = expected(concepts, number)
        for cid in want_req:
            home = owner.get(cid, "")
            if home in position and position[home] >= position[vid]:
                problems.append(Problem(
                    path.name,
                    f"requires の {cid} は {home} 導入で、分割後の並びで先行していない"))


def show(concepts: list[Concept], sessions: dict[int, Path],
         variants: list[Variant]) -> None:
    for number in sorted(sessions):
        introduces, requires = expected(concepts, number)
        print(f"コマ{number:2d}  introduces={len(introduces):2d}  requires={len(requires):2d}")
        for cid in introduces:
            print(f"        + {cid}")
    for v in variants:
        requires = derive_requires(concepts, v.introduces)
        print(f"コマ{v.vid}  introduces={len(v.introduces):2d}  requires={len(requires):2d}")
        for cid in v.introduces:
            print(f"        + {cid}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", action="store_true", help="各回の introduces / requires を表示する")
    args = parser.parse_args()

    problems: list[Problem] = []
    sessions = session_files()
    if not sessions:
        print(f"[FAIL] 原稿が見つからない: {SESSIONS}", file=sys.stderr)
        raise SystemExit(1)
    variants = variant_files()
    concepts = parse_ledger(problems)
    if concepts:
        check_ledger(concepts, sessions, problems)
        check_sessions(concepts, sessions, problems)
        check_variants(concepts, sessions, variants, problems)

    if args.show and concepts:
        show(concepts, sessions, variants)

    if problems:
        for p in problems:
            print(f"[FAIL] {p}", file=sys.stderr)
        print(f"\n{len(problems)} 件の不整合", file=sys.stderr)
        raise SystemExit(1)
    print(f"[ OK ] 概念 {len(concepts)} 件 / 原稿 {len(sessions) + len(variants)} 本"
          f"（うち分割回・統合回 {len(variants)} 本）の introduces / requires が一致")


if __name__ == "__main__":
    main()
