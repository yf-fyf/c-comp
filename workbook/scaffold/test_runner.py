#!/usr/bin/env python3
"""
mycc テストランナー

使い方:
    python3 scaffold/test_runner.py [SESSION_DIR]
    python3 scaffold/test_runner.py --compiler PATH --tests PATH

例:
    python3 scaffold/test_runner.py sessions/05_loops
    python3 scaffold/test_runner.py --compiler sessions/05_loops/mycc.py --tests sessions/05_loops/tests
    python3 scaffold/test_runner.py        # final/mycc.py と final/tests を使う

テストケース形式:
    tests/foo.c        入力ソース
    tests/foo.ans      期待する exit code（整数）
    tests/foo.stdout   期待する標準出力（省略可）
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")
QEMU = os.environ.get("QEMU", "qemu-riscv64")
ROOT = Path(__file__).resolve().parent.parent


def resolve_path(raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    return ROOT / path


def which(name: str) -> Path | None:
    resolved = shutil.which(name)
    return Path(resolved) if resolved else None


def last_error_line(stderr: str | None) -> str:
    """エラー出力の要点だけを1行で返す。

    Python のトレースバックは最後の行に例外が出るので、そこを拾う。
    全文が要るときは mycc.py を直接実行する。
    """
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    if not lines:
        return "エラー出力なし（mycc.py を直接実行して確かめる）"
    return lines[-1][:160]


def run_compiler(compiler: Path, src: Path, extra_srcs: list = None) -> str:
    args = [sys.executable, str(compiler), str(src)] if compiler.suffix == ".py" else [str(compiler), str(src)]
    if extra_srcs:
        args.extend(str(p) for p in extra_srcs)

    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, args,
                                            output=result.stdout, stderr=result.stderr)
    return result.stdout


def run_test(src: Path, compiler: Path, gcc_bin: Path, qemu_bin: Path) -> str:
    base = src.with_suffix("")
    ans_file = base.with_suffix(".ans")
    out_file = base.with_suffix(".stdout")
    files_file = base.with_suffix(".files")

    if not ans_file.exists():
        return "SKIP"

    expected_code = int(ans_file.read_text().strip())
    expected_out = out_file.read_text() if out_file.exists() else ""

    extra_srcs = []
    if files_file.exists():
        for line in files_file.read_text().strip().splitlines():
            line = line.strip()
            if line:
                extra_path = src.parent / line
                if not extra_path.is_file():
                    return f"FAIL: extra source not found: {extra_path}"
                extra_srcs.append(extra_path)

    try:
        asm = run_compiler(compiler, src, extra_srcs)
    except subprocess.CalledProcessError as error:
        # 理由を落とすと最初の失敗が無情報になる。未実装なのか例外なのかを出す。
        return f"FAIL: compile — {last_error_line(error.stderr)}"

    with tempfile.NamedTemporaryFile(suffix=".out", delete=False) as tmp:
        bin_path = Path(tmp.name)

    try:
        result = subprocess.run(
            [str(gcc_bin), "-x", "assembler", "-static", "-", "-o", str(bin_path)],
            input=asm, capture_output=True, text=True,
        )
        if result.returncode != 0:
            return f"FAIL: assemble — {last_error_line(result.stderr)}"

        result = subprocess.run(
            [str(qemu_bin), str(bin_path)],
            capture_output=True, text=True,
        )
        actual_code = result.returncode
        actual_out = result.stdout
    finally:
        bin_path.unlink(missing_ok=True)

    if actual_code != expected_code:
        return f"FAIL: exit code expected={expected_code} got={actual_code}"

    if out_file.exists() and actual_out != expected_out:
        return f"FAIL: stdout mismatch\n  expected: {expected_out!r}\n  got:      {actual_out!r}"

    return "PASS"


def main():
    parser = argparse.ArgumentParser(description="mycc テストランナー")
    parser.add_argument("session_dir", nargs="?", help="セッションディレクトリ (例: sessions/05_loops)")
    parser.add_argument("--compiler", help="コンパイラのパス (デフォルト: final/mycc.py)")
    parser.add_argument("--tests", dest="tests_dir", help="テストディレクトリのパス (デフォルト: final/tests)")
    args = parser.parse_args()

    compiler_path = args.compiler or "final/mycc.py"
    tests_dir = args.tests_dir or "final/tests"

    if args.session_dir:
        compiler_path = f"{args.session_dir}/mycc.py"
        tests_dir = f"{args.session_dir}/tests"

    compiler_path = resolve_path(compiler_path)
    tests_dir = resolve_path(tests_dir)

    if not compiler_path.is_file():
        print(f"compiler not found: {compiler_path}", file=sys.stderr)
        raise SystemExit(2)

    if not tests_dir.is_dir():
        print(f"tests directory not found: {tests_dir}", file=sys.stderr)
        raise SystemExit(2)

    gcc_bin = which(GCC)
    if gcc_bin is None:
        print(f"gcc not found: {GCC}", file=sys.stderr)
        print("Install the RV64 toolchain or run through docker/rv64.", file=sys.stderr)
        raise SystemExit(2)

    qemu_bin = which(QEMU)
    if qemu_bin is None:
        print(f"qemu not found: {QEMU}", file=sys.stderr)
        print("Install qemu-user or run through docker/rv64.", file=sys.stderr)
        raise SystemExit(2)

    pass_count = 0
    fail_count = 0
    skip_count = 0

    for src in sorted(Path(tests_dir).glob("*.c")):
        result = run_test(src, compiler_path, gcc_bin, qemu_bin)
        if result == "PASS":
            print(f"[PASS] {src}")
            pass_count += 1
        elif result == "SKIP":
            print(f"[SKIP] {src} (*.ans ファイルがない)")
            skip_count += 1
        else:
            print(f"[{result}] {src}")
            fail_count += 1

    print()
    print("=============================")
    print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
    print("=============================")

    if fail_count > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
