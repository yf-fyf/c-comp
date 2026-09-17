"""Q1の正常系ランナーが、検査の失敗を成功扱いしないことをCLI経由で確認する。"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class GoldenTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.workbook = Path(tmp.name) / "workbook"
        self.topic = self.workbook / "advanced" / "Q1_typecheck"
        self.topic.mkdir(parents=True)
        shutil.copy(ROOT / "workbook/advanced/Q1_typecheck/golden.py", self.topic)
        shutil.copytree(ROOT / "workbook/scaffold", self.workbook / "scaffold",
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.tests = self.workbook / "sessions" / "sample" / "tests"
        self.tests.mkdir(parents=True)

    def source(self, name, source="int main() { return 0; }"):
        path = self.tests / name
        path.write_text(source, encoding="utf-8")
        return path

    def run_golden(self, checker="def check_program(prog):\n    return []\n"):
        (self.topic / "typecheck.py").write_text(checker, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(self.topic / "golden.py")],
            cwd=self.workbook, capture_output=True, text=True, timeout=15,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHON_COLORS="0"),
        )

    def assert_failed(self, result, *details):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[FAIL]", result.stdout)
        self.assertNotIn("[PASS]", result.stdout)
        for detail in details:
            self.assertIn(detail, result.stdout)

    def test_valid_input_passes(self):
        self.source("good.c")
        result = self.run_golden()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[PASS] 1 ファイル", result.stdout)

    def test_checker_exceptions_fail_with_input_and_reason(self):
        self.source("broken.c")
        for error in ('RuntimeError("broken handler")', 'SystemExit(0)',
                      'SyntaxError("checker bug")'):
            with self.subTest(error=error):
                result = self.run_golden(f"def check_program(prog):\n    raise {error}\n")
                self.assert_failed(result, "broken.c", error.split("(")[0])

    def test_partial_failure_does_not_disappear(self):
        self.source("good.c")
        self.source("struct.c", "struct Pair { int x; }; int main() { return 0; }")
        result = self.run_golden(
            "def check_program(prog):\n"
            "    if prog.struct_defs:\n"
            "        raise RuntimeError('struct handler')\n"
            "    return []\n"
        )
        self.assert_failed(result, "struct.c", "struct handler", "検査: 1 件", "検査失敗: 1 件")

    def test_false_positive_is_reported(self):
        self.source("good.c")
        result = self.run_golden(
            "from types import SimpleNamespace\n"
            "def check_program(prog):\n"
            "    return [SimpleNamespace(line=1, msg='false alarm')]\n"
        )
        self.assert_failed(result, "good.c", "false alarm", "誤検出")

    def test_unimplemented_is_incomplete(self):
        self.source("good.c")
        result = self.run_golden("def check_program(prog):\n    raise NotImplementedError('Step 1')\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("[SKIP]", result.stdout)
        self.assertIn("good.c", result.stdout)
        self.assertIn("未実装: Step 1", result.stdout)
        self.assertNotIn("[PASS]", result.stdout)

    def test_empty_corpus_fails(self):
        self.assert_failed(self.run_golden(), "入力が0件")

    def test_frontend_rejection_is_reported_as_exclusion(self):
        self.source("good.c")
        self.source("invalid.c", "int main( {")
        result = self.run_golden()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[SKIP] sessions/sample/tests/invalid.c", result.stdout)
        self.assertIn("scaffold が受理しない", result.stdout)
        self.assertIn("除外: 1 件", result.stdout)
        self.assertIn("[PASS] 1 ファイル", result.stdout)

    def test_excluded_only_corpus_fails(self):
        self.source("invalid.c", "int main( {")
        self.assert_failed(self.run_golden(), "除外: 1 件", "入力が0件")

    def test_multifile_exclusion_is_reported(self):
        self.source("good.c")
        source = self.source("multi.c")
        source.with_suffix(".files").write_text("math_util.c\n", encoding="utf-8")
        self.source("math_util.c", "int helper() { return 1; }")
        result = self.run_golden()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("除外: 2 件", result.stdout)
        self.assertIn("multi.c — 複数ファイル", result.stdout)
        self.assertIn("math_util.c — 複数ファイル", result.stdout)

    def test_unexpected_frontend_error_fails(self):
        self.source("broken.c")
        lexer = self.workbook / "scaffold" / "lexer.py"
        with lexer.open("a", encoding="utf-8") as f:
            f.write("\ndef preprocess(*args, **kwargs):\n    raise RuntimeError('frontend bug')\n")
        self.assert_failed(self.run_golden(), "broken.c", "scaffold の処理に失敗", "frontend bug")


if __name__ == "__main__":
    unittest.main()
