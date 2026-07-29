#!/usr/bin/env python3
"""O2 確認スクリプト — cfg.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの cfg.py
    python3 check.py path/to/answers_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O2_cfg" / "cfg.py").is_file():
    passes_dir = passes_dir / "O2_cfg"

spec = importlib.util.spec_from_file_location("O2_cfg", passes_dir / "cfg.py")
cfg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfg)

pass_count = 0
fail_count = 0
skip_count = 0


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


# 小さな while ループ:
#   main:  li a0, 0
#   .L1:   beqz a0, .L2
#          addi a0, a0, -1
#          j .L1
#   .L2:   ret
LOOP = [
    '  .text',
    '  .globl main',
    'main:',
    '  li a0, 0',
    '.L1:',
    '  beqz a0, .L2',
    '  addi a0, a0, -1',
    '  j .L1',
    '.L2:',
    '  ret',
]

# 呼び出しを含む直線的な列(call はブロックを切らない)
CALLSEQ = [
    '  .text',
    'f:',
    '  li a0, 1',
    '  call g',
    '  addi a0, a0, 1',
    '  ret',
]

LOOP_INSNS, LOOP_LABELS = cfg.strip_asm(LOOP)
CALL_INSNS, CALL_LABELS = cfg.strip_asm(CALLSEQ)


# ---------------------------------------------------------------
# 前処理(完成済み)が期待どおりか確かめる
# ---------------------------------------------------------------


def step0():
    check("strip_asm が命令だけを取り出す", LOOP_INSNS,
          ['li a0, 0', 'beqz a0, .L2', 'addi a0, a0, -1', 'j .L1', 'ret'])
    check("strip_asm がラベルの飛び先を作る", LOOP_LABELS,
          {'main': 0, '.L1': 1, '.L2': 4})
    check("is_terminator: 条件分岐", cfg.is_terminator('beqz a0, .L2'), True)
    check("is_terminator: call はブロックを切らない",
          cfg.is_terminator('call g'), False)
    check("branch_target", cfg.branch_target('beqz a0, .L2'), '.L2')
    check("branch_target: ret に飛び先はない", cfg.branch_target('ret'), None)


# ---------------------------------------------------------------
# Step 1: find_leaders
# ---------------------------------------------------------------


def step1():
    check("ループのリーダ", cfg.find_leaders(LOOP_INSNS, LOOP_LABELS),
          {0, 1, 2, 4})
    check("call はリーダを作らない",
          cfg.find_leaders(CALL_INSNS, CALL_LABELS), {0})

    insns = ['li a0, 1', 'ret']
    check("ret の次に命令が無ければリーダにしない",
          cfg.find_leaders(insns, {'f': 0}), {0})

    check("空の入力", cfg.find_leaders([], {}), set())


# ---------------------------------------------------------------
# Step 2: build_blocks
# ---------------------------------------------------------------


def step2():
    leaders = {0, 1, 2, 4}
    blocks = cfg.build_blocks(LOOP_INSNS, leaders, LOOP_LABELS)
    check("ブロック数", len(blocks), 4)
    check("各ブロックの命令", [b.insns for b in blocks],
          [['li a0, 0'], ['beqz a0, .L2'],
           ['addi a0, a0, -1', 'j .L1'], ['ret']])
    check("先頭位置", [b.start for b in blocks], [0, 1, 2, 4])
    check("ブロック番号", [b.index for b in blocks], [0, 1, 2, 3])
    check("ラベルの対応", [b.labels for b in blocks],
          [['main'], ['.L1'], [], ['.L2']])
    check("最後の命令", blocks[2].last, 'j .L1')

    one = cfg.build_blocks(CALL_INSNS, {0}, CALL_LABELS)
    check("call を含む列は1ブロック", len(one), 1)
    check("空の入力", cfg.build_blocks([], set(), {}), [])


# ---------------------------------------------------------------
# Step 3: build_edges
# ---------------------------------------------------------------


def step3():
    blocks = cfg.build_blocks(LOOP_INSNS, {0, 1, 2, 4}, LOOP_LABELS)
    edges = cfg.build_edges(blocks, LOOP_LABELS)
    check("落ちるだけのブロック", edges[0], [1])
    check("条件分岐は2つ(飛び先と次)", sorted(edges[1]), [2, 3])
    check("j は飛び先だけ", edges[2], [1])
    check("ret に後続はない", edges[3], [])
    check("全ブロックが鍵になっている", sorted(edges), [0, 1, 2, 3])

    check("後方辺はループの戻り", cfg.back_edges(blocks, edges), [(2, 1)])

    one = cfg.build_blocks(CALL_INSNS, {0}, CALL_LABELS)
    check("ret で終わる単独ブロック", cfg.build_edges(one, CALL_LABELS), {0: []})


# ---------------------------------------------------------------
# 通しで組み立てる
# ---------------------------------------------------------------


def step4():
    blocks, edges = cfg.build_cfg(LOOP)
    check("build_cfg のブロック数", len(blocks), 4)
    check("関数名が入る", [b.func for b in blocks], ['main'] * 4)
    dot = cfg.to_dot(blocks, edges)
    check("dot 形式で出力できる", dot.startswith('digraph cfg {'), True)
    check("辺が dot に出ている", '  b2 -> b1' in dot, True)


run_step("Step 0: 前処理(完成済み)", step0)
run_step("Step 1: find_leaders", step1)
run_step("Step 2: build_blocks", step2)
run_step("Step 3: build_edges", step3)
run_step("通し: build_cfg / to_dot", step4)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
