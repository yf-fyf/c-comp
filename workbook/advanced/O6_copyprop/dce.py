#!/usr/bin/env python3
"""O6: 死コード除去(スケルトン)

O5 の生存解析を使い、「書いた値が誰にも読まれない」命令を消す。
副作用のある命令は、結果が読まれなくても消してはいけない。

実装する順番:
    Step 4: has_side_effect
    Step 5: is_dead
    Step 6: run

確認:
    python3 check.py
    python3 golden.py
"""

import importlib.util
import os
from pathlib import Path

DIR = Path(__file__).resolve().parent

# 副作用がある(= 結果が読まれなくても消せない)命令
SIDE_EFFECT = ('sd', 'sw', 'sh', 'sb', 'call', 'jal', 'jalr',
               'ret', 'jr', 'j', 'ecall', 'ebreak')


def _load(name, subdir, filename):
    """前提の回のモジュールを読み込む(完成済み)。"""
    candidates = [DIR.parent / subdir / filename]
    answers = os.environ.get("OPTCC_ANSWERS")
    if answers:
        candidates.append(Path(answers) / subdir / filename)
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location(name, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit(
        f"{subdir}/{filename} が見つからない。先にその回を終わらせる。\n"
        f"探した場所: {', '.join(str(p) for p in candidates)}"
    )


cfg = _load("dce_uses_cfg", "O2_cfg", "cfg.py")
lv = _load("dce_uses_liveness", "O5_liveness", "liveness.py")


# ---------------------------------------------------------------
# Step 4: 消してはいけない命令
# ---------------------------------------------------------------


def has_side_effect(insn):
    """結果が読まれなくても消してはいけない命令なら True。"""
    # TODO(Step 4)
    #
    # ニーモニックが SIDE_EFFECT に入っているか、`b` で始まる(条件分岐)なら True。
    #
    # なぜストアを消せないか: `sw a0, -24(s0)` はレジスタには何も書かないので、
    # 「書いた先が生きていない」という判定では必ず消える対象に見えてしまう。
    # しかし実際にはメモリを書き換えている。消すとプログラムの意味が変わる。
    raise NotImplementedError("Step 4: has_side_effect を実装する")


# ---------------------------------------------------------------
# Step 5: 死んでいるかを判定する
# ---------------------------------------------------------------


def is_dead(insn, live):
    """insn の**直後**の生存集合が live のとき、この命令を消してよいか。"""
    # TODO(Step 5)
    #
    #   1. has_side_effect(insn) なら False(消せない)
    #   2. lv.def_use(insn) の defs が空なら False(そもそも何も書いていない)
    #   3. defs と live に共通のレジスタが**1つも無ければ** True
    #      = 書いた値が誰にも読まれない
    raise NotImplementedError("Step 5: is_dead を実装する")


# ---------------------------------------------------------------
# Step 6: 全体に適用する
# ---------------------------------------------------------------


def run(lines):
    """optcc.py から呼ばれる入口。消えなくなるまで繰り返す。"""
    # TODO(Step 6)
    #
    # 次を、消せる命令が無くなるまで繰り返す。
    #   1. blocks, edges = cfg.build_cfg(lines)
    #   2. after = lv.live_after(blocks, edges)
    #   3. 各ブロックの各命令について is_dead を判定し、
    #      消す命令の通し番号(b.start + 位置)を集める
    #   4. 1つも無ければ lines を返して終わり
    #   5. あれば _drop(lines, dead) で落として、もう一周する
    #
    # **繰り返しが要る理由**: 1つ消すと、その命令が読んでいた値が
    # 誰にも読まれなくなり、別の命令が新たに死ぬことがある。
    #     li  a1, 5      ← 2周目で死ぬ
    #     add a0, a1, a1 ← 1周目で死ぬ
    raise NotImplementedError("Step 6: run を実装する")


def _drop(lines, dead):
    """通し番号が dead に入っている命令の行を落とす(完成済み)。"""
    out = []
    n = 0
    started = False
    for raw in lines:
        s = raw.strip()
        if s == '.text':
            started = True
        is_insn = (started and s and not s.startswith('#')
                   and not s.endswith(':') and not s.startswith('.'))
        if is_insn:
            if n not in dead:
                out.append(raw)
            n += 1
        else:
            out.append(raw)
    return out
