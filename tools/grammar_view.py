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
    return {
        # Pandoc parses metadata strings as Markdown, which would remove HTML
        # tags and normalise grammar whitespace. Hex preserves literal UTF-8.
        "code": html.encode("utf-8").hex(),
        "legend": legend_html(delta).encode("utf-8").hex(),
        "label": f"この回までの文法全文（{len(current.lines)}行）",
        "expanded": True,
        "precedence": delta.precedence_states,
    }


def legend_html(delta: Delta) -> str:
    if delta.snapshot.session == 1:
        return '<p class="grammar-legend">最初の文法です。以降の回では、全文中で追加・変更を示します。</p>'
    if not delta.changes and all(s == "existing" for s in delta.precedence_states):
        return '<p class="grammar-legend">前回から文法・優先順位の追加や変更はありません。</p>'
    return ('<p class="grammar-legend"><span class="grammar-added">追加</span>は新しい規則・選択肢、'
            '<span class="grammar-changed">変更</span>は前回の形の置き換えです。'
            'ラベルのない行は既存です。</p>')
