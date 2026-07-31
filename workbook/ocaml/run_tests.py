#!/usr/bin/env python3
"""
OCaml 参考実装の回帰テストランナー

各回の `komaNN.exe` を、対応する `sessions/NN_xxx/tests/` に掛ける。
テストケースの規約は `scaffold/test_runner.py` と同じ（`.ans` / `.stdout` / `.files`）。

判定の流れも Python 版と揃えているが、qemu 実行に**タイムアウトを設けている**点だけ
異なる。生成コードが無限ループになるとテストランナー自体が返らなくなるためである。

コマ2 だけはインタープリターでアセンブリを出さないため、
`評価結果: N` の印字を `.ans` と直接比較する。

最後に等価性テストを回す。`reference/mycc_ref.exe --no-comments` の出力が
`koma16.exe` の出力とバイト単位で一致することを、全テストソースで確かめる。

使い方:
    cd workbook/ocaml
    dune build
    python3 run_tests.py               # 全回
    python3 run_tests.py 13            # コマ13 だけ
    python3 run_tests.py 12 13 16      # 複数指定
    python3 run_tests.py --build-dir DIR   # 別ビルド（変更前版との比較用）
    python3 run_tests.py --no-equivalence  # 等価性テストを飛ばす

前提: riscv64-linux-gnu-gcc と qemu-riscv64（コマ3以降で使う）。
      無い場合は docker/rv64 経由で実行する。
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OCAML_DIR = Path(__file__).resolve().parent
WORKBOOK = OCAML_DIR.parent

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")
QEMU = os.environ.get("QEMU", "qemu-riscv64")

RESULT_RE = re.compile(r"^評価結果:\s*(-?\d+)$", re.MULTILINE)


def tests_dir_for(num: int) -> Path | None:
    """コマ番号からテストディレクトリを引く（対応表は持たず番号で照合する）"""
    if num == 16:
        # コマ16 は統合版。自前の tests を持たず final/tests を使う
        return WORKBOOK / "final" / "tests"
    matches = sorted(WORKBOOK.glob(f"sessions/{num:02d}_*/tests"))
    return matches[0] if matches else None


def extra_sources(src: Path) -> list[Path] | str:
    """`.files` に列挙された追加ソース（コマ15 の複数ファイル）"""
    files_file = src.with_suffix(".files")
    if not files_file.exists():
        return []
    extras = []
    for line in files_file.read_text().strip().splitlines():
        line = line.strip()
        if not line:
            continue
        path = src.parent / line
        if not path.is_file():
            return f"FAIL: 追加ソースがない: {path}"
        extras.append(path)
    return extras


def run_compiler_case(exe: Path, src: Path, timeout_s: int) -> str:
    """コマ3 以降: コンパイル → アセンブル → qemu 実行 → .ans / .stdout と比較"""
    ans_file = src.with_suffix(".ans")
    if not ans_file.exists():
        return "SKIP"
    expected_code = int(ans_file.read_text().strip())
    out_file = src.with_suffix(".stdout")
    expected_out = out_file.read_text() if out_file.exists() else ""

    extras = extra_sources(src)
    if isinstance(extras, str):
        return extras

    try:
        proc = subprocess.run(
            [str(exe), str(src), *(str(p) for p in extras)],
            capture_output=True, text=True, timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return f"FAIL: コンパイルが {timeout_s}s で終わらない"
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or [""])[0]
        return f"FAIL: コンパイル失敗 — {first}"

    with tempfile.NamedTemporaryFile(suffix=".out", delete=False) as tmp:
        bin_path = Path(tmp.name)
    try:
        asm = subprocess.run(
            [GCC, "-x", "assembler", "-static", "-", "-o", str(bin_path)],
            input=proc.stdout, capture_output=True, text=True,
        )
        if asm.returncode != 0:
            first = (asm.stderr.strip().splitlines() or [""])[0]
            return f"FAIL: アセンブル失敗 — {first}"
        try:
            run = subprocess.run(
                [QEMU, str(bin_path)], capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired:
            return f"FAIL: 実行が {timeout_s}s で終わらない（無限ループの疑い）"
    finally:
        bin_path.unlink(missing_ok=True)

    if run.returncode != expected_code:
        # 128 超は qemu が受けたシグナル（139 = SIGSEGV など）
        sig = f"（シグナル {run.returncode - 128}）" if run.returncode > 128 else ""
        return f"FAIL: 終了コード expected={expected_code} got={run.returncode}{sig}"
    if out_file.exists() and run.stdout != expected_out:
        return f"FAIL: 標準出力が違う\n    expected: {expected_out!r}\n    got:      {run.stdout!r}"
    return "PASS"


def run_interpreter_case(exe: Path, src: Path, timeout_s: int) -> str:
    """コマ2 用: `評価結果: N` の印字を .ans と比べる"""
    ans_file = src.with_suffix(".ans")
    if not ans_file.exists():
        return "SKIP"
    expected = int(ans_file.read_text().strip())
    try:
        proc = subprocess.run(
            [str(exe), str(src)], capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired:
        return f"FAIL: 評価が {timeout_s}s で終わらない"
    if proc.returncode != 0:
        first = (proc.stderr.strip().splitlines() or [""])[0]
        return f"FAIL: 実行時エラー — {first}"
    m = RESULT_RE.search(proc.stdout)
    if not m:
        return f"FAIL: 出力の形式が違う — {proc.stdout.strip()!r}"
    if int(m.group(1)) != expected:
        return f"FAIL: 評価結果 expected={expected} got={m.group(1)}"
    return "PASS"


def all_test_sources() -> list[Path]:
    """全回のテストソース（コマ2 のものも含む。どれも同じ C サブセットである）"""
    dirs = sorted(WORKBOOK.glob("sessions/*/tests")) + [WORKBOOK / "final" / "tests"]
    return [src for d in dirs if d.is_dir() for src in sorted(d.glob("*.c"))]


def run_equivalence_case(k16: Path, ref: Path, src: Path, timeout_s: int) -> str:
    """`koma16.exe` と `mycc_ref.exe --no-comments` の出力が一致することを確かめる。

    mycc_ref は注記コメントを足しただけの別実装なので、素の出力は koma16 と
    バイト単位で同じでなければならない。リファレンス側を書き換えたときに
    生成コードが変わっていないことを、この比較で担保する。
    """
    extras = extra_sources(src)
    if isinstance(extras, str):
        return extras
    argv = [str(src), *(str(p) for p in extras)]
    try:
        a = subprocess.run([str(k16), *argv], capture_output=True, text=True, timeout=timeout_s)
        b = subprocess.run(
            [str(ref), "--no-comments", *argv], capture_output=True, text=True, timeout=timeout_s
        )
    except subprocess.TimeoutExpired:
        return f"FAIL: コンパイルが {timeout_s}s で終わらない"
    if a.returncode != b.returncode:
        return f"FAIL: 終了コードが違う koma16={a.returncode} mycc_ref={b.returncode}"
    if a.returncode != 0:
        # 両方が同じように失敗するケース（このコーパスには無い想定）は比較対象外
        return "SKIP"
    if a.stdout != b.stdout:
        expected = a.stdout.splitlines()
        got = b.stdout.splitlines()
        for i, (x, y) in enumerate(zip(expected, got)):
            if x != y:
                return f"FAIL: {i + 1} 行目が違う\n    koma16:   {x!r}\n    mycc_ref: {y!r}"
        return f"FAIL: 行数が違う koma16={len(expected)} mycc_ref={len(got)}"
    return "PASS"


def run_equivalence(build_dir: Path, timeout_s: int, quiet: bool) -> tuple[int, int, int]:
    k16 = build_dir / "sessions" / "koma16.exe"
    ref = build_dir / "reference" / "mycc_ref.exe"
    print("\n--- 等価性 (koma16.exe == mycc_ref.exe --no-comments) ---")
    for exe in (k16, ref):
        if not exe.is_file():
            print(f"  実行ファイルがない: {exe}", file=sys.stderr)
            return (0, 1, 0)

    npass = nfail = nskip = 0
    for src in all_test_sources():
        result = run_equivalence_case(k16, ref, src, timeout_s)
        rel = src.relative_to(WORKBOOK)
        if result == "PASS":
            npass += 1
            if not quiet:
                print(f"  [PASS] {rel}")
        elif result == "SKIP":
            nskip += 1
            if not quiet:
                print(f"  [SKIP] {rel} (両方ともコンパイルできない)")
        else:
            nfail += 1
            print(f"  [{result}] {rel}")
    return (npass, nfail, nskip)


def main() -> int:
    ap = argparse.ArgumentParser(description="OCaml 参考実装の回帰テスト")
    ap.add_argument("sessions", nargs="*", type=int, help="コマ番号（省略時は全回）")
    ap.add_argument("--build-dir", default=str(OCAML_DIR / "_build" / "default"),
                    help="komaNN.exe があるディレクトリ")
    ap.add_argument("--timeout", type=int, default=15, help="1件あたりの制限秒数")
    ap.add_argument("-q", "--quiet", action="store_true", help="PASS を表示しない")
    ap.add_argument("--no-equivalence", action="store_true",
                    help="koma16 と mycc_ref の出力一致テストを飛ばす")
    args = ap.parse_args()

    build_dir = Path(args.build_dir).resolve()
    available = sorted(int(p.stem[4:]) for p in (OCAML_DIR / "sessions").glob("koma[0-9][0-9].ml"))
    if not available:
        print("komaNN.ml が見つからない", file=sys.stderr)
        return 2
    wanted = args.sessions or available
    unknown = [n for n in wanted if n not in available]
    if unknown:
        print(f"該当する実装がない: {unknown}（あるのは {available}）", file=sys.stderr)
        return 2
    if not build_dir.is_dir():
        print(f"ビルド成果物がない: {build_dir}\n先に `dune build` を実行する", file=sys.stderr)
        return 2
    for tool in (GCC, QEMU):
        if shutil.which(tool) is None:
            print(f"{tool} が見つからない。docker/rv64 経由で実行する", file=sys.stderr)
            return 2

    rows: list[tuple[str, int, int, int]] = []
    total = [0, 0, 0]
    for num in wanted:
        exe = build_dir / "sessions" / f"koma{num:02d}.exe"
        tests = tests_dir_for(num)
        label = tests.relative_to(WORKBOOK) if tests else "対象テストなし"
        print(f"\n--- コマ{num:02d} ({label}) ---")
        if not exe.is_file():
            print(f"  実行ファイルがない: {exe}", file=sys.stderr)
            rows.append((f"コマ{num:02d}", 0, 1, 0))
            total[1] += 1
            continue
        if tests is None or not tests.is_dir():
            print("  対象テストがないので飛ばす")
            rows.append((f"コマ{num:02d}", 0, 0, 0))
            continue

        npass = nfail = nskip = 0
        runner = run_interpreter_case if num == 2 else run_compiler_case
        for src in sorted(tests.glob("*.c")):
            # コマ15 の math_util.c のように、他のテストから include される
            # 補助ソースは .ans を持たないので SKIP に落ちる
            result = runner(exe, src, args.timeout)
            rel = src.relative_to(WORKBOOK)
            if result == "PASS":
                npass += 1
                if not args.quiet:
                    print(f"  [PASS] {rel}")
            elif result == "SKIP":
                nskip += 1
                if not args.quiet:
                    print(f"  [SKIP] {rel} (.ans がない)")
            else:
                nfail += 1
                print(f"  [{result}] {rel}")
        rows.append((f"コマ{num:02d}", npass, nfail, nskip))
        for i, v in enumerate((npass, nfail, nskip)):
            total[i] += v

    if not args.no_equivalence:
        npass, nfail, nskip = run_equivalence(build_dir, args.timeout, args.quiet)
        rows.append(("等価性  ", npass, nfail, nskip))
        for i, v in enumerate((npass, nfail, nskip)):
            total[i] += v

    print("\n=================================")
    for label, npass, nfail, nskip in rows:
        mark = "OK  " if nfail == 0 else "FAIL"
        print(f"  {mark} {label}  PASS: {npass:3d}  FAIL: {nfail:3d}  SKIP: {nskip:3d}")
    print("---------------------------------")
    print(f"  合計       PASS: {total[0]:3d}  FAIL: {total[1]:3d}  SKIP: {total[2]:3d}")
    print("=================================")
    return 1 if total[1] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
