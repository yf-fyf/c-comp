#!/usr/bin/env python3
"""B1 確認スクリプト — fold.py / peephole.py を Step ごとにテストする

使い方:
    python3 check.py                      # 同じディレクトリのパスを確認
    python3 check.py path/to/passes_dir   # 別ディレクトリのパスを確認
"""

import importlib.util
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parents[1]
SCAFFOLD = WORKBOOK / "scaffold"

passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fold = load_module("b1_fold", passes_dir / "fold.py")
peephole = load_module("b1_peephole", passes_dir / "peephole.py")

sys.path.insert(0, str(SCAFFOLD))
from lexer import tokenize                          # noqa: E402
from parser import Parser                           # noqa: E402
from parse_viewer import node_to_sexp, render_sexp  # noqa: E402
import ast_def                                      # noqa: E402

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


def fold_sexpr(src):
    """式をパースして畳み込み、S 式にする。"""
    node = Parser(tokenize(src)).parse_expr()
    node = fold.fold_node(node)
    return " ".join(render_sexp(node_to_sexp(node)).split())


# ---------------------------------------------------------------
# Step 1a: fold_binary / fold_unary(値の計算)
# ---------------------------------------------------------------


def step1a():
    check("3 + 4", fold.fold_binary(ast_def.ND_ADD, 3, 4), 7)
    check("10 - 3", fold.fold_binary(ast_def.ND_SUB, 10, 3), 7)
    check("6 * 7", fold.fold_binary(ast_def.ND_MUL, 6, 7), 42)
    check("7 / 2", fold.fold_binary(ast_def.ND_DIV, 7, 2), 3)
    check("-7 / 2 は -3(C は 0 方向切り捨て)",
          fold.fold_binary(ast_def.ND_DIV, -7, 2), -3)
    check("-7 % 2 は -1(符号は左辺と同じ)",
          fold.fold_binary(ast_def.ND_MOD, -7, 2), -1)
    check("5 / 0 は畳み込まない",
          fold.fold_binary(ast_def.ND_DIV, 5, 0), None)
    check("2 < 3", fold.fold_binary(ast_def.ND_LT, 2, 3), 1)
    check("1 && 0", fold.fold_binary(ast_def.ND_AND, 1, 0), 0)
    check("64bit の桁あふれ(4611686018427387904 == 1 << 62)",
          fold.fold_binary(ast_def.ND_MUL, 4611686018427387904, 4), 0)
    check("-(5)", fold.fold_unary(ast_def.ND_NEG, 5), -5)
    check("!0", fold.fold_unary(ast_def.ND_NOT, 0), 1)


# ---------------------------------------------------------------
# Step 1b: 木の畳み込み(S 式で確認)
# ---------------------------------------------------------------


def step1b():
    check("1 + 2 * 3", fold_sexpr("1 + 2 * 3"), "(num 7)")
    check("(100 - 3 * 7) / 4 + 1",
          fold_sexpr("(100 - 3 * 7) / 4 + 1"), "(num 20)")
    check("-(3 + 4)", fold_sexpr("-(3 + 4)"), "(num -7)")
    check("変数が混ざる部分は残る",
          fold_sexpr("a + 2 * 3"), '(add (var "a") (num 6))')
    check("ゼロ除算は残る",
          fold_sexpr("5 / 0"), "(div (num 5) (num 0))")
    check("畳み込み対象でないただの比較",
          fold_sexpr("1 < 2"), "(num 1)")
    check("f(2 * 3) の引数も畳む",
          fold_sexpr("f(2 * 3)"), '(call "f" (args (num 6)))')


# ---------------------------------------------------------------
# Step 2: fuse_push_const_pop
# ---------------------------------------------------------------

PUSH_SNIPPET = [
    "  ld a0, -24(s0)",
    "  addi sp, sp, -8",
    "  sd a0, 0(sp)",
    "  li a0, 1",
    "  ld a1, 0(sp)",
    "  addi sp, sp, 8",
    "  add a0, a1, a0",
]

PUSH_EXPECTED = [
    "  ld a0, -24(s0)",
    "  mv a1, a0",
    "  li a0, 1",
    "  add a0, a1, a0",
]


def step2():
    out, changed = peephole.fuse_push_const_pop(list(PUSH_SNIPPET))
    check("push/li/pop → mv/li", [l.rstrip() for l in out], PUSH_EXPECTED)
    check("変化フラグ", changed, True)

    # 定数でない右辺(関数呼び出しなど)は触らない
    keep = [
        "  addi sp, sp, -8",
        "  sd a0, 0(sp)",
        "  call f",
        "  ld a1, 0(sp)",
        "  addi sp, sp, 8",
    ]
    out, changed = peephole.fuse_push_const_pop(list(keep))
    check("li 以外は触らない", out, keep)
    check("変化なしフラグ", changed, False)


# ---------------------------------------------------------------
# Step 3: remove_jump_to_next / remove_branch_to_next
# ---------------------------------------------------------------


def step3():
    snippet = [
        "  beqz a0, .L1",
        "  li a0, 1",
        "  j .L2",
        ".L1:",
        "  li a0, 2",
        ".L2:",
        "  ret",
    ]
    out, changed = peephole.remove_jump_to_next(list(snippet))
    check("j .L2 は消えない(間に命令がある)",
          out, snippet)

    snippet2 = [
        "  j .L3",
        ".L3:",
        "  ret",
    ]
    out, changed = peephole.remove_jump_to_next(list(snippet2))
    check("直後ラベルへの j を削除", out, [".L3:", "  ret"])
    check("変化フラグ", changed, True)

    snippet3 = [
        "  beqz a0, .L4",
        ".L4:",
        "  ret",
    ]
    out, changed = peephole.remove_branch_to_next(list(snippet3))
    check("直後ラベルへの beqz を削除", out, [".L4:", "  ret"])

    # ラベルを挟んでも「命令を挟まなければ」削除できる
    snippet4 = [
        "  j .L6",
        ".L5:",
        ".L6:",
        "  ret",
    ]
    out, changed = peephole.remove_jump_to_next(list(snippet4))
    check("他のラベルを挟んでも削除できる",
          out, [".L5:", ".L6:", "  ret"])


# ---------------------------------------------------------------
# Step 4: optimize(全部まとめて)
# ---------------------------------------------------------------


def step4():
    asm = "\n".join(PUSH_SNIPPET + ["  j .L9", ".L9:", "  ret"]) + "\n"
    expected = "\n".join(PUSH_EXPECTED + [".L9:", "  ret"]) + "\n"
    check("optimize で両方の規則が効く", peephole.optimize(asm), expected)


run_step("Step 1a: fold_binary / fold_unary", step1a)
run_step("Step 1b: 木の畳み込み(S 式)", step1b)
run_step("Step 2: fuse_push_const_pop", step2)
run_step("Step 3: ジャンプ・分岐の削除", step3)
run_step("Step 4: optimize(不動点まで)", step4)

print()
print("=============================")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print("=============================")

if skip_count > 0:
    print("未実装の Step が残っている。SKIP は未達なので、完了条件は満たしていない。")
if fail_count > 0 or skip_count > 0:
    raise SystemExit(1)
