#!/usr/bin/env python3
"""
発展課題の依存関係の整合を機械的に検査する。

使い方:
    python3 tools/check_advanced_deps.py            # 全チェックを実行
    python3 tools/check_advanced_deps.py --only graph
    python3 tools/check_advanced_deps.py --show     # 読み取った依存関係を表示する

突き合わせる3つの情報源:

    A. 索引の一覧表   workbook/advanced/README.md の「## 全トピック一覧」
    B. 位置づけブロック 各トピックの「## この回の位置づけ」（配布物と原稿の2部）
    C. 依存グラフ     索引の「### 依存関係」のコードブロック

チェック一覧:
    block  27トピックすべてが位置づけブロックを持ち、必須の行がそろっているか
    pair   配布物（workbook/advanced/<dir>/README.md）と
           原稿（materials/advanced/<ID>_*.md）の位置づけが一致しているか
    index  索引の一覧表の「必須の前提」「コマ」が位置づけブロックと一致しているか
    graph  依存グラフの辺が、位置づけブロックから計算した**直接の前提**
           （＝トピック間の依存の推移簡約）とちょうど一致しているか
    term   原稿側で `fixed17` の初出が索引の定義へ張られているか
           （サイト版は1トピック1ページなので、索引を読まずに来た人にも
             定義への入口が要る。見出しの中は初出とみなさない）

「直接の前提」を推移簡約で定義しているので、図に間接の前提を描き足しても、
逆に直接の辺を消しても、どちらも検出される。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "workbook" / "advanced" / "README.md"
WORKBOOK_ADVANCED = ROOT / "workbook" / "advanced"
MATERIALS_ADVANCED = ROOT / "materials" / "advanced"

# 索引の「### 依存関係」に描く系列。O 系列だけがトピック間で積み上がる。
GRAPH_FAMILY = "O"

# 位置づけブロックに必ずある行（全27本にそろえた固定表）。
REQUIRED_ROWS = ("必須の前提", "推奨の前提", "改変しない", "編集する", "完了条件", "コマ数")
# S / L 系列だけに必須の行。
SPEC_ROW = "仕様との関係"

TOPIC_ID = re.compile(r"\b([FBORSLQP][0-9])\b")
SESSION = re.compile(r"コマ ?([0-9]+)")
FIXED17_DEF_LINK = "../../workbook/advanced/README.md#fixed17"


def strip_code(text: str) -> str:
    """バッククォートの中を落とす。`s1` などを回 ID と読み違えないため。"""
    return re.sub(r"`[^`]*`", " ", text)


def unlink(text: str) -> str:
    """Markdown リンクをラベルだけにする。原稿だけリンクが張ってあっても比較できる。"""
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)


def prereq_tokens(cell: str) -> set[str]:
    """前提を表す欄から、回 ID と「コマ N」を取り出して集合にする。"""
    plain = strip_code(unlink(cell))
    tokens = set(TOPIC_ID.findall(plain))
    tokens |= {f"コマ{n}" for n in SESSION.findall(plain)}
    # 「F1〜F4」のような範囲表記を展開する。
    for family, start, end in re.findall(r"([FBORSLQP])([0-9])〜[FBORSLQP]?([0-9])", plain):
        tokens |= {f"{family}{n}" for n in range(int(start), int(end) + 1)}
    return tokens


class Problem:
    def __init__(self, path: Path, message: str, line: int = 0):
        self.path = path
        self.line = line
        self.message = message

    def __str__(self) -> str:
        where = self.path.relative_to(ROOT).as_posix()
        if self.line:
            where += f":{self.line}"
        return f"{where}: {self.message}"


def table_rows(text: str, heading: str) -> list[list[str]]:
    """指定の見出しの直後にある最初の表の行を返す（区切り行と見出し行は除く）。"""
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == heading)
    except StopIteration:
        return []
    rows: list[list[str]] = []
    seen_table = False
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("|"):
            seen_table = True
            # `\|` はセルの区切りではない（表の中で `||` を書くときの書き方）。
            cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", stripped.strip("|"))]
            if all(set(cell) <= {"-", ":"} for cell in cells if cell):
                continue
            rows.append(cells)
        elif seen_table and stripped:
            break
    return rows[1:] if rows else []


# ---------------------------------------------------------------- 情報源 A


def read_index_table() -> dict[str, dict]:
    text = INDEX.read_text(encoding="utf-8")
    entries: dict[str, dict] = {}
    for cells in table_rows(text, "## 全トピック一覧"):
        if len(cells) < 5:
            continue
        topic = cells[0]
        if not TOPIC_ID.fullmatch(topic):
            continue
        entries[topic] = {
            # ディレクトリ欄はリンクになっている（[`F0_cyk/`](...)）。ラベルだけ取る。
            "dir": unlink(cells[1]).strip("`/ "),
            "sessions": cells[3],
            "prereq": prereq_tokens(cells[4]),
            "prereq_raw": cells[4],
        }
    return entries


# ---------------------------------------------------------------- 情報源 B


def read_block(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    rows = table_rows(text, "## この回の位置づけ")
    return {cells[0]: cells[1] for cells in rows if len(cells) >= 2}


def materials_path(directory: str) -> Path:
    """配布物のディレクトリ名 `O7_layout` は、原稿では `O7_layout.md` になる。"""
    return MATERIALS_ADVANCED / f"{directory}.md"


# ---------------------------------------------------------------- 情報源 C


def read_graph() -> tuple[set[tuple[str, str]], set[str], str]:
    """依存グラフのコードブロックから辺・節点・原文を読む。

    各行は「左 ─→ 右, 右, ...」の形で、左が右の直接の前提である。
    """
    text = INDEX.read_text(encoding="utf-8")
    match = re.search(r"### 依存関係\n+```text\n(.*?)```", text, re.S)
    if not match:
        return set(), set(), ""
    body = match.group(1)
    edges: set[tuple[str, str]] = set()
    nodes: set[str] = set()
    for line in body.splitlines():
        if "─→" not in line:
            continue
        left, right = line.split("─→", 1)
        sources = TOPIC_ID.findall(left)
        targets = TOPIC_ID.findall(right)
        if len(sources) != 1:
            continue
        nodes.add(sources[0])
        for target in targets:
            nodes.add(target)
            edges.add((sources[0], target))
    return edges, nodes, body


# ---------------------------------------------------------------- 計算


def transitive_reduction(edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
    """辺 (u, v) のうち、長さ2以上の道でも v に届くものを落とす。"""
    succ: dict[str, set[str]] = {}
    for u, v in edges:
        succ.setdefault(u, set()).add(v)
        succ.setdefault(v, set())

    def reachable(start: str, skip: tuple[str, str]) -> set[str]:
        seen: set[str] = set()
        stack = [start]
        while stack:
            node = stack.pop()
            for nxt in succ.get(node, ()):
                if (node, nxt) == skip or nxt in seen:
                    continue
                seen.add(nxt)
                stack.append(nxt)
        return seen

    return {(u, v) for u, v in edges if v not in reachable(u, (u, v))}


# ---------------------------------------------------------------- チェック


def check_all(only: str | None) -> tuple[list[Problem], dict]:
    problems: list[Problem] = []
    index = read_index_table()
    blocks: dict[str, dict[str, str]] = {}

    def run(name: str) -> bool:
        return only is None or only == name

    if not index:
        problems.append(Problem(INDEX, "「## 全トピック一覧」の表を読めなかった"))
        return problems, {}

    for topic, entry in index.items():
        wb = WORKBOOK_ADVANCED / entry["dir"] / "README.md"
        ms = materials_path(entry["dir"])
        wb_block = read_block(wb) if wb.is_file() else {}
        ms_block = read_block(ms) if ms.is_file() else {}
        blocks[topic] = wb_block

        if run("block"):
            for path, block in ((wb, wb_block), (ms, ms_block)):
                if not path.is_file():
                    problems.append(Problem(path, f"{topic} の README が無い"))
                    continue
                if not block:
                    problems.append(Problem(path, "「## この回の位置づけ」の表が無い"))
                    continue
                missing = [row for row in REQUIRED_ROWS if row not in block]
                if missing:
                    problems.append(Problem(path, f"位置づけブロックに行が無い: {', '.join(missing)}"))
                if topic[0] in "SL" and SPEC_ROW not in block:
                    problems.append(Problem(path, f"S / L 系列には「{SPEC_ROW}」の行が要る"))

        if run("pair") and wb_block and ms_block:
            for row in ("必須の前提", "推奨の前提"):
                if row in wb_block and row in ms_block:
                    if prereq_tokens(wb_block[row]) != prereq_tokens(ms_block[row]):
                        problems.append(
                            Problem(
                                ms,
                                f"{topic} の「{row}」が配布物と食い違う: "
                                f"配布物={sorted(prereq_tokens(wb_block[row]))} "
                                f"原稿={sorted(prereq_tokens(ms_block[row]))}",
                            )
                        )
            if wb_block.get("コマ数") != ms_block.get("コマ数"):
                problems.append(
                    Problem(ms, f"{topic} の「コマ数」が配布物と食い違う: "
                                f"配布物={wb_block.get('コマ数')} 原稿={ms_block.get('コマ数')}")
                )

        if run("index") and wb_block:
            block_prereq = prereq_tokens(wb_block.get("必須の前提", ""))
            if block_prereq != entry["prereq"]:
                problems.append(
                    Problem(
                        INDEX,
                        f"{topic} の「必須の前提」が一覧表と位置づけブロックで食い違う: "
                        f"一覧表={sorted(entry['prereq'])} 位置づけ={sorted(block_prereq)}",
                    )
                )
            if wb_block.get("コマ数", "").strip() != entry["sessions"].strip():
                problems.append(
                    Problem(
                        INDEX,
                        f"{topic} の「コマ」が一覧表と位置づけブロックで食い違う: "
                        f"一覧表={entry['sessions']} 位置づけ={wb_block.get('コマ数')}",
                    )
                )

    # --- graph ---------------------------------------------------------
    topic_edges = {
        (prereq, topic)
        for topic, block in blocks.items()
        for prereq in prereq_tokens(block.get("必須の前提", ""))
        if prereq in index
    }
    reduced = transitive_reduction(topic_edges)
    drawn_edges, drawn_nodes, body = read_graph()
    family_nodes = {topic for topic in index if topic.startswith(GRAPH_FAMILY)}
    expected = {(u, v) for u, v in reduced if u in family_nodes and v in family_nodes}

    if run("graph"):
        if not body:
            problems.append(Problem(INDEX, "「### 依存関係」のコードブロックを読めなかった"))
        else:
            if drawn_nodes != family_nodes:
                problems.append(
                    Problem(
                        INDEX,
                        f"依存グラフの節点が {GRAPH_FAMILY} 系列と一致しない: "
                        f"図={sorted(drawn_nodes)} 一覧表={sorted(family_nodes)}",
                    )
                )
            for edge in sorted(expected - drawn_edges):
                problems.append(Problem(INDEX, f"依存グラフに辺が足りない: {edge[0]} → {edge[1]}"))
            for edge in sorted(drawn_edges - expected):
                reason = "間接の前提（推移簡約で消える）" if edge in topic_edges else "位置づけブロックに根拠が無い"
                problems.append(Problem(INDEX, f"依存グラフに余分な辺がある: {edge[0]} → {edge[1]}（{reason}）"))

    # --- term ----------------------------------------------------------
    if run("term"):
        if '<a id="fixed17">' not in INDEX.read_text(encoding="utf-8"):
            problems.append(Problem(INDEX, "`fixed17` の定義（アンカー fixed17）が無い"))
        for path in sorted(MATERIALS_ADVANCED.glob("*.md")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for number, line in enumerate(lines, 1):
                # 見出しの中はリンクにしない（初出とみなさない）。
                if "fixed17" not in line or line.lstrip().startswith("#"):
                    continue
                at = line.index("fixed17")
                linked = None
                for link in re.finditer(r"\[([^\]]*)\]\(([^)]*)\)", line):
                    label_start, label_end = link.span(1)
                    if label_start <= at < label_end:
                        linked = link
                        break
                if not linked:
                    problems.append(
                        Problem(path, f"`fixed17` の初出が定義へ張られていない（{FIXED17_DEF_LINK} を張る）", number)
                    )
                elif linked.group(2) != FIXED17_DEF_LINK:
                    problems.append(Problem(path, f"`fixed17` の初出のリンク先が違う: {linked.group(2)}", number))
                break

    return problems, {"edges": topic_edges, "reduced": reduced, "drawn": drawn_edges}


def show(info: dict) -> None:
    print("トピック間の依存（位置づけブロックの「必須の前提」から）:")
    for u, v in sorted(info["edges"]):
        mark = "直接" if (u, v) in info["reduced"] else "間接"
        print(f"  {u} → {v}  ({mark})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", choices=("block", "pair", "index", "graph", "term"))
    parser.add_argument("--show", action="store_true", help="読み取った依存関係を表示する")
    args = parser.parse_args()

    problems, info = check_all(args.only)
    if args.show and info:
        show(info)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        print(f"check_advanced_deps: {len(problems)} 件の不整合", file=sys.stderr)
        raise SystemExit(1)
    print("check_advanced_deps: OK")


if __name__ == "__main__":
    main()
