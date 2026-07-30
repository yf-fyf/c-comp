#!/usr/bin/env python3
"""B2 確認スクリプト — regstack.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの regstack.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("b2_regstack", passes_dir / "regstack.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

pass_count = 0
fail_count = 0
skip_count = 0


class FakeCG:
    """emit と depth だけを持つ、テスト用のコード生成器もどき。"""

    def __init__(self, depth=0):
        self.lines = []
        self.depth = depth

    def emit(self, line):
        self.lines.append(line.strip())


def check(label, actual, expected):
    global pass_count, fail_count
    if actual == expected:
        print(f"  [PASS] {label}")
        pass_count += 1
    else:
        print(f"  [FAIL] {label}")
        print(f"         expected: {expected!r}")
        print(f"         got     : {actual!r}")
        fail_count += 1


def run_step(name, fn):
    global skip_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


# ---------------------------------------------------------------
# Step 1: push_a0 / pop_into
# ---------------------------------------------------------------


def step1():
    cg = FakeCG()
    rs.push_a0(cg)
    check("depth 0 の push は t0 へ", cg.lines, ["mv t0, a0"])
    check("push で depth が増える", cg.depth, 1)

    rs.push_a0(cg)
    check("depth 1 の push は t1 へ", cg.lines[-1:], ["mv t1, a0"])

    cg2 = FakeCG(depth=2)
    rs.pop_into(cg2, 'a1')
    check("pop は1つ下の段から戻す", cg2.lines, ["mv a1, t1"])
    check("pop で depth が減る", cg2.depth, 1)

    # レジスタが尽きたらメモリへ
    cg3 = FakeCG(depth=len(rs.REGS))
    rs.push_a0(cg3)
    check("レジスタが尽きたらメモリへ",
          cg3.lines, ["addi sp, sp, -16", "sd a0, 0(sp)"])
    rs.pop_into(cg3, 'a1')
    check("メモリからの pop",
          cg3.lines[-2:], ["ld a1, 0(sp)", "addi sp, sp, 16"])

    # push と pop を往復して depth が戻る
    cg4 = FakeCG()
    for _ in range(10):
        rs.push_a0(cg4)
    for _ in range(10):
        rs.pop_into(cg4, 'a1')
    check("10回 push/pop すると depth が 0 に戻る", cg4.depth, 0)


# ---------------------------------------------------------------
# Step 2: spill_before_call / reload_after_call
# ---------------------------------------------------------------


def step2():
    cg = FakeCG(depth=0)
    rs.spill_before_call(cg)
    check("生きているレジスタがなければ何も出さない", cg.lines, [])

    cg = FakeCG(depth=1)
    rs.spill_before_call(cg)
    check("1本の退避(16 バイト確保)",
          cg.lines, ["addi sp, sp, -16", "sd t0, 0(sp)"])

    cg = FakeCG(depth=3)
    rs.spill_before_call(cg)
    check("3本の退避(32 バイトに切り上げ)",
          cg.lines,
          ["addi sp, sp, -32", "sd t0, 0(sp)", "sd t1, 8(sp)", "sd t2, 16(sp)"])

    cg = FakeCG(depth=3)
    rs.reload_after_call(cg)
    check("3本の復元",
          cg.lines,
          ["ld t0, 0(sp)", "ld t1, 8(sp)", "ld t2, 16(sp)", "addi sp, sp, 32"])

    # depth がレジスタ数を超えても、退避するのは実レジスタの分だけ
    cg = FakeCG(depth=len(rs.REGS) + 3)
    rs.spill_before_call(cg)
    n_sd = sum(1 for l in cg.lines if l.startswith("sd "))
    check("退避するのは t レジスタの本数まで", n_sd, len(rs.REGS))

    # spill と reload で sp の増減が一致する
    for d in range(1, len(rs.REGS) + 1):
        a = FakeCG(depth=d)
        b = FakeCG(depth=d)
        rs.spill_before_call(a)
        rs.reload_after_call(b)
        down = int(a.lines[0].split(", ")[-1])
        up = int(b.lines[-1].split(", ")[-1])
        if down != -up:
            check(f"depth={d} の sp 増減が一致", down, -up)
            return
    check("すべての depth で sp の増減が一致", True, True)


run_step("Step 1: push_a0 / pop_into", step1)
run_step("Step 2: spill_before_call / reload_after_call", step2)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
