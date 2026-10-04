"""Grammar changes must match the course sequence and preserve literal source."""
from html.parser import HTMLParser
import contextlib
import io
from pathlib import Path
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site
from grammar_snapshots import (
    GRAMMAR_HEADING, PREC_INTRO, GrammarLine, Snapshot,
    compare_snapshots, delta_for_path, parse_ebnf_block, read_snapshot,
)
from grammar_view import grammar_metadata

ROOT = Path(__file__).resolve().parents[2]


class LiteralText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


class PageProbe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.full = []
        self.code = []
        self.in_code = False
        self.ids = []
        self.states = []
    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get("class", "").split()
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "details" and "grammar-full" in classes:
            self.full.append("open" in attrs)
        if tag == "code" and "grammar-code" in classes:
            self.in_code = True
        if tag == "span" and "grammar-line" in classes:
            self.states.append(attrs.get("data-label"))
    def handle_endtag(self, tag):
        if tag == "code":
            self.in_code = False
    def handle_data(self, data):
        if self.in_code:
            self.code.append(data)


class GrammarTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)

    def source(self, number, body, *, extra=""):
        table = ("\n" + PREC_INTRO + "\n\n| 優先順位 | 演算子 | 結合 |\n"
                 "|---|---|---|\n| 1 | `*` `/` `%` | 左 |\n| 2 | `+` `-` | 左 |\n"
                 if number < 4 else "")
        path = self.directory / f"{number:02}_fixture.md"
        path.write_text("# Fixture\n\n" + GRAMMAR_HEADING + "\n\n```ebnf\n" + body
                        + "\n```\n" + table + "\n## Next\n" + extra, encoding="utf-8")
        return path

    def test_course_sequence_has_the_observed_additions_and_replacements(self):
        paths = sorted((ROOT / "materials/sessions").glob("*.md"))
        expected = [(0, 0), (0, 0), (8, 2), (7, 2), (8, 1), (8, 2), (4, 2),
                    (2, 0), (5, 2), (1, 1), (1, 0), (8, 0), (4, 0), (1, 0)]
        for path in paths:
            n = int(path.name[:2])
            if not 1 <= n <= 14:
                continue
            with self.subTest(session=n):
                delta = delta_for_path(path)
                self.assertEqual((sum(c.kind == "added" for c in delta.changes),
                                  sum(c.kind == "changed" for c in delta.changes)), expected[n - 1])
        last = delta_for_path(next(p for p in paths if p.name.startswith("14_")))
        self.assertEqual(len(last.cumulative), 69)
        self.assertEqual([c.line.rule for c in last.changes], ["define_dir"])

    def test_comments_and_spacing_do_not_create_changes_and_source_positions_survive(self):
        first = self.source(1, "program ::= INT_LITERAL /* old note */")
        second = self.source(2, "program   ::=  INT_LITERAL  /* new note */")
        delta = compare_snapshots(read_snapshot(second, 2), read_snapshot(first, 1))
        self.assertEqual(delta.changes, [])
        line = delta.snapshot.lines[0]
        self.assertEqual(line.raw, "program   ::=  INT_LITERAL  /* new note */")
        self.assertEqual(second.read_text().splitlines()[line.number - 1], line.raw)

    def test_new_alternative_is_an_addition(self):
        first = self.source(1, "program ::= INT_LITERAL")
        second = self.source(2, "program ::= INT_LITERAL\n          | IDENT")
        delta = compare_snapshots(read_snapshot(second, 2), read_snapshot(first, 1))
        self.assertEqual([(c.kind, c.line.rule, c.line.rhs) for c in delta.changes],
                         [("added", "program", "IDENT")])

    def test_unapproved_removal_is_rejected(self):
        first = self.source(1, "program ::= INT_LITERAL\n          | IDENT")
        second = self.source(2, "program ::= INT_LITERAL")
        with self.assertRaisesRegex(ValueError, "unapproved removal"):
            compare_snapshots(read_snapshot(second, 2), read_snapshot(first, 1))

    def test_allowed_replacement_is_changed_and_requires_the_expected_after(self):
        first = self.source(2, "func_body ::= '{' stmt '}'")
        second = self.source(3, "func_body ::= '{' { var_decl } { expr_stmt } 'return' expr ';' '}'")
        delta = compare_snapshots(read_snapshot(second, 3), read_snapshot(first, 2))
        self.assertEqual(delta.changes[0].kind, "changed")
        self.assertEqual(delta.changes[0].before, "'{' stmt '}'")
        second = self.source(3, "func_body ::= '{' expr '}'")
        with self.assertRaisesRegex(ValueError, "unapproved removal"):
            compare_snapshots(read_snapshot(second, 3), read_snapshot(first, 2))

    def test_final_snapshot_cannot_hide_missing_rules_in_a_partial_block(self):
        include = "'#' 'include' '\"' FILENAME '\"' NEWLINE"
        previous = Snapshot(13, self.directory / "13_fixture.md", [
            GrammarLine("", 1, "include_dir", include),
            GrammarLine("", 2, "program", "INT_LITERAL"),
        ], {"include_dir": 1, "program": 2}, [])
        current = Snapshot(14, self.directory / "14_fixture.md", [
            GrammarLine("", 1, "include_dir", include),
            GrammarLine("", 2, "define_dir", "'#' 'define' IDENT { TOKEN } NEWLINE"),
        ], {"include_dir": 1, "define_dir": 2}, [])
        with self.assertRaisesRegex(ValueError, "unapproved removal of program"):
            compare_snapshots(current, previous)

    def test_precedence_additions_are_scoped_to_the_grammar_table(self):
        for number, expected in [(2, 0), (4, 2), (13, 2), (14, 0)]:
            path = next((ROOT / "materials/sessions").glob(f"{number:02}_*.md"))
            delta = delta_for_path(path)
            self.assertEqual(delta.precedence_states.count("added"), expected)
        path = self.source(1, "program ::= INT_LITERAL", extra=PREC_INTRO + "\n| unrelated |\n")
        self.assertEqual(len(read_snapshot(path, 1).precedence), 2)

    def test_malformed_grammar_is_not_silently_annotated(self):
        path = self.source(1, "| IDENT")
        with self.assertRaisesRegex(ValueError, "規則名の無い"):
            read_snapshot(path, 1)
        self.assertTrue(parse_ebnf_block(["not a rule"], 1)[2])

    def test_full_html_preserves_source_and_escapes_markup_even_with_token_marks(self):
        for number in [1, 3, 4, 7, 12, 13, 14]:
            path = next((ROOT / "materials/sessions").glob(f"{number:02}_*.md"))
            view = grammar_metadata(path)
            code = bytes.fromhex(view["code"]).decode()
            parser = LiteralText()
            parser.feed(code)
            snapshot = read_snapshot(path, number)
            self.assertEqual("".join(parser.parts), "\n".join(l.raw for l in snapshot.lines))
            self.assertTrue(view["expanded"])
        path = self.source(1, "program ::= '<script>'")
        code = bytes.fromhex(grammar_metadata(path)["code"]).decode()
        self.assertIn("&lt;script&gt;", code)
        self.assertNotIn("<script>", code)

    def test_initial_and_unchanged_sessions_are_explicitly_different(self):
        for number, expected in [(1, "最初の文法"), (2, "追加や変更はありません")]:
            path = next((ROOT / "materials/sessions").glob(f"{number:02}_*.md"))
            self.assertIn(expected, bytes.fromhex(grammar_metadata(path)["legend"]).decode())

    def test_live_rebuild_includes_next_session_without_spilling_into_docs(self):
        root = self.directory
        session = root / "materials/sessions"
        paths = [session / "12_fixture.md", session / "13_fixture.md", session / "14_fixture.md",
                 root / "workbook/docs/language_spec.md"]
        pages = [SimpleNamespace(source=p) for p in paths]
        with patch.object(build_site, "ROOT", root):
            self.assertEqual(build_site.pages_with_grammar_dependents([paths[0]], pages), paths[:2])
            self.assertEqual(build_site.pages_with_grammar_dependents([paths[2]], pages), [paths[2]])
            self.assertEqual(build_site.pages_with_grammar_dependents([paths[3]], pages), [paths[3]])

    @unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for generated HTML integration")
    def test_pandoc_preserves_full_source_markup_and_existing_anchors(self):
        nav = build_site.load_nav()
        pages = build_site.build_pages(nav)
        links = build_site.link_map(pages)
        for number in [1, 2, 3, 4, 13, 14]:
            page = next(p for p in pages if p.section_slug == "sessions" and p.slug.startswith(f"{number:02}_"))
            with self.subTest(session=number), contextlib.redirect_stdout(io.StringIO()):
                build_site.render_page(nav, pages, page, self.directory, links)
                html = (self.directory / page.out_dir / "index.html").read_text()
                probe = PageProbe()
                probe.feed(html)
                snapshot = read_snapshot(page.source, number)
                self.assertEqual("".join(probe.code), "\n".join(l.raw for l in snapshot.lines))
                self.assertEqual(probe.full, [True])
                self.assertNotIn('grammar-overview', html)
                self.assertNotIn('grammar-updates', html)
                self.assertNotIn('前回からの追加・変更', html)
                self.assertEqual(len(probe.ids), len(set(probe.ids)))
                self.assertIn("この回までの言語仕様ebnf", probe.ids)
                delta = delta_for_path(page.source)
                self.assertEqual(probe.states.count("追加"), sum(c.kind == "added" for c in delta.changes))
                self.assertEqual(probe.states.count("変更"), sum(c.kind == "changed" for c in delta.changes))
                self.assertIn('assets/grammar.js', html)


if __name__ == "__main__":
    unittest.main()
