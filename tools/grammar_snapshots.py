"""Shared grammar parsing for document checks and static lecture presentation.

Keep the Markdown source as the authority; normalised alternatives are comparison
keys, never replacement text for the full displayed grammar.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

GRAMMAR_HEADING = "### この回までの言語仕様（EBNF）"
GRAMMAR_SPEC_HEADING = "## 形式文法（EBNF）"
GRAMMAR_SPEC_SKIP_SUBHEADINGS = {"### 字句トークン"}
GRAMMAR_LAST_SESSION = 14

# 回をまたいで右辺が「置き換わる」箇所。素朴な部分集合判定では削除と
# 誤検知されるため、(消える回, 規則名, 精密化前, 精密化後) を許可リストに置く。
# 出典: 各回原稿の累積文法。初期回の末尾return制限はコマ4で解除する。
GRAMMAR_REFINEMENTS: tuple[tuple[int, str, str, str], ...] = (
    (2, "func_body", "'{' stmt '}'",
     "'{' { var_decl } { expr_stmt } 'return' expr ';' '}'"),
    (3, "func_body", "'{' { var_decl } { expr_stmt } 'return' expr ';' '}'",
     "'{' { var_decl } { stmt } '}'"),
    (2, "expr", "binary_expr", "assign_expr"),
    (6, "stmt", "'return' expr ';'", "'return' [ expr ] ';'"),
    (5, "func_def", "'int' 'main' '(' ')' func_body",
     "ret_type IDENT '(' [ param_list ] ')' func_body"),
    (4, "expr_stmt", "expr ';'", "[ expr ] ';'"),
    (6, "scalar_type", "'int'", "'int' [ stars ]"),
    (8, "stars", "'*'", "'*' { '*' }"),
    (8, "unary_expr", "primary_expr", "postfix_expr"),
    (3, "assign_expr", "binary_expr", "cond_expr"),
    (5, "program", "func_def", "external_decl { external_decl }"),
    (9, "func_proto", "ret_type IDENT '(' [ param_list ] ')' ';'",
     "ret_type IDENT '(' [ param_list [ ',' '...' ] ] ')' ';'"),
)

GRAMMAR_COMMENT_RE = re.compile(r"/\*.*?\*/")
GRAMMAR_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")
GRAMMAR_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def normalize_rhs(text: str) -> str:
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
        line = normalize_rhs(raw)
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


def nonterminals(alt: str) -> set[str]:
    """選択肢の右辺に現れる非終端記号（小文字始まり）を返す。"""
    stripped = GRAMMAR_QUOTED_RE.sub(" ", alt)
    return {w for w in GRAMMAR_WORD_RE.findall(stripped) if w[:1].islower()}


def extract_ebnf_after(lines: list[str], heading_idx: int,
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


PREC_TABLE: tuple[tuple[tuple[str, ...], str, int], ...] = (
    (("*", "/", "%"), "左", 2),
    (("+", "-"), "左", 2),
    (("<", ">", "<=", ">="), "左", 4),
    (("==", "!="), "左", 4),
    (("&&",), "左", 13),
    (("||",), "左", 13),
)
PREC_INTRO = "この回までの二項演算子の優先順位（高い順）:"
PREC_LAST_SESSION = GRAMMAR_LAST_SESSION
PREC_CELL_CODE_RE = re.compile(r"`([^`]+)`")


def expected_precedence(n: int) -> list[tuple[tuple[str, ...], str]]:
    """コマ n の表に載るべき行を返す（コマ1 の範囲はコマ2 と同一）。"""
    limit = max(n, 2)
    return [(ops, assoc) for (ops, assoc, intro) in PREC_TABLE if intro <= limit]


def parse_precedence_table(lines: list[str], start: int) -> tuple[
        list[tuple[tuple[str, ...], str]], int] | None:
    """PREC_INTRO 行 start の後ろの Markdown 表を (行, 表の開始行番号) で返す。"""
    i = start + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not lines[i].strip().startswith("|"):
        return None
    header_lineno = i + 1
    i += 2  # ヘッダ行と区切り行を読み飛ばす
    rows: list[tuple[tuple[str, ...], str]] = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        # `\|`（表中でパイプを書くための退避）では列を分割しない
        cells = [c.strip() for c in
                 re.split(r"(?<!\\)\|", lines[i].strip().strip("|"))]
        if len(cells) >= 3:
            ops = tuple(m.replace("\\|", "|")
                        for m in PREC_CELL_CODE_RE.findall(cells[1]))
            rows.append((ops, cells[2]))
        i += 1
    return rows, header_lineno


@dataclass(frozen=True)
class GrammarLine:
    raw: str
    number: int
    rule: str | None
    rhs: str | None

    @property
    def key(self) -> tuple[str, str] | None:
        return (self.rule, self.rhs) if self.rhs is not None else None


@dataclass
class Snapshot:
    session: int
    path: Path
    lines: list[GrammarLine]
    defined: dict[str, int]
    precedence: list[tuple[tuple[str, ...], str]]

    @property
    def alternatives(self) -> set[tuple[str, str]]:
        return {line.key for line in self.lines if line.key is not None}


@dataclass(frozen=True)
class Change:
    kind: str
    line: GrammarLine
    before: str | None = None


@dataclass
class Delta:
    snapshot: Snapshot
    changes: list[Change]
    precedence_states: list[str]
    cumulative: set[tuple[str, str]]


@dataclass
class Transition:
    replacements: dict[tuple[str, str], str]
    invalid: list[tuple[str, str, str | None]]
    used: set[tuple[int, str, str]]


def classify_transition(prior: set[tuple[str, str]], now: set[tuple[str, str]],
                        from_session: int) -> Transition:
    """One refinement interpretation for both checking and presentation."""
    allowed = {(rule, before): after for n, rule, before, after in GRAMMAR_REFINEMENTS
               if n == from_session}
    replacements, invalid, used = {}, [], set()
    for rule, before in sorted(prior - now):
        after = allowed.get((rule, before))
        if after is None or (rule, after) not in now:
            invalid.append((rule, before, after))
        else:
            replacements[rule, after] = before
            used.add((from_session, rule, before))
    return Transition(replacements, invalid, used)


def read_snapshot(path: Path, session: int) -> Snapshot:
    source = path.read_text(encoding="utf-8").splitlines()
    heading = next((i for i, line in enumerate(source)
                    if line.strip() == GRAMMAR_HEADING), None)
    if heading is None:
        raise ValueError(f"{path.name}: grammar heading is missing")
    block = extract_ebnf_after(
        source, heading,
        stop_pred=lambda s: s.startswith("## ") or s.startswith("### "))
    if block is None:
        raise ValueError(f"{path.name}: grammar block is missing")
    body, start = block
    _alts, defined, problems = parse_ebnf_block(body, start)
    if problems:
        raise ValueError(f"{path.name}: " + "; ".join(problems))
    current = None
    rows = []
    for offset, raw in enumerate(body):
        normal = normalize_rhs(raw)
        rhs = None
        if "::=" in normal:
            current, rhs = (part.strip() for part in normal.split("::=", 1))
        elif normal.startswith("|"):
            rhs = normal[1:].strip()
        rows.append(GrammarLine(raw, start + offset, current, rhs or None))

    # Only the precedence table in this grammar section is relevant.
    end = next((i for i in range(heading + 1, len(source))
                if source[i].startswith("## ") or source[i].startswith("### ")),
               len(source))
    intro = next((i for i in range(heading, end) if source[i].strip() == PREC_INTRO), None)
    precedence = []
    if intro is not None:
        table = parse_precedence_table(source, intro)
        if table is None:
            raise ValueError(f"{path.name}: precedence table is unreadable")
        precedence = table[0]
    if session <= PREC_LAST_SESSION and precedence != expected_precedence(session):
        raise ValueError(f"{path.name}: precedence table does not match this session")
    return Snapshot(session, path, rows, defined, precedence)


def compare_snapshots(current: Snapshot, previous: Snapshot | None = None,
                      previous_cumulative: set[tuple[str, str]] | None = None) -> Delta:
    """Classify source lines; unapproved removal must not become a green addition."""
    if previous is None:
        if current.session != 1:
            raise ValueError("Only session 1 can be an initial snapshot")
        return Delta(current, [], ["initial"] * len(current.precedence), current.alternatives)
    if previous.session + 1 != current.session:
        raise ValueError("Grammar comparison requires consecutive sessions")
    prior = previous.alternatives if previous_cumulative is None else previous_cumulative
    now = current.alternatives
    transition = classify_transition(prior, now, previous.session)
    if transition.invalid:
        rule, before, _after = transition.invalid[0]
        raise ValueError(f"{current.path.name}: unapproved removal of {rule} ::= {before}")
    changes = []
    for line in current.lines:
        if line.key is None or line.key in prior:
            continue
        before = transition.replacements.get(line.key)
        changes.append(Change("changed" if before is not None else "added", line, before))
    states = ["existing" if row in previous.precedence else
              "changed" if row[0] in {r[0] for r in previous.precedence} else "added"
              for row in current.precedence]
    return Delta(current, changes, states, now)


def session_paths(directory: Path) -> dict[int, Path]:
    return {int(path.name[:2]): path for path in sorted(directory.glob("*.md"))
            if re.match(r"^\d\d_", path.name)
            and 1 <= int(path.name[:2]) <= GRAMMAR_LAST_SESSION}


def delta_for_path(path: Path) -> Delta:
    n = int(path.name[:2])
    current = read_snapshot(path, n)
    paths = session_paths(path.parent)
    if n == 1:
        return compare_snapshots(current)
    if n - 1 not in paths:
        raise ValueError(f"{path.name}: previous grammar snapshot is missing")
    return compare_snapshots(current, read_snapshot(paths[n - 1], n - 1))
