#!/usr/bin/env python3
"""O7 確認スクリプト — layout.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの layout.py
    python3 check.py path/to/answers_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O7_layout" / "layout.py").is_file():
    passes_dir = passes_dir / "O7_layout"

spec = importlib.util.spec_from_file_location("O7_layout", passes_dir / "layout.py")
lay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lay)

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


O2_FUNCS = ("find_leaders", "build_blocks", "build_edges")


def run_step(name, fn):
    global skip_count
    print(f"--- {name} ---")
    try:
        fn()
    except NotImplementedError as e:
        if any(f in str(e) for f in O2_FUNCS):
            print(f"  [SKIP] O2 の cfg.py が未完成: {e}")
            print("         この回は O2(フローグラフ)を前提にしている。"
                  "先に O2_cfg/check.py を全 PASS にする")
        else:
            print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


# いまのコンパイラが出す while ループの形
LOOP = [
    '  .text',
    '  .globl main',
    'main:',
    '  li a0, 0',
    '.L2:',
    '  lw a0, -24(s0)',
    '  beqz a0, .L4',
    '  addi a0, a0, -1',
    '  sw a0, -24(s0)',
    '  j .L2',
    '.L4:',
    '  li a0, 0',
    '  ret',
]

ROTATED = [
    '.text',
    '.globl main',
    'main:',
    'li a0, 0',
    'j .L2',
    '.LR0:',
    'addi a0, a0, -1',
    'sw a0, -24(s0)',
    '.L2:',
    'lw a0, -24(s0)',
    'bnez a0, .LR0',
    '.L4:',
    'li a0, 0',
    'ret',
]


# ---------------------------------------------------------------
# Step 1: invert_branch
# ---------------------------------------------------------------


def step1():
    check("beqz → bnez", lay.invert_branch('beqz a0, .L4'), 'bnez a0, .L4')
    check("bnez → beqz", lay.invert_branch('bnez a0, .L4'), 'beqz a0, .L4')
    check("blt → bge", lay.invert_branch('blt a1, a0, .L2'), 'bge a1, a0, .L2')
    check("bgeu → bltu", lay.invert_branch('bgeu a1, a0, .L2'), 'bltu a1, a0, .L2')
    check("前後の空白は無視する",
          lay.invert_branch('  beqz a0, .L4  '), 'bnez a0, .L4')
    check("無条件ジャンプは反転できない", lay.invert_branch('j .L2'), None)
    check("分岐でない命令", lay.invert_branch('addi a0, a0, 1'), None)
    check("ret", lay.invert_branch('ret'), None)


# ---------------------------------------------------------------
# Step 2: rotate_one / rotate_loops
# ---------------------------------------------------------------


def step2():
    check("ループの入口を見つける", lay.loop_headers(LOOP), ['.L2'])

    out = lay.rotate_one(LOOP, '.L2', '.LR0')
    check("ループを回転する", norm(out), ROTATED)

    check("存在しないラベルは回せない",
          lay.rotate_one(LOOP, '.L9', '.LR0'), None)

    # 戻り先の直後が出口ラベルでない形(いまのコンパイラは出さない)
    odd = ['main:', '.L2:', '  beqz a0, .L4', '  j .L2', '  li a0, 1', '.L4:', '  ret']
    check("形が違えば回さない", lay.rotate_one(odd, '.L2', '.LR0'), None)

    check("rotate_loops でも同じ結果", norm(lay.rotate_loops(LOOP)), ROTATED)

    plain = ['main:', '  li a0, 1', '  ret']
    check("ループが無ければそのまま",
          norm(lay.rotate_loops(plain)), norm(plain))


# ---------------------------------------------------------------
# Step 3: remove_jump_to_next
# ---------------------------------------------------------------


def step3():
    lines = ['  j .L1', '.L1:', '  ret']
    check("次の行へのジャンプを消す",
          norm(lay.remove_jump_to_next(lines)), ['.L1:', 'ret'])

    lines = ['  j .L1', '  li a0, 1', '.L1:', '  ret']
    check("間に命令があれば消さない",
          norm(lay.remove_jump_to_next(lines)), norm(lines))

    lines = ['  j .L1', '', '.L1:', '  ret']
    check("空行はまたいで判定する",
          norm(lay.remove_jump_to_next(lines)), ['', '.L1:', 'ret'])

    lines = ['  beqz a0, .L1', '.L1:', '  ret']
    check("条件分岐は消さない(消すと意味が変わる)",
          norm(lay.remove_jump_to_next(lines)), norm(lines))


# ---------------------------------------------------------------
# Step 4: run
# ---------------------------------------------------------------


def step4():
    out = lay.run(LOOP)
    check("run は回転と削除の両方をかける", norm(out), ROTATED)
    check("返り値は行リスト(タプルではない)", isinstance(out, list), True)

    # 回転した結果 `j .L2` の直後が `.L2:` になる形は作らないが、
    # 素の出力にある `j .L1` / `.L1:` は消える
    lines = ['main:', '  li a0, 1', '  j .L1', '.L1:', '  ret']
    check("回転できなくても次行ジャンプは消える",
          norm(lay.run(lines)), ['main:', 'li a0, 1', '.L1:', 'ret'])


run_step("Step 1: invert_branch", step1)
run_step("Step 2: rotate_one / rotate_loops", step2)
run_step("Step 3: remove_jump_to_next", step3)
run_step("Step 4: run", step4)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
