#!/usr/bin/env python3
"""O2 golden test — ベンチマークのフローグラフを作って検証する

使い方:
    python3 golden.py
    python3 golden.py path/to/answers_dir       # 教員用参照実装で確認する
    OPTCC_COMPILER=... python3 golden.py

1. bench/*.c のフローグラフが構造的に正しいこと
2. ブロック数・辺数・後方辺(ループの戻り)を表にすること
3. dot が使えれば cfg_out/ に図を書き出すこと
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
OPTDIR = DIR.parent
WORKBOOK = DIR.parents[1]
BENCH = OPTDIR / "O1_measure" / "bench"
OPTCC = OPTDIR / "optcc.py"
OUTDIR = DIR / "cfg_out"

passes_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DIR
if (passes_dir / "O2_cfg" / "cfg.py").is_file():
    passes_dir = passes_dir / "O2_cfg"
spec = importlib.util.spec_from_file_location("O2_cfg", passes_dir / "cfg.py")
cfg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cfg)


def compile_asm(csrc):
    r = subprocess.run([sys.executable, str(OPTCC), "--passes", "", str(csrc)],
                       capture_output=True, text=True, env=os.environ)
    if r.returncode != 0:
        raise RuntimeError(f"{csrc.name}: コンパイル失敗\n{r.stderr[:300]}")
    return r.stdout


def validate(blocks, edges):
    """フローグラフとして辻褄が合っているかを確かめる。"""
    problems = []
    n = len(blocks)
    for b in blocks:
        if not b.insns:
            problems.append(f"B{b.index}: 命令が空のブロックがある")
        if b.func is None:
            problems.append(f"B{b.index}: どの関数にも属していない")
    if sorted(edges) != list(range(n)):
        problems.append("edges の鍵が全ブロックを覆っていない")
        return problems
    for b in blocks:
        succ = edges[b.index]
        if len(set(succ)) != len(succ):
            problems.append(f"B{b.index}: 後続が重複している {succ}")
        for s in succ:
            if not 0 <= s < n:
                problems.append(f"B{b.index}: 存在しないブロック {s} へ辺がある")
        mnemonic = b.last.split()[0] if b.last else ''
        if mnemonic in ('ret', 'jr'):
            if succ:
                problems.append(f"B{b.index}: ret の後続がある {succ}")
        elif mnemonic == 'j':
            if len(succ) != 1:
                problems.append(f"B{b.index}: j の後続が1つでない {succ}")
        elif cfg.is_terminator(b.last):
            if len(succ) != 2 and b.index + 1 < n:
                problems.append(f"B{b.index}: 条件分岐の後続が2つでない {succ}")
        else:
            if succ != [b.index + 1] and b.index + 1 < n:
                problems.append(f"B{b.index}: 落ちる先が次のブロックでない {succ}")
    return problems


def main():
    print("=== 1. フローグラフを作って構造を確かめる ===")
    rows = []
    try:
        for csrc in sorted(BENCH.glob("*.c")):
            asm = compile_asm(csrc)
            blocks, edges = cfg.build_cfg(asm.splitlines())
            problems = validate(blocks, edges)
            if problems:
                print(f"{csrc.stem}: 問題あり")
                for p in problems[:5]:
                    print(f"    {p}")
                return 1
            rows.append((csrc.stem, blocks, edges))
            print(f"{csrc.stem:<12} OK")
    except NotImplementedError as e:
        print(f"\n未実装: {e}")
        print("(先に check.py を全 PASS にする)")
        return 1

    print()
    print("=== 2. 規模を測る ===")
    print(f"{'ベンチマーク':<14} {'関数':>4} {'ブロック':>8} {'辺':>5} {'後方辺':>7} {'最大ブロック':>12}")
    print("-" * 58)
    tb = te = tk = 0
    for name, blocks, edges in rows:
        funcs = {b.func for b in blocks}
        back = cfg.back_edges(blocks, edges)
        ne = sum(len(v) for v in edges.values())
        biggest = max((len(b.insns) for b in blocks), default=0)
        tb += len(blocks)
        te += ne
        tk += len(back)
        print(f"{name:<14} {len(funcs):>4} {len(blocks):>8} {ne:>5} "
              f"{len(back):>7} {biggest:>12}")
    print("-" * 58)
    print(f"{'合計':<14} {'':>4} {tb:>8} {te:>5} {tk:>7}")

    if tk == 0:
        print("\n後方辺が1つも無い。ループのあるベンチマークがあるはずなので、")
        print("build_edges の飛び先の解決を確認する。")
        return 1

    print()
    print("=== 3. 図を書き出す ===")
    OUTDIR.mkdir(exist_ok=True)
    dot = shutil.which("dot")
    for name, blocks, edges in rows:
        for func in sorted({b.func for b in blocks}):
            path = OUTDIR / f"{name}_{func}.dot"
            path.write_text(cfg.to_dot(blocks, edges, func=func), encoding="utf-8")
            if dot:
                subprocess.run([dot, "-Tpng", str(path),
                                "-o", str(path.with_suffix(".png"))], check=True)
    print(f"{OUTDIR}/ に書き出した" + ("(PNG つき)" if dot else "(dot が無いので .dot のみ)"))

    print()
    print("ループのあるベンチマークでは、後方辺(点線)が必ず1本以上ある。")
    print("これが「繰り返し」の正体であり、O7 のループ回転が狙う場所でもある。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
