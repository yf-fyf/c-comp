#!/usr/bin/env python3
"""optcc — 最適化パスを合成して走らせるコンパイララッパー(完成済み。編集しない)

mycc.py には手を入れず、次の2種類の最適化を差し込む。

  1. コード生成パッチ  … コード生成器のメソッドを差し替える(--regalloc)
  2. アセンブリのパス  … 生成されたアセンブリを行単位で書き換える(--passes)

使い方:
    python3 optcc.py --passes isel file.c
    python3 optcc.py --regalloc --passes isel,copyprop,dce,layout file.c
    python3 optcc.py --passes '' file.c        # 最適化なし(基準値)

    python3 scaffold/test_runner.py \
        --compiler advanced/optcc.py --tests final/tests
    # ↑ この場合は環境変数 OPTCC_PASSES / OPTCC_REGALLOC でパスを指定する

パスの名前と実体:
    isel      O3_isel/isel.py
    copyprop  O6_copyprop/copyprop.py
    dce       O6_copyprop/dce.py
    layout    O7_layout/layout.py

いずれも `run(lines) -> lines`(アセンブリの行リストを受け取って行リストを返す)
という同じ形をしている。だから順番を変えたり組み合わせたりできる。

--regalloc だけは形が違う。アセンブリになる前のコード生成器に手を入れる
(O4_regalloc/regalloc.py の `patch(cls, mycc)`)。
局所変数をレジスタに置く判断には AST の情報が要るので、アセンブリでは遅い。

環境変数:
    OPTCC_COMPILER  ベースにするコンパイラ(既定: workbook/final/mycc.py)
    OPTCC_PASSES    適用するパス(--passes と同じ書式。--passes 未指定のとき使う)
    OPTCC_REGALLOC  1 なら --regalloc と同じ
    OPTCC_ANSWERS   実装を別ディレクトリから読む(教員用参照実装の確認用)
"""

import importlib.util
import inspect
import io
import os
import sys
from contextlib import redirect_stdout
from pathlib import Path

DIR = Path(__file__).resolve().parent
WORKBOOK = DIR.parent
SCAFFOLD = WORKBOOK / "scaffold"

# パス名 → (ディレクトリ名, ファイル名)
PASS_TABLE = {
    "isel":     ("O3_isel", "isel.py"),
    "copyprop": ("O6_copyprop", "copyprop.py"),
    "dce":      ("O6_copyprop", "dce.py"),
    "layout":   ("O7_layout", "layout.py"),
}

# コード生成パッチ(パスではないので PASS_TABLE には入れない)
REGALLOC_FILE = ("O4_regalloc", "regalloc.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def resolve_file(subdir, filename):
    """実装ファイルの場所を決める。

    OPTCC_ANSWERS が指定されていればそちらを優先する(教員用参照実装)。
    """
    answers = os.environ.get("OPTCC_ANSWERS")
    if answers:
        cand = Path(answers) / subdir / filename
        if cand.is_file():
            return cand
    return DIR / subdir / filename


def resolve_pass(name):
    if name not in PASS_TABLE:
        known = ", ".join(sorted(PASS_TABLE))
        raise SystemExit(f"知らないパス名: {name}(使えるのは: {known})")
    return resolve_file(*PASS_TABLE[name])


def parse_passes(spec):
    return [p.strip() for p in spec.split(",") if p.strip()]


def find_codegen_class(mod):
    """mycc モジュールから、_push_a0 を持つコード生成クラスを探す。"""
    best = None
    for _, obj in vars(mod).items():
        if inspect.isclass(obj) and hasattr(obj, "_push_a0"):
            # 継承関係があるときは最も派生したものを選ぶ
            if best is None or issubclass(obj, best):
                best = obj
    if best is None:
        raise RuntimeError("_push_a0 を持つコード生成クラスが見つからない")
    return best


def compile_to_asm(compiler, srcs, regalloc=False):
    """mycc を呼び出してアセンブリ文字列を得る。"""
    sys.path.insert(0, str(SCAFFOLD))
    mycc = load_module("mycc_under_optcc", compiler)
    if regalloc:
        path = resolve_file(*REGALLOC_FILE)
        if not path.is_file():
            raise SystemExit(f"regalloc の実装が見つからない: {path}")
        ra = load_module("optcc_regalloc", path)
        ra.patch(find_codegen_class(mycc), mycc)
    saved = sys.argv
    sys.argv = [str(compiler)] + srcs
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            mycc.main()
    finally:
        sys.argv = saved
    return buf.getvalue()


def apply_passes(asm, pass_names):
    """アセンブリに各パスを順に適用する。"""
    lines = asm.splitlines()
    for name in pass_names:
        path = resolve_pass(name)
        if not path.is_file():
            raise SystemExit(f"パスの実装が見つからない: {path}")
        mod = load_module(f"optcc_pass_{name}", path)
        lines = mod.run(lines)
    return "\n".join(lines) + "\n"


def main():
    args = sys.argv[1:]
    passes_spec = os.environ.get("OPTCC_PASSES", "")
    regalloc = os.environ.get("OPTCC_REGALLOC", "") == "1"
    srcs = []
    i = 0
    while i < len(args):
        if args[i] == "--passes":
            passes_spec = args[i + 1] if i + 1 < len(args) else ""
            i += 2
            continue
        if args[i].startswith("--passes="):
            passes_spec = args[i].split("=", 1)[1]
            i += 1
            continue
        if args[i] == "--regalloc":
            regalloc = True
            i += 1
            continue
        srcs.append(args[i])
        i += 1

    if not srcs:
        print("使い方: python3 optcc.py [--regalloc] [--passes isel,dce] file.c ...",
              file=sys.stderr)
        raise SystemExit(2)

    compiler = Path(os.environ.get("OPTCC_COMPILER", WORKBOOK / "final" / "mycc.py"))
    # コマ15 前は final/mycc.py が統合先のプレースホルダなので、
    # ここで弾かないと「最適化で壊れた」ように見える失敗になる。
    sys.path.insert(0, str(DIR))
    from basecc import ensure_base  # noqa: E402
    ensure_base(compiler, "OPTCC_COMPILER")

    asm = compile_to_asm(compiler, srcs, regalloc=regalloc)
    sys.stdout.write(apply_passes(asm, parse_passes(passes_spec)))


if __name__ == "__main__":
    main()
