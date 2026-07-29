#!/usr/bin/env python3
"""O6 確認スクリプト — copyprop.py と dce.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの実装
    python3 check.py path/to/answers_dir
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O6_copyprop" / "copyprop.py").is_file():
    passes_dir = passes_dir / "O6_copyprop"


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, passes_dir / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cp = load("O6_copyprop", "copyprop.py")
dce = load("o6_dce", "dce.py")

pass_count = 0
fail_count = 0
skip_count = 0

PREREQ = {
    "find_leaders": "O2(O2_cfg)", "build_blocks": "O2(O2_cfg)",
    "build_edges": "O2(O2_cfg)",
    "def_use": "O5(O5_liveness)", "block_def_use": "O5(O5_liveness)",
    "solve": "O5(O5_liveness)", "live_after": "O5(O5_liveness)",
}


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
        for func, where in PREREQ.items():
            if func in str(e):
                print(f"  [SKIP] {where} が未完成: {e}")
                print(f"         この回は {where} を前提にしている。先にそちらを終わらせる")
                skip_count += 1
                return
        print(f"  [SKIP] 未実装: {e}")
        skip_count += 1


# 割り当て後によく出る形
BLOCK = [
    'mv a0, s2',
    'addi sp, sp, -8',
    'sd a0, 0(sp)',
    'mv a0, s1',
    'ld a1, 0(sp)',
    'addi sp, sp, 8',
    'add a0, a1, a0',
    'sext.w s2, a0',
]

PROG = [
    '  .text',
    '  .globl main',
    'main:',
    '  mv a1, s1',
    '  add a0, a1, a1',
    '  li a0, 7',
    '  ret',
]


# ---------------------------------------------------------------
# Step 1: replace_uses
# ---------------------------------------------------------------


def step1():
    check("読んでいるレジスタを置き換える",
          cp.replace_uses('add a0, a1, s1', 's1', 's2'), 'add a0, a1, s2')
    check("カッコの中(ベースレジスタ)も置き換える",
          cp.replace_uses('sd a0, 0(s1)', 's1', 's2'), 'sd a0, 0(s2)')
    check("ストアの第1オペランドは読んでいるので置き換える",
          cp.replace_uses('sd s1, 0(sp)', 's1', 's2'), 'sd s2, 0(sp)')
    check("書き込み先は置き換えない",
          cp.replace_uses('mv s1, a0', 's1', 's2'), 'mv s1, a0')
    check("関係ないレジスタは変えない",
          cp.replace_uses('add a0, a1, a2', 's1', 's2'), 'add a0, a1, a2')
    check("オペランドが無い命令", cp.replace_uses('ret', 's1', 's2'), 'ret')


# ---------------------------------------------------------------
# Step 2: copy_prop_block
# ---------------------------------------------------------------


def step2():
    out = cp.copy_prop_block(list(BLOCK))
    check("mv の値を使う側へ伝播する", out, [
        'mv a0, s2',
        'addi sp, sp, -8',
        'sd s2, 0(sp)',          # a0 → s2
        'mv a0, s1',
        'ld a1, 0(sp)',
        'addi sp, sp, 8',
        'add a0, a1, s1',        # a0 → s1
        'sext.w s2, a0',
    ])
    check("mv 自体は残る(消すのは dce の仕事)",
          out.count('mv a0, s2'), 1)

    danger = ['mv a1, s1', 'li s1, 0', 'add a0, a1, a1']
    check("元のレジスタが書き換わったら、そこで打ち切る",
          cp.copy_prop_block(list(danger)), danger)

    danger2 = ['mv a1, s1', 'li a1, 0', 'add a0, a1, a1']
    check("置き換え先が書き換わったら、そこで打ち切る",
          cp.copy_prop_block(list(danger2)), danger2)

    plain = ['li a0, 1', 'ret']
    check("mv が無ければそのまま", cp.copy_prop_block(list(plain)), plain)


# ---------------------------------------------------------------
# Step 3: copyprop の run
# ---------------------------------------------------------------


def step3():
    out = cp.run(list(PROG))
    check("ラベルやディレクティブは残る",
          [l for l in norm(out) if l.startswith('.') or l.endswith(':')],
          ['.text', '.globl main', 'main:'])
    check("伝播が起きている", 'add a0, s1, s1' in norm(out), True)
    check("返り値は行リスト", isinstance(out, list), True)


# ---------------------------------------------------------------
# Step 4: has_side_effect
# ---------------------------------------------------------------


def step4():
    check("ストアは消せない", dce.has_side_effect('sw a0, -24(s0)'), True)
    check("呼び出しは消せない", dce.has_side_effect('call f'), True)
    check("分岐は消せない", dce.has_side_effect('beqz a0, .L1'), True)
    check("ジャンプは消せない", dce.has_side_effect('j .L1'), True)
    check("ret は消せない", dce.has_side_effect('ret'), True)
    check("算術は消せる可能性がある", dce.has_side_effect('add a0, a1, a2'), False)
    check("ロードは消せる可能性がある", dce.has_side_effect('lw a0, 0(s0)'), False)


# ---------------------------------------------------------------
# Step 5: is_dead
# ---------------------------------------------------------------


def step5():
    check("書いた先が生きていなければ死んでいる",
          dce.is_dead('li a0, 5', {'a1', 's1'}), True)
    check("書いた先が生きていれば生きている",
          dce.is_dead('li a0, 5', {'a0'}), False)
    check("ストアは生存集合によらず消せない",
          dce.is_dead('sw a0, -24(s0)', set()), False)
    check("call は戻り値が使われなくても消せない",
          dce.is_dead('call f', set()), False)


# ---------------------------------------------------------------
# Step 6: dce の run
# ---------------------------------------------------------------


def step6():
    # add の結果は li a0, 7 に上書きされるので死ぬ。
    # すると mv a1, s1 も誰にも読まれなくなって死ぬ(繰り返しが要る)。
    out = dce.run(list(PROG))
    check("死んだ命令が消える",
          norm(out), ['.text', '.globl main', 'main:', 'li a0, 7', 'ret'])

    keep = ['  .text', 'main:', '  li a0, 7', '  ret']
    check("生きている命令は消さない", norm(dce.run(list(keep))), norm(keep))


# ---------------------------------------------------------------
# 通し: copyprop → dce
# ---------------------------------------------------------------


def step7():
    out = dce.run(cp.run(list(PROG)))
    check("2つを続けてかけても壊れない",
          norm(out), ['.text', '.globl main', 'main:', 'li a0, 7', 'ret'])


run_step("Step 1: replace_uses", step1)
run_step("Step 2: copy_prop_block", step2)
run_step("Step 3: copyprop の run", step3)
run_step("Step 4: has_side_effect", step4)
run_step("Step 5: is_dead", step5)
run_step("Step 6: dce の run", step6)
run_step("通し: copyprop → dce", step7)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
