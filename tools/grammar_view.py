"""Render source-preserving grammar annotations for the existing Pandoc filter."""
from __future__ import annotations

from difflib import SequenceMatcher
from html import escape
from pathlib import Path
import re

from grammar_snapshots import Delta, GrammarLine, Change, delta_for_path


TOKENS = re.compile(r"/\*.*?\*/|'[^']*'|\"[^\"]*\"|\w+|[^\w\s]|\s+")


def render_line(line: GrammarLine, change: Change | None) -> str:
    if change is None or change.before is None:
        return escape(line.raw)
    # Highlight inserted/replaced tokens; keep every original character intact.
    cut = line.raw.index("::=") + 3 if "::=" in line.raw else line.raw.index("|") + 1
    prefix, rhs = line.raw[:cut], line.raw[cut:]
    before = [t for t in TOKENS.findall(change.before) if not t.isspace()]
    tokens = TOKENS.findall(rhs)
    meaningful = [t for t in tokens if not t.isspace() and not t.startswith("/*")]
    updated = set()
    for op, _a, _b, start, end in SequenceMatcher(a=before, b=meaningful, autojunk=False).get_opcodes():
        if op in {"insert", "replace"}:
            updated.update(range(start, end))
    parts = [escape(prefix)]
    index = 0
    for token in tokens:
        value = escape(token)
        if not token.isspace() and not token.startswith("/*"):
            if index in updated:
                value = '<mark class="grammar-token">' + value + '</mark>'
            index += 1
        parts.append(value)
    return "".join(parts)


def grammar_metadata(path: Path) -> dict:
    delta = delta_for_path(path)
    current = delta.snapshot
    changes = {change.line.number: change for change in delta.changes}
    code = []
    for line in current.lines:
        change = changes.get(line.number)
        kind = change.kind if change else "existing"
        label = {"added": "追加", "changed": "変更"}.get(kind, "")
        code.append(f'<span id="grammar-line-{line.number}" class="grammar-line grammar-{kind}"'
                    f' data-label="{label}">{render_line(line, change)}</span>')
    html = '<pre class="grammar-pre"><code class="grammar-code">' + "\n".join(code) + '</code></pre>'
    label = ("この回の文法" if current.session == 1 else
             "前処理指令の差分" if current.session == 14 else "この回までの文法全文")
    return {
        # Pandoc parses metadata strings as Markdown, which would remove HTML
        # tags and normalise grammar whitespace. Hex preserves literal UTF-8.
        "code": html.encode("utf-8").hex(),
        "overview": overview_html(delta).encode("utf-8").hex(),
        "label": f"{label}（{len(current.lines)}行）",
        "expanded": current.session in {1, 14},
        "precedence": delta.precedence_states,
    }


def overview_html(delta: Delta) -> str:
    if delta.snapshot.session == 1:
        return '<p class="grammar-status">最初の文法です。以降の回では、前回からの追加・変更を示します。</p>'
    if not delta.changes and all(s == "existing" for s in delta.precedence_states):
        return '<p class="grammar-status">前回から文法・優先順位の追加や変更はありません。</p>'
    rows = []
    for change in delta.changes:
        label = "変更" if change.before is not None else "追加"
        line = change.line
        before = ('<small class="grammar-before">前回: <code>' + escape(change.before) + '</code></small>'
                  if change.before is not None else "")
        rows.append(f'<li class="grammar-update grammar-{change.kind}">'
                    f'<span class="grammar-badge">{label}</span> '
                    f'<a href="#grammar-line-{line.number}"><code>{escape(line.rule)}</code></a>'
                    f'<code class="grammar-rhs"> ::= {escape(line.rhs)}</code>{before}</li>')
    for index, state in enumerate(delta.precedence_states):
        if state not in {"added", "changed"}:
            continue
        ops, assoc = delta.snapshot.precedence[index]
        label = "変更" if state == "changed" else "追加"
        rows.append(f'<li class="grammar-update grammar-{state}">'
                    f'<span class="grammar-badge">{label}</span> 優先順位表: '
                    f'<code>{escape(" ".join(ops))}</code>（{assoc}結合）</li>')
    return ('<div class="grammar-overview"><p class="grammar-overview-title">前回からの追加・変更</p>'
            '<p class="grammar-legend"><span class="grammar-added">追加</span>は新しい規則・選択肢、'
            '<span class="grammar-changed">変更</span>は前回の形の置き換えです。'
            '全文でも同じラベルを付けています。ラベルのない行は既存です。</p><ul class="grammar-updates">'
            + "".join(rows) + '</ul></div>')
