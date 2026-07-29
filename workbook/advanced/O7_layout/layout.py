#!/usr/bin/env python3
"""O7: ブロック整列とループ回転(スケルトン)

ループが毎回実行している「条件へ戻るジャンプ」を消す。
静的命令数はほとんど変わらないのに、動的命令数が減る。

前提は O2(cfg.py)。ループの入口はフローグラフの**後方辺**から見つける。

実装する順番:
    Step 1: invert_branch
    Step 2: rotate_one / rotate_loops
    Step 3: remove_jump_to_next
    Step 4: run

確認:
    python3 check.py
    python3 golden.py
"""

import importlib.util
import os
import re
from pathlib import Path

DIR = Path(__file__).resolve().parent

# 条件分岐の反転表(完成済み)
INVERSE = {
    'beqz': 'bnez', 'bnez': 'beqz',
    'beq': 'bne', 'bne': 'beq',
    'blt': 'bge', 'bge': 'blt',
    'bltu': 'bgeu', 'bgeu': 'bltu',
    'blez': 'bgtz', 'bgtz': 'blez',
    'bltz': 'bgez', 'bgez': 'bltz',
}

BRANCH = re.compile(r'^(b\w+)\s+(.*),\s*([A-Za-z_.$][\w.$]*)$')
JUMP = re.compile(r'^j\s+([A-Za-z_.$][\w.$]*)$')
LABEL = re.compile(r'^([A-Za-z_.$][\w.$]*):$')


def _load_cfg():
    """O2 で作った cfg.py を読み込む(完成済み)。"""
    candidates = [DIR.parent / "O2_cfg" / "cfg.py"]
    answers = os.environ.get("OPT_ANSWERS")
    if answers:
        candidates.append(Path(answers) / "O2_cfg" / "cfg.py")
    for path in candidates:
        if path.is_file():
            spec = importlib.util.spec_from_file_location("o7_uses_cfg", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    raise SystemExit(
        "O2 の cfg.py が見つからない。先に O2_cfg/cfg.py を用意する。\n"
        f"探した場所: {', '.join(str(p) for p in candidates)}"
    )


cfg = _load_cfg()


# ---------------------------------------------------------------
# Step 1: 条件を反転する
# ---------------------------------------------------------------


def invert_branch(insn):
    """条件分岐の条件を反転して返す。条件分岐でなければ None。

        'beqz a0, .L4'      →  'bnez a0, .L4'
        'blt a1, a0, .L2'   →  'bge a1, a0, .L2'
        'j .L2'             →  None
    """
    # TODO(Step 1)
    #
    # BRANCH で分解すると (ニーモニック, 飛び先以外のオペランド, 飛び先ラベル)。
    # ニーモニックが INVERSE にあれば、それを置き換えて組み直す。
    #   f'{INVERSE[mnemonic]} {operands}, {target}'
    # 先頭の空白は付けない(呼ぶ側でそろえる)。
    raise NotImplementedError("Step 1: invert_branch を実装する")


# ---------------------------------------------------------------
# Step 2: ループを回転する
# ---------------------------------------------------------------


def loop_headers(lines):
    """フローグラフを作り、ループの入口になっているラベルを集める(完成済み)。

    後方辺 (n → s) の s がループの入口(ヘッダ)である。
    """
    blocks, edges = cfg.build_cfg(lines)
    headers = []
    for _tail, head in cfg.back_edges(blocks, edges):
        for name in blocks[head].labels:
            if name not in headers:
                headers.append(name)
    return headers


def _index_of(lines, text):
    """strip したら text と一致する行の位置(完成済み)。無ければ -1。"""
    for i, line in enumerate(lines):
        if line.strip() == text:
            return i
    return -1


def _next_code(lines, start):
    """start 以降で、最初の空行・コメントでない行の位置(完成済み)。"""
    for i in range(start, len(lines)):
        s = lines[i].strip()
        if s and not s.startswith('#'):
            return i
    return -1


def rotate_one(lines, header, new_label):
    """ヘッダ header のループを1つ回転した行リストを返す。できなければ None。

        header:  <条件>                      j header
                 beqz rX, exit       new_label: <本体>
                 <本体>          →   header:    <条件>
                 j header                       bnez rX, new_label
        exit:                        exit:
    """
    # TODO(Step 2)
    #
    # 手順:
    #  1. top = _index_of(lines, f'{header}:')。見つからなければ None
    #  2. top の次から順に見て、最初の「制御が移る命令」を探す(cfg.is_terminator)。
    #     - その手前に別のラベルが来たら形が違う → None
    #     - 見つけた命令が条件分岐でなければ(invert_branch が None)→ None
    #     この位置を cond_end とする。exit ラベルは BRANCH の3番目のグループ
    #  3. cond_end の次から `j {header}`(JUMP で判定)を探す。無ければ None。
    #     この位置を back とする
    #  4. back の次の実行行が f'{exit}:' でなければ形が違う → None
    #     (ループの出口が本体の直後に来ていることの確認)
    #  5. 組み直す
    #         lines[:top]
    #       + [f'  j {header}', f'{new_label}:']
    #       + 本体 lines[cond_end+1:back]
    #       + [f'{header}:']
    #       + 条件 lines[top+1:cond_end]
    #       + [反転した分岐(飛び先を new_label に差し替えたもの)]
    #       + lines[back+1:]
    #
    # 反転した分岐の飛び先を差し替えるには、invert_branch の結果の
    # 最後の `, ラベル` を new_label に置き換える。
    #     inverted.rsplit(",", 1)[0] + f', {new_label}'
    raise NotImplementedError("Step 2: rotate_one を実装する")


def rotate_loops(lines):
    """回せるループを全部回す。"""
    # TODO(Step 2)
    #
    # loop_headers(lines) を回し、rotate_one が成功したら
    # lines を差し替えて**最初からやり直す**(行がずれるため)。
    # どのヘッダでも成功しなくなったら終わり。
    # new_label は '.LR0', '.LR1', ... のように重複しない名前を作る。
    raise NotImplementedError("Step 2: rotate_loops を実装する")


# ---------------------------------------------------------------
# Step 3: 次の行へのジャンプを消す
# ---------------------------------------------------------------


def remove_jump_to_next(lines):
    """`j L` の直後が `L:` なら、そのジャンプは要らないので消す。"""
    # TODO(Step 3)
    #
    # 各行が JUMP に一致したら、_next_code で次の実行行を探し、
    # それが f'{飛び先}:' と一致すればその `j` の行を出力しない。
    # それ以外の行はそのまま出す。
    raise NotImplementedError("Step 3: remove_jump_to_next を実装する")


# ---------------------------------------------------------------
# Step 4: まとめて適用する
# ---------------------------------------------------------------


def run(lines):
    """optcc.py から呼ばれる入口。行リストを受け取って行リストを返す。"""
    # TODO(Step 4)
    #
    # rotate_loops をかけてから remove_jump_to_next をかける。
    # 順番が逆だと、回転が作った「次の行へのジャンプ」を消し損ねる。
    raise NotImplementedError("Step 4: run を実装する")
