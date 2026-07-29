#!/usr/bin/env python3
"""O3 確認スクリプト — isel.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの isel.py
    python3 check.py path/to/passes_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O3_isel" / "isel.py").is_file():
    passes_dir = passes_dir / "O3_isel"

spec = importlib.util.spec_from_file_location("O3_isel", passes_dir / "isel.py")
isel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isel)

pass_count = 0
fail_count = 0
skip_count = 0


def norm(lines):
    return [l.strip() for l in lines]


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
# Step 1: fold_load
# ---------------------------------------------------------------


def step1():
    out, ch = isel.fold_load(['  addi a0, s0, -24', '  lw a0, 0(a0)'])
    check("addi + lw を1命令に", norm(out), ['lw a0, -24(s0)'])
    check("変化フラグ", ch, True)

    out, _ = isel.fold_load(['  addi a0, s0, -24', '  ld a0, 0(a0)'])
    check("ld でも畳む", norm(out), ['ld a0, -24(s0)'])

    out, _ = isel.fold_load(['  addi a1, s0, -8', '  lb a1, 0(a1)'])
    check("レジスタが違っても畳む", norm(out), ['lb a1, -8(s0)'])

    keep = ['  addi a0, s0, -24', '  lw a1, 0(a0)']
    out, ch = isel.fold_load(list(keep))
    check("読み込み先が別レジスタなら畳まない", norm(out), norm(keep))
    check("変化なしフラグ", ch, False)

    keep = ['  addi a0, s0, -24', '  lw a0, 8(a0)']
    out, _ = isel.fold_load(list(keep))
    check("offset が 0 でなければ畳まない", norm(out), norm(keep))

    keep = ['  addi a0, s0, -5000', '  lw a0, 0(a0)']
    out, _ = isel.fold_load(list(keep))
    check("12ビットに収まらない offset は畳まない", norm(out), norm(keep))

    keep = ['  addi a0, s0, -24', '  ret']
    out, _ = isel.fold_load(list(keep))
    check("ロードでなければ畳まない", norm(out), norm(keep))


# ---------------------------------------------------------------
# Step 2: is_dead_after
# ---------------------------------------------------------------


def step2():
    lines = ['  addi a1, s0, -8', '  sw a0, 0(a1)', '  li a1, 3', '  ret']
    check("後で上書きされるレジスタは死んでいる",
          isel.is_dead_after(lines, 1, 'a1'), True)

    lines = ['  addi a1, s0, -8', '  sw a0, 0(a1)', '  add a0, a1, a0', '  ret']
    check("後で読まれるレジスタは生きている",
          isel.is_dead_after(lines, 1, 'a1'), False)

    lines = ['  addi sp, sp, -8', '  sd a0, 0(sp)', '  li a0, 3',
             '  ld a1, 0(sp)', '  addi sp, sp, 8']
    check("sp は後で使うので死んでいない(ここが肝)",
          isel.is_dead_after(lines, 1, 'sp'), False)

    lines = ['  addi a1, s0, -8', '  sw a0, 0(a1)', '.L1:', '  li a1, 3']
    check("ラベルより先は判断しない(安全側で False)",
          isel.is_dead_after(lines, 1, 'a1'), False)

    lines = ['  addi a1, s0, -8', '  sw a0, 0(a1)', '  call f', '  li a1, 3']
    check("呼び出しより先も判断しない",
          isel.is_dead_after(lines, 1, 'a1'), False)


# ---------------------------------------------------------------
# Step 3: fold_store / fold_mul_to_shift
# ---------------------------------------------------------------


def step3():
    lines = ['  addi a1, s0, -16', '  sw a0, 0(a1)', '  li a1, 0', '  ret']
    out, ch = isel.fold_store(lines)
    check("アドレスが死んでいれば store を畳む",
          norm(out), ['sw a0, -16(s0)', 'li a1, 0', 'ret'])

    keep = ['  addi sp, sp, -8', '  sd a0, 0(sp)', '  li a0, 3',
            '  ld a1, 0(sp)', '  addi sp, sp, 8']
    out, ch = isel.fold_store(list(keep))
    check("push の並びは畳まない(壊すため)", norm(out), norm(keep))
    check("変化なしフラグ", ch, False)

    lines = ['  li a1, 4', '  mul a0, a0, a1', '  li a1, 0', '  ret']
    out, _ = isel.fold_mul_to_shift(lines)
    check("4 倍はシフト2", norm(out), ['slli a0, a0, 2', 'li a1, 0', 'ret'])

    lines = ['  li a1, 8', '  mul a0, a0, a1', '  li a1, 0', '  ret']
    out, _ = isel.fold_mul_to_shift(lines)
    check("8 倍はシフト3", norm(out), ['slli a0, a0, 3', 'li a1, 0', 'ret'])

    keep = ['  li a1, 3', '  mul a0, a0, a1', '  li a1, 0', '  ret']
    out, _ = isel.fold_mul_to_shift(list(keep))
    check("2 の冪でなければ畳まない", norm(out), norm(keep))

    keep = ['  li a1, 4', '  mul a0, a0, a1', '  add a2, a1, a0']
    out, _ = isel.fold_mul_to_shift(list(keep))
    check("定数が後で使われるなら畳まない", norm(out), norm(keep))


# ---------------------------------------------------------------
# Step 4: run
# ---------------------------------------------------------------


def step4():
    lines = ['  addi a0, s0, -24', '  lw a0, 0(a0)',
             '  li a1, 4', '  mul a0, a0, a1', '  li a1, 0', '  ret']
    out = isel.run(list(lines))
    check("複数の畳み込みが同時に効く",
          norm(out), ['lw a0, -24(s0)', 'slli a0, a0, 2', 'li a1, 0', 'ret'])
    check("返り値は行リスト(タプルではない)", isinstance(out, list), True)

    plain = ['  li a0, 1', '  ret']
    check("畳めるものが無ければそのまま", norm(isel.run(list(plain))), norm(plain))


run_step("Step 1: fold_load", step1)
run_step("Step 2: is_dead_after", step2)
run_step("Step 3: fold_store / fold_mul_to_shift", step3)
run_step("Step 4: run", step4)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
