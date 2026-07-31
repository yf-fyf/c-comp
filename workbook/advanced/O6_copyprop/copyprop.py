#!/usr/bin/env python3
"""O6: コピー伝播(スケルトン)

`mv rD, rS` の後で rD を読んでいる箇所を rS に置き換える。
置き換えただけでは命令は減らない。しかし `mv` が誰にも読まれなくなるので、
死コード除去(dce.py)が消せるようになる。

前提は O2(cfg.py)と O5(liveness.py)、そして O4(レジスタ割り当て)。
O4 を通していないと `mv` がほとんど出てこないので、効果が見えない。

実装する順番:
    Step 1: replace_uses
    Step 2: copy_prop_block
    Step 3: run

確認:
    python3 check.py
    python3 golden.py
"""

import importlib.util
import os
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent

MV = re.compile(r'^mv\s+(\w+),\s*(\w+)$')


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


cfg = _load("o6_uses_cfg", "O2_cfg", "cfg.py")
lv = _load("o6_uses_liveness", "O5_liveness", "liveness.py")


# ---------------------------------------------------------------
# Step 1: オペランドを置き換える
# ---------------------------------------------------------------


def replace_uses(insn, old, new):
    """命令が**読んでいる** old を new に置き換える。書き込み先は変えない。

        replace_uses('add a0, a1, s1', 's1', 's2')  → 'add a0, a1, s2'
        replace_uses('sd a0, 0(s1)',   's1', 's2')  → 'sd a0, 0(s2)'
        replace_uses('mv s1, a0',      's1', 's2')  → 'mv s1, a0'  (書き込み先)
    """
    # TODO(Step 1)
    #
    # 1. 命令をニーモニックとオペナンドに分ける
    #      parts = insn.split(None, 1)
    #      ops = [o.strip() for o in parts[1].split(',')]
    # 2. lv.def_use(insn) で「書き込み先」を調べる
    # 3. 各オペランドについて
    #      - 第1オペランド(i == 0)が書き込み先に入っているなら、そのまま
    #      - old と一致するなら new にする
    #      - `0(s1)` のようにカッコの中にあるなら、その中だけ置き換える
    #        (re.sub で `(old)` の形を `(new)` にする)
    # 4. f'{ニーモニック} ' + ', '.join(...) で組み直す
    #
    # オペランドが無い命令(`ret` など)はそのまま返す。
    raise NotImplementedError("Step 1: replace_uses を実装する")


# ---------------------------------------------------------------
# Step 2: ブロックの中で伝播する
# ---------------------------------------------------------------


def copy_prop_block(insns):
    """ブロック1つの中でコピー伝播を行い、新しい命令列を返す。"""
    # TODO(Step 2)
    #
    # copies = {}   … 「置き換え先レジスタ → 元のレジスタ」の表
    #
    # 命令を先頭から順に見て、各命令について
    #   1. lv.def_use(insn) で読んでいるレジスタを調べ、
    #      表に載っているものを replace_uses で置き換える
    #   2. 置き換えた**後**の命令で、もう一度 def_use を取る。
    #      書き込み先のレジスタが絡む表の項目は、もう使えないので消す。
    #        - copies から、書き込み先を鍵とする項目を消す
    #        - copies の**値**が書き込み先になっている項目も消す
    #          (元のレジスタが書き換わったら、コピーは同じ値でなくなる)
    #   3. その命令が `mv rD, rS`(MV に一致)なら、copies[rD] = rS を登録する
    #      ただし rD == rS のときは登録しない
    #
    # 2 を忘れるのがいちばん多い間違いである。
    #     mv  a1, s1
    #     li  s1, 0      ← ここで s1 が変わったのに
    #     add a0, a1, a1 ← a1 を s1 に置き換えたら値が違う
    #
    # **ブロックをまたがない。** またぐには「どの定義がここへ届くか」
    # (到達定義解析)が要る。
    raise NotImplementedError("Step 2: copy_prop_block を実装する")


# ---------------------------------------------------------------
# Step 3: 全体に適用する
# ---------------------------------------------------------------


def run(lines):
    """optcc.py から呼ばれる入口。行リストを受け取って行リストを返す。"""
    # TODO(Step 3)
    #
    # blocks, _edges = cfg.build_cfg(lines) でフローグラフを作り、
    # 各ブロックに copy_prop_block をかける。
    #
    # 結果は「命令の通し番号 → 新しい命令」の辞書にまとめる。
    # 通し番号は b.start + ブロック内の位置。
    # 最後に _rewrite(lines, replaced) で元の行の並びへ戻す。
    raise NotImplementedError("Step 3: run を実装する")


def _rewrite(lines, replaced):
    """命令の通し番号で置き換えた結果を、元の行の並びへ戻す(完成済み)。"""
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
            out.append('  ' + replaced.get(n, s))
            n += 1
        else:
            out.append(raw)
    return out
