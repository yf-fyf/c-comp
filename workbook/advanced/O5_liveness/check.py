#!/usr/bin/env python3
"""O5 確認スクリプト — liveness.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの liveness.py
    python3 check.py path/to/answers_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O5_liveness" / "liveness.py").is_file():
    passes_dir = passes_dir / "O5_liveness"

spec = importlib.util.spec_from_file_location("O5_liveness", passes_dir / "liveness.py")
lv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lv)
cfg = lv.cfg

pass_count = 0
fail_count = 0
skip_count = 0

O2_FUNCS = ("find_leaders", "build_blocks", "build_edges")


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
        if any(f in str(e) for f in O2_FUNCS):
            print(f"  [SKIP] O2 の cfg.py が未完成: {e}")
            print("         この回は O2(フローグラフ)を前提にしている。"
                  "先に O2_cfg/check.py を全 PASS にする")
        else:
            print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


# 小さなループ:
#   main:  li s1, 0
#   .L1:   beqz s1, .L2
#          addi s1, s1, -1
#          j .L1
#   .L2:   mv a0, s1
#          ret
LOOP = [
    '  .text',
    'main:',
    '  li s1, 0',
    '.L1:',
    '  beqz s1, .L2',
    '  addi s1, s1, -1',
    '  j .L1',
    '.L2:',
    '  mv a0, s1',
    '  ret',
]


def build():
    return cfg.build_cfg(LOOP)


# ---------------------------------------------------------------
# Step 1: def_use
# ---------------------------------------------------------------


def step1():
    check("算術: 第1オペランドに書き、残りを読む",
          lv.def_use('add a0, a1, a2'), ({'a0'}, {'a1', 'a2'}))
    check("li: 定数は use にならない",
          lv.def_use('li a0, 5'), ({'a0'}, set()))
    check("mv", lv.def_use('mv a0, s1'), ({'a0'}, {'s1'}))
    check("ロード: ベースを読み、行き先に書く",
          lv.def_use('lw a0, -24(s0)'), ({'a0'}, {'s0'}))
    check("ストア: def は空(メモリに書くのでレジスタは変わらない)",
          lv.def_use('sw a0, -24(s0)'), (set(), {'a0', 's0'}))
    check("条件分岐: 読むだけ。飛び先ラベルは外す",
          lv.def_use('beqz a0, .L4'), (set(), {'a0'}))
    check("無条件ジャンプ", lv.def_use('j .L2'), (set(), set()))

    defs, uses = lv.def_use('call f')
    check("call は caller-saved を壊す", defs, set(lv.CALLER_SAVED))
    check("call は引数レジスタを読む(安全側)", uses, set(lv.ARG_REGS))

    check("ret", lv.def_use('ret'), (set(), set(lv.RETURN_USES)))
    check("ret は callee-saved も読む(エピローグの復帰を死コードにしない)",
          {'s1', 's2', 's11'} <= lv.def_use('ret')[1], True)
    check("ret は caller-saved の t を読まない",
          't0' in lv.def_use('ret')[1], False)


# ---------------------------------------------------------------
# Step 2: block_def_use / solve
# ---------------------------------------------------------------


def step2():
    blocks, edges = build()

    class B:
        insns = ['li a0, 5', 'add a1, a0, s1', 'mv a0, s2']

    defs, uses = lv.block_def_use(B())
    check("ブロックの def", defs, {'a0', 'a1'})
    check("書かれる前に読まれたものだけが use", uses, {'s1', 's2'})

    live_in, live_out = lv.solve(blocks, edges)
    # B0=main(li s1,0) B1=.L1(beqz) B2=(addi, j) B3=.L2(mv a0,s1 / ret)
    check("ループの中で s1 が生きている", 's1' in live_out[1], True)
    check("s1 を書く前(入口)では s1 は生きていない",
          's1' in live_in[0], False)
    check("最後のブロックの live_out は空", live_out[3], set())
    check("ret が読む ra は、書かれていないので入口から生きている",
          'ra' in live_in[3], True)
    check("a0 はブロックの中で書かれてから読まれるので、入口では生きていない",
          'a0' in live_in[3], False)

    check("live_in / live_out の長さがブロック数と同じ",
          (len(live_in), len(live_out)), (4, 4))


# ---------------------------------------------------------------
# Step 3: live_after
# ---------------------------------------------------------------


def step3():
    blocks, edges = build()
    after = lv.live_after(blocks, edges)
    check("命令の数だけ結果がある", len(after), 6)

    ret_pos = blocks[3].start + 1                 # `ret`
    check("ret の直後には何も生きていない", after[ret_pos], set())

    mv_pos = blocks[3].start                      # `mv a0, s1`
    check("mv の直後では a0 が生きている(ret が読む)",
          'a0' in after[mv_pos], True)
    check("関数の出口では callee-saved も生きている"
          "(呼び出し元へ返す義務があるため)",
          's1' in after[mv_pos], True)


# ---------------------------------------------------------------
# Step 4: live_across_calls
# ---------------------------------------------------------------


def step4():
    blocks, edges = build()
    check("呼び出しが無ければ空", lv.live_across_calls(blocks, edges), set())

    # s1 を call の前後で使う例
    withcall = [
        '  .text',
        'main:',
        '  li s1, 3',
        '  call f',
        '  mv a0, s1',
        '  ret',
    ]
    blocks, edges = cfg.build_cfg(withcall)
    across = lv.live_across_calls(blocks, edges)
    check("呼び出しをまたいで生きる s1 を見つける", 's1' in across, True)


run_step("Step 1: def_use", step1)
run_step("Step 2: block_def_use / solve", step2)
run_step("Step 3: live_after", step3)
run_step("Step 4: live_across_calls", step4)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
