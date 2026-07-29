#!/usr/bin/env python3
"""O5: 生存変数解析(スケルトン)

「この地点から先で、このレジスタの値がまだ読まれるか」を
フローグラフ全体にわたって求める。**後ろ向き**のデータフロー解析。

前提は O2(cfg.py)と O4(レジスタ割り当て)。
O4 を通していない出力に対しては、ほとんど何も生きていない
—— それを最初に自分で測って確かめる。

実装する順番:
    Step 1: def_use
    Step 2: block_def_use / solve
    Step 3: live_after
    Step 4: live_across_calls

確認:
    python3 check.py
    python3 golden.py
"""

import importlib.util
import os
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent

# RV64 の呼び出し規約(完成済み)
ARG_REGS = {f'a{i}' for i in range(8)}
CALLER_SAVED = ARG_REGS | {'ra'} | {f't{i}' for i in range(7)}
# 呼び出し元へ値を返す義務があるレジスタ。関数の出口ではこれらが「生きている」。
# ここに callee-saved を入れ忘れると、エピローグの `ld s1, ...` が
# 死コードとして消され、呼び出し元のレジスタが壊れる。
CALLEE_SAVED = {'sp', 's0'} | {f's{i}' for i in range(1, 12)}
RETURN_USES = {'a0', 'ra'} | CALLEE_SAVED

MEM = re.compile(r'^(-?\d+)\((\w+)\)$')
LOADS = ('ld', 'lw', 'lh', 'lb', 'lbu', 'lhu', 'lwu')
STORES = ('sd', 'sw', 'sh', 'sb')
NO_DEF = ('j', 'ret', 'jr', 'call', 'jal', 'jalr')


def _load_cfg():
    """O2 で作った cfg.py を読み込む(完成済み)。"""
    candidates = [DIR.parent / "O2_cfg" / "cfg.py"]
    answers = os.environ.get("OPT_ANSWERS")
    if answers:
        candidates.append(Path(answers) / "O2_cfg" / "cfg.py")
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("o5_uses_cfg", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit(
        "O2 の cfg.py が見つからない。先に O2_cfg/cfg.py を用意する。\n"
        f"探した場所: {', '.join(str(p) for p in candidates)}"
    )


cfg = _load_cfg()


def _is_reg(op):
    """オペランドがレジスタ名なら True(完成済み)。"""
    return bool(re.fullmatch(r'(x\d+|zero|ra|sp|gp|tp|fp|[ats]\d+)', op))


def _base_of(op):
    """`-24(s0)` の形なら {'s0'}、そうでなければ空集合(完成済み)。"""
    m = MEM.match(op)
    return {m.group(2)} if m else set()


# ---------------------------------------------------------------
# Step 1: 命令ごとの def と use
# ---------------------------------------------------------------


def def_use(insn):
    """命令が「書くレジスタ」と「読むレジスタ」の組 (defs, uses) を返す。"""
    parts = insn.split(None, 1)
    mnemonic = parts[0]
    ops = [o.strip() for o in parts[1].split(',')] if len(parts) > 1 else []

    # --- ここから完成済み ---
    if mnemonic == 'j':
        return set(), set()                # 無条件ジャンプは何も読み書きしない
    if mnemonic.startswith('b'):
        # 条件分岐は読むだけ。最後のオペランドは飛び先ラベルなので外す
        return set(), {o for o in ops[:-1] if _is_reg(o)}
    # --- ここまで完成済み ---

    # TODO(Step 1)
    #
    # 残りを、次の表のとおりに実装する。
    #
    # | 命令               | def                | use            |
    # |--------------------|--------------------|----------------|
    # | call / jal / jalr  | CALLER_SAVED すべて | ARG_REGS すべて |
    # | ret / jr           | なし               | RETURN_USES    |
    # | sw rs2, N(rs1)     | **なし**           | rs2 と rs1     |
    # | lw rd, N(rs)       | rd                 | rs             |
    # | それ以外(算術など) | 第1オペランド      | 残りのオペランド |
    #
    # 押さえどころ:
    #   - **ストアはレジスタに書かない**。書き先はメモリなので def は空集合。
    #     ここを間違えると、生きている値を死んでいると判断してしまう
    #   - **call はレジスタを壊す**。呼ばれた側が自由に使ってよいレジスタを
    #     全部 def 扱いにする。どの引数を実際に読むかは命令からは分からないので、
    #     use も a0〜a7 全部にする(安全側に倒す)
    #   - `ret` は戻り値 a0 と復帰先 ra を読む
    #
    # ヒント:
    #   - オペランドがレジスタかどうかは _is_reg(op)
    #   - `-24(s0)` からベースを取るには _base_of(op)
    #   - `li a0, 5` の `5` はレジスタではないので _is_reg で自然に外れる
    #   - ops が空の命令(`ret` など)に ops[0] を使わないよう気をつける
    raise NotImplementedError("Step 1: def_use を実装する")


# ---------------------------------------------------------------
# Step 2: データフロー方程式を解く
# ---------------------------------------------------------------


def block_def_use(block):
    """ブロック全体の (defs, uses) を返す。

    use は「ブロックの中で、**書かれる前に**読まれる」レジスタ。
    def は「ブロックの中で書かれる」レジスタ。
    """
    # TODO(Step 2)
    #
    # ブロックの命令を**先頭から**なめる。
    #   defined = set()   … ここまでに書かれたレジスタ
    #   use     = set()   … 書かれる前に読まれたレジスタ
    # 各命令の (d, u) について
    #   use |= (u - defined)      ← まだ書かれていないものを読んだら use
    #   defined |= d
    #
    # 「書かれる前に」が肝である。
    #   mv a0, s1     ← s1 は use
    #   li a0, 5      ← a0 に書いてから
    #   add a1, a0, a0 ← 読んでいるので、この a0 は use ではない
    raise NotImplementedError("Step 2: block_def_use を実装する")


def solve(blocks, edges):
    """後ろ向きに反復して (live_in, live_out) を求める。

        live_out[B] = ∪ live_in[S]        (S は B の後続)
        live_in[B]  = use[B] ∪ (live_out[B] − def[B])

    どちらもブロック番号を添字にしたリストで返す。
    """
    # TODO(Step 2)
    #
    # 1. 全ブロックの live_in / live_out を空集合で初期化する
    # 2. 変化がなくなるまで、次を繰り返す(不動点反復)
    #      各ブロック B について(**後ろから**なめると速く収束する)
    #        live_out[B] = 後続の live_in の和集合
    #        live_in[B]  = use[B] | (live_out[B] - def[B])
    #      どれか1つでも変わったら、もう一周する
    #
    # ループがあると1周では終わらない。
    # 後方辺を通って情報が戻ってくるので、収束するまで回す必要がある。
    raise NotImplementedError("Step 2: solve を実装する")


# ---------------------------------------------------------------
# Step 3: 命令単位に展開する
# ---------------------------------------------------------------


def live_after(blocks, edges):
    """命令の**直後**で生きているレジスタ。{命令の通し番号: 集合} を返す。

    通し番号は `block.start + ブロック内の位置`。
    O6(死コード除去)がこれを使う。
    """
    # TODO(Step 3)
    #
    # solve でブロック単位の解を得たあと、各ブロックについて
    # **末尾から先頭へ** 遡りながら1命令ずつ更新する。
    #
    #   live = live_out[B] のコピー
    #   ブロックの命令を逆順に見て、各命令 i について
    #     result[B.start + i] = live のコピー   ← この命令の「直後」の生存集合
    #     d, u = def_use(命令)
    #     live -= d
    #     live |= u
    #
    # 順番に注意する。記録してから live を更新する。
    raise NotImplementedError("Step 3: live_after を実装する")


# ---------------------------------------------------------------
# Step 4: 呼び出しをまたいで生きるレジスタ
# ---------------------------------------------------------------


def live_across_calls(blocks, edges):
    """`call` の直後で生きているレジスタの集合。

    ここに現れるレジスタは、呼び出しをまたいで値を保たなければならない
    = callee-saved に置くか、退避が要る。
    """
    # TODO(Step 4)
    #
    # live_after を求め、ニーモニックが 'call' か 'jal' の命令について
    # その直後の生存集合を全部合わせる。
    raise NotImplementedError("Step 4: live_across_calls を実装する")


# ---------------------------------------------------------------
# 可視化(完成済み)
# ---------------------------------------------------------------


def annotate(blocks, edges):
    """to_dot(annot=...) に渡す注記を作る。"""
    live_in, live_out = solve(blocks, edges)
    return {b.index: (f'in : {_fmt(live_in[b.index])}\n'
                      f'out: {_fmt(live_out[b.index])}')
            for b in blocks}


def _fmt(regs):
    order = {'ra': 0, 'sp': 1, 's0': 2}
    return '{' + ', '.join(sorted(regs, key=lambda r: (order.get(r, 3), r))) + '}'
