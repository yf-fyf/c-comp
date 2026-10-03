"""Check generated navigation and the cascade used by lecture code blocks."""
import contextlib
from html.parser import HTMLParser
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_site


class NavigationProbe(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_toc = False
        self.toc_open = []
        self.links = []
        self.shortcuts = []
        self.headings = []
        self.ids = []
        self.code = []
        self.in_pre = False
        self.stack = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get("class", "").split()
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "details" and "toc" in classes:
            self.in_toc = True
            self.toc_open.append("open" in attrs)
        if tag == "a" and self.in_toc:
            self.links.append(attrs["href"])
        if tag == "a" and "toc-grammar" in classes:
            self.shortcuts.append(attrs["href"])
        if tag == "h2":
            # Pandoc moves a heading's ID to <section> inside a Div (the goal).
            identifier = attrs.get("id") or next(
                value["id"] for element, value in reversed(self.stack)
                if element == "section" and "id" in value)
            self.headings.append(identifier)
        if tag == "pre":
            self.in_pre = True
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, attrs))

    def handle_endtag(self, tag):
        if tag == "details":
            self.in_toc = False
        if tag == "pre":
            self.in_pre = False
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.in_pre:
            self.code.append(data)


@unittest.skipUnless(shutil.which("pandoc"), "Pandoc is required for generated HTML checks")
class SitePresentationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.nav = build_site.load_nav()
        self.pages = build_site.build_pages(self.nav)
        self.links = build_site.link_map(self.pages)

    def render(self, page):
        with contextlib.redirect_stdout(io.StringIO()):
            build_site.render_page(self.nav, self.pages, page, self.output, self.links)
        html = (self.output / page.out_dir / "index.html").read_text()
        probe = NavigationProbe()
        probe.feed(html)
        return html, probe

    def test_collapsible_toc_retains_all_section_links_and_only_one_grammar_shortcut(self):
        for prefix in ["01_", "12_"]:
            page = next(p for p in self.pages if p.section_slug == "sessions" and p.slug.startswith(prefix))
            with self.subTest(page=page.slug):
                _html, probe = self.render(page)
                self.assertEqual(probe.toc_open, [False])
                self.assertEqual(probe.links, ["#" + identifier for identifier in probe.headings])
                self.assertEqual(len(probe.shortcuts), 1)
                self.assertIn(probe.shortcuts[0][1:], probe.ids)
                self.assertEqual(len(probe.ids), len(set(probe.ids)))

    def test_shared_pages_do_not_get_a_nonexistent_lecture_grammar_shortcut(self):
        for slug in ["F0_cyk", "language_spec"]:
            page = next(p for p in self.pages if p.slug == slug)
            with self.subTest(page=slug):
                _html, probe = self.render(page)
                self.assertEqual(probe.shortcuts, [])
                self.assertEqual(probe.links, ["#" + identifier for identifier in probe.headings])

    def test_highlight_cascade_and_literal_program_text_survive_generation(self):
        source = self.output / "fixture.md"
        literal = 'print("literal < & >")\n  # indentation and comment'
        source.write_text("# Fixture\n\n## First\n\n```python\n" + literal
                          + "\n```\n\n## Second\n\n### Nested\n", encoding="utf-8")
        destination = self.output / "fixture.html"
        build_site.run_pandoc(source, destination, variables={"base": ""}, metadata={})
        html = destination.read_text()
        probe = NavigationProbe()
        probe.feed(html)
        self.assertEqual("".join(probe.code), literal)
        self.assertEqual(probe.links, ["#first", "#second"])
        self.assertLess(html.index("</style>"), html.index('href="assets/style.css"'))
        self.assertIn('src="assets/navigation.js"', html)


if __name__ == "__main__":
    unittest.main()
