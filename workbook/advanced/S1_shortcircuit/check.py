#!/usr/bin/env python3
"""S1 確認スクリプト — shortcircuit.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリの shortcircuit.py
    python3 check.py path/to/passes_dir

生成された命令列を直接見て、「右辺を飛ばす分岐があるか」を確かめる。
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"
passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR

spec = importlib.util.spec_from_file_location("S1_shortcircuit",
                                              passes_dir / "shortcircuit.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize   # noqa: E402
from parser import Parser    # noqa: E402

pass_count = 0
fail_count = 0
skip_count = 0


class FakeCG:
    """emit / codegen / new_label だけを持つコード生成器もどき。"""

    def __init__(self):
        self.lines = []
        self.n = 0

    def emit(self, line):
        self.lines.append(line.strip())

    def codegen(self, node):
        self.emit(f'# eval {node.kind}')

    def new_label(self):
        self.n += 1
        return f'.L{self.n}'


def parse_expr(src):
    return Parser(tokenize(src)).parse_expr()


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


def gen(fn, src):
    cg = FakeCG()
    fn(cg, parse_expr(src))
    return cg.lines


def index_of(lines, pred):
    for i, l in enumerate(lines):
        if pred(l):
            return i
    return -1


def common_checks(kind, lines, branch, jump_when):
    """短絡の構造ができているかを確かめる共通部分。"""
    lhs = index_of(lines, lambda l: l == '# eval Var')
    rhs = index_of(lines[lhs + 1:], lambda l: l == '# eval Num')
    rhs = rhs + lhs + 1 if rhs >= 0 else -1

    check(f"{kind}: 左辺を評価している", lhs >= 0)
    check(f"{kind}: 右辺を評価している", rhs > lhs)

    # 左辺の直後に「右辺を飛ばす分岐」があること
    between = lines[lhs + 1:rhs]
    check(f"{kind}: 左辺の直後に {branch} がある（{jump_when}）",
          any(l.startswith(branch) for l in between),
          f"左辺と右辺の間の命令: {between}")

    # ラベル定義が2つある(飛び先と合流点)
    labels = [l for l in lines if l.endswith(':')]
    check(f"{kind}: ラベルを2つ使っている", len(labels) == 2,
          f"実際は {labels}")

    # 結果は 1 か 0 に正規化される
    check(f"{kind}: 結果を 1 と 0 にしている",
          any(l == 'li a0, 1' for l in lines) and any(l == 'li a0, 0' for l in lines),
          str(lines))

    # 無条件ジャンプで合流している
    check(f"{kind}: j で合流している",
          any(l.startswith('j ') for l in lines), str(lines))


def step1():
    lines = gen(sc.gen_and, "x && 1")
    common_checks("&&", lines, 'beqz', '左が偽なら右を飛ばす')


def step2():
    lines = gen(sc.gen_or, "x || 1")
    common_checks("||", lines, 'bnez', '左が真なら右を飛ばす')

    # && と || で飛ぶ条件が逆になっていること
    and_lines = gen(sc.gen_and, "x && 1")
    check("&& と || で分岐命令が逆になっている",
          any(l.startswith('beqz') for l in and_lines)
          and any(l.startswith('bnez') for l in lines))


run_step("Step 1: gen_and", step1)
run_step("Step 2: gen_or", step2)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if fail_count > 0:
    raise SystemExit(1)
