"""Ensure assembled link checks inspect web paths and URL queries."""

import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "build_site_links_test", Path(__file__).resolve().parents[1] / "build_site.py"
)
BUILD_SITE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD_SITE
SPEC.loader.exec_module(BUILD_SITE)


class SiteLinksTest(unittest.TestCase):
    def check_tree(self, root, *, assembled):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            status = BUILD_SITE.check_links(root, assembled=assembled)
        return status, output.getvalue()

    def test_standalone_site_allows_web_paths_but_assembled_site_requires_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<a href="tools/app.html?mode=build">app</a>')
            self.assertEqual(self.check_tree(root, assembled=False)[0], 0)
            self.assertEqual(self.check_tree(root, assembled=True)[0], 1)
            (root / "tools").mkdir()
            (root / "tools" / "app.html").write_text("app")
            self.assertEqual(self.check_tree(root, assembled=True)[0], 0)

    def test_assembled_check_catches_missing_web_assets_and_links_to_docs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tools" / "app.html").write_text(
                '<script src="assets/missing.js"></script><a href="../docs/missing/">help</a>'
            )
            status, output = self.check_tree(root, assembled=True)
            self.assertEqual(status, 1)
            self.assertIn("assets/missing.js", output)
            self.assertIn("../docs/missing/", output)

    def test_assembled_check_requires_linked_download(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text('<a href="downloads/missing.zip">download</a>')
            self.assertEqual(self.check_tree(root, assembled=True)[0], 1)


if __name__ == "__main__":
    unittest.main()
