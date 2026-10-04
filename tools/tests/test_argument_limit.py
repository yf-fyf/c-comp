"""The supplied Python parser diagnoses argument limits before code generation."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def source(kind, count):
    params = ", ".join(f"int p{i}" for i in range(count))
    args = ", ".join("1" for _ in range(count))
    if kind == "definition":
        return f"int f({params}) {{ return 0; }}"
    if kind == "prototype":
        return f"int f({params});"
    if kind == "variadic prototype":
        return f"int f({params}, ...);"
    call_params = ", ".join(f"int p{i}" for i in range(min(count, 8)))
    declaration = "int f(int first, ...);" if kind == "variadic call" else f"int f({call_params});"
    return declaration + f" int main() {{ return f({args}); }}"


class ArgumentLimitTest(unittest.TestCase):
    def test_boundary(self):
        for kind in ["definition", "prototype", "call", "variadic prototype", "variadic call"]:
            for count in [0, 8, 9]:
                if count == 0 and kind.startswith("variadic"):
                    continue  # ... requires a fixed parameter; not an argument-limit case.
                with self.subTest(kind=kind, count=count), tempfile.TemporaryDirectory() as raw:
                    path = Path(raw)/"input.c"
                    path.write_text(source(kind, count))
                    result = subprocess.run(
                        [sys.executable, str(ROOT/"workbook/scaffold/parse_viewer.py"), str(path)],
                        capture_output=True, text=True, timeout=10,
                    )
                    if count <= 8:
                        self.assertEqual(result.returncode, 0, result.stderr)
                    else:
                        self.assertNotEqual(result.returncode, 0)
                        self.assertIn("最大8個", result.stderr)
                        self.assertIn("line", result.stderr)


if __name__ == "__main__":
    unittest.main()
