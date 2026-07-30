#!/usr/bin/env python3
"""O1 確認スクリプト — measure.py をテストする

使い方:
    python3 check.py                      # 同じディレクトリの measure.py
    python3 check.py path/to/answers_dir

Step 2 は実際に qemu で走らせて確かめるので、少し時間がかかる。
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O1_measure" / "measure.py").is_file():
    passes_dir = passes_dir / "O1_measure"

spec = importlib.util.spec_from_file_location("O1_measure", passes_dir / "measure.py")
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)

import os  # noqa: E402
COMPILER = Path(os.environ.get("OPT_COMPILER", WORKBOOK / "final" / "mycc.py"))
GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")

pass_count = 0
fail_count = 0
skip_count = 0

SAMPLE_ASM = """  .text
  .globl main
main:
  addi sp, sp, -16
  sd ra, 8(sp)
# コメント
  li a0, 42

.L1:
  ret
  .word 3
"""


def check(label, ok, detail=""):
    global pass_count, fail_count
    if ok:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}{(' — ' + detail) if detail else ''}")
        fail_count += 1


def run_step(name, fn):
    global skip_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


def build(src_text, workdir, name):
    """C ソースをコンパイルして実行ファイルを作る(完成済みの補助)。"""
    csrc = workdir / f"{name}.c"
    csrc.write_text(src_text)
    r = subprocess.run([sys.executable, str(COMPILER), str(csrc)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"コンパイル失敗: {r.stderr[:200]}")
    asm = r.stdout
    exe = workdir / name
    link = subprocess.run([GCC, "-x", "assembler", "-static", "-", "-o", str(exe)],
                          input=asm, capture_output=True, text=True)
    if link.returncode != 0:
        raise RuntimeError(f"アセンブル失敗: {link.stderr[:200]}")
    return asm, exe


def loop_program(n):
    return ("int main() { int i; int s; s = 0;"
            f" for (i = 0; i < {n}; i = i + 1) {{ s = s + i; }}"
            " return s % 256; }\n")


# ---------------------------------------------------------------
# Step 1: count_static
# ---------------------------------------------------------------


def step1():
    check("命令だけを数える(ラベル・ディレクティブ・コメントは除く)",
          me.count_static(SAMPLE_ASM) == 4,
          f"期待 4、実際 {me.count_static(SAMPLE_ASM)}")
    check("空文字列は 0", me.count_static("") == 0)
    check("ラベルだけなら 0", me.count_static(".L1:\nmain:\n") == 0)
    check("ディレクティブだけなら 0",
          me.count_static("  .text\n  .globl main\n  .word 7\n") == 0)
    check("インデントの有無によらず数える",
          me.count_static("ret\n  ret\n\tret\n") == 3)


# ---------------------------------------------------------------
# Step 2: count_dynamic
# ---------------------------------------------------------------


def step2():
    if shutil.which("qemu-riscv64") is None or shutil.which(GCC) is None:
        print("  [SKIP] qemu / gcc が無いので動的計測は確認できません")
        return
    if not COMPILER.is_file():
        print(f"  [SKIP] コンパイラが見つかりません: {COMPILER}")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        asm100, exe100 = build(loop_program(100), tmp, "l100")
        asm200, exe200 = build(loop_program(200), tmp, "l200")

        names = me.function_names(asm100)
        check("関数名を集められる", "main" in names, str(names))

        ranges = me.our_symbol_ranges(exe100, names)
        check("main のアドレス範囲が取れる", len(ranges) >= 1, str(ranges))
        lo, hi = ranges[0]
        check("in_ranges が範囲内を真と判定する", me.in_ranges(lo, ranges))
        check("in_ranges が範囲外を偽と判定する", not me.in_ranges(lo - 0x10000, ranges))

        ours100, total100 = me.count_dynamic(exe100, names)
        ours200, total200 = me.count_dynamic(exe200, names)

        check("自作コードの実行命令数が数えられている",
              ours100 > 0, f"実際 {ours100}")
        check("自作コードは全体より少ない(libc の起動を除けている)",
              ours100 < total100, f"自作 {ours100} / 全体 {total100}")
        check("静的命令数よりずっと多い(ループで増幅されている)",
              ours100 > me.count_static(asm100) * 5,
              f"静的 {me.count_static(asm100)} / 動的 {ours100}")
        check("反復回数を2倍にすると実行命令数もほぼ2倍になる",
              1.5 * ours100 < ours200 < 2.5 * ours100,
              f"100回 {ours100} / 200回 {ours200}")
        check("静的命令数は反復回数を変えてもほとんど変わらない",
              abs(me.count_static(asm100) - me.count_static(asm200)) <= 2,
              f"{me.count_static(asm100)} vs {me.count_static(asm200)}")


run_step("Step 1: count_static", step1)
run_step("Step 2: count_dynamic", step2)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
