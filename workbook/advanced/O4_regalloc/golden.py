#!/usr/bin/env python3
"""O4 golden test — 正しさと効果を測る

使い方:
    python3 golden.py
    OPTCC_COMPILER=... OPTCC_ANSWERS=... python3 golden.py

この回は**意味を壊しやすい**。効果より先に fixed17 を確認する。
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DIR = Path(__file__).resolve().parent
OPTDIR = DIR.parent
WORKBOOK = DIR.parents[1]
BENCH = OPTDIR / "O1_measure" / "bench"
RUNNER = WORKBOOK / "scaffold" / "test_runner.py"
OPTCC = OPTDIR / "optcc.py"

GCC = os.environ.get("GCC", "riscv64-linux-gnu-gcc")


def _measure_path():
    """O1 の measure.py を探す(OPTCC_ANSWERS があればそちらを優先)。"""
    answers = os.environ.get("OPTCC_ANSWERS")
    if answers:
        cand = Path(answers) / "O1_measure" / "measure.py"
        if cand.is_file():
            return cand
    return OPTDIR / "O1_measure" / "measure.py"


spec = importlib.util.spec_from_file_location("O1_measure", _measure_path())
me = importlib.util.module_from_spec(spec)
spec.loader.exec_module(me)


def run_tests(tests, regalloc, passes):
    env = dict(os.environ, OPTCC_PASSES=passes,
               OPTCC_REGALLOC="1" if regalloc else "0")
    r = subprocess.run(
        [sys.executable, str(RUNNER), "--compiler", str(OPTCC), "--tests", str(tests)],
        text=True, capture_output=True, env=env,
    )
    return r.returncode == 0, r.stdout


def build(csrc, regalloc, passes, workdir, tag):
    args = [sys.executable, str(OPTCC)]
    if regalloc:
        args.append("--regalloc")
    args += ["--passes", passes, str(csrc)]
    r = subprocess.run(args, capture_output=True, text=True, env=os.environ)
    if r.returncode != 0:
        raise RuntimeError(f"{csrc.name}: コンパイル失敗\n{r.stderr[-400:]}")
    asm = r.stdout
    exe = workdir / f"{csrc.stem}_{tag}"
    link = subprocess.run([GCC, "-x", "assembler", "-static", "-", "-o", str(exe)],
                          input=asm, capture_output=True, text=True)
    if link.returncode != 0:
        raise RuntimeError(f"{csrc.name}: アセンブル失敗\n{link.stderr[:300]}")
    return asm, exe


def main():
    print("=== 1. 正しさの確認(fixed17 を regalloc + isel で実行)===")
    try:
        ok, out = run_tests(WORKBOOK / "final" / "tests", True, "isel")
    except Exception as e:                                  # noqa: BLE001
        print(f"実行できなかった: {e}")
        return 1
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        if "NotImplementedError" in out:
            print("(未実装の Step がある。先に check.py を全 PASS にする)")
            return 1
        print()
        print("レジスタ割り当てが意味を壊している。よくある原因:")
        print("  - emit_var_assign が右辺を cg.codegen で生成していない")
        print("    (右辺の変数が古いメモリから読まれる)")
        print("  - save_restore を呼び忘れて、呼び出し元の s レジスタを壊している")
        print("  - int の代入で sext.w を使っていない(32ビットへの切り詰めが消える)")
        return 1

    print()
    print("=== 2. ベンチマークの正しさ ===")
    ok, out = run_tests(BENCH, True, "isel")
    print("\n".join(out.strip().splitlines()[-3:]))
    if not ok:
        return 1

    print()
    print("=== 3. 効果(isel だけ → isel + レジスタ割り当て)===")
    try:
        me.count_static("  ret\n")
    except NotImplementedError:
        print("O1(measure.py)が未完成のため、効果の測定は省略します。")
        print("先に O1_measure/check.py を全 PASS にしてください。")
        return 0

    print(f"{'ベンチマーク':<12} {'静的:前':>8} {'後':>7} {'削減':>6} "
          f"{'動的:前':>10} {'後':>10} {'削減':>8}")
    print("-" * 66)
    tb = ta = db = da = 0
    worse = []
    with tempfile.TemporaryDirectory() as tmp:
        for csrc in sorted(BENCH.glob("*.c")):
            asm0, exe0 = build(csrc, False, "isel", Path(tmp), "before")
            asm1, exe1 = build(csrc, True, "isel", Path(tmp), "after")
            s0, s1 = me.count_static(asm0), me.count_static(asm1)
            d0 = me.count_dynamic(exe0, me.function_names(asm0))[0]
            d1 = me.count_dynamic(exe1, me.function_names(asm1))[0]
            tb += s0
            ta += s1
            db += d0
            da += d1
            if d1 > d0:
                worse.append(csrc.stem)
            print(f"{csrc.stem:<12} {s0:>8} {s1:>7} {(s0 - s1) * 100 // s0:>5}% "
                  f"{d0:>10} {d1:>10} {(d0 - d1) * 100 / d0:>7.1f}%")
    print("-" * 66)
    print(f"{'合計':<12} {tb:>8} {ta:>7} {(tb - ta) * 100 // tb:>5}% "
          f"{db:>10} {da:>10} {(db - da) * 100 / db:>7.1f}%")

    if ta >= tb:
        print("\n命令数が減っていない。decide_promotions が空を返していないか確認する。")
        return 1

    print()
    if worse:
        print(f"遅くなったベンチマークがある: {', '.join(worse)}")
        print("callee-saved レジスタの退避・復帰の費用が、昇格の利得を上回っている。")
        print("worth_promoting で「割に合う変数」だけを選ぶ(コマ2)。")
    else:
        print("どのベンチマークも遅くなっていない。")
        print("worth_promoting が、割に合わない昇格を止めている。")
    print()
    print("残った `mv a0, sK` は O6(コピー伝播と死コード除去)で消える。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
