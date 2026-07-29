#!/usr/bin/env python3
"""O2: 基本ブロックとフローグラフ(スケルトン)

アセンブリを基本ブロックに切り分け、制御の流れを辺で結ぶ。
ここで作るフローグラフを、O4(生存解析)・O6(コピー伝播/死コード除去)・
O7(ブロック整列)がそのまま使う。

実装する順番:
    Step 1: find_leaders
    Step 2: build_blocks
    Step 3: build_edges

確認:
    python3 check.py
    python3 golden.py
"""

import re

# 制御が別の場所へ移る命令。ここで基本ブロックが終わる。
# call は「戻ってくる」のでブロックを切らないことに注意。
TERMINATOR = re.compile(
    r'^(j|jr|jal|jalr|ret|beq|bne|blt|bge|bltu|bgeu'
    r'|beqz|bnez|blez|bgez|bltz|bgtz)\b'
)

# 分岐・ジャンプの飛び先(最後のオペランドがラベル)
TARGET = re.compile(r'([A-Za-z_.$][\w.$]*)\s*$')


class Block:
    """基本ブロック: 途中から入らず、途中から出ない命令の並び。"""

    def __init__(self, index, start, insns, labels=None, func=None):
        self.index = index          # ブロック番号
        self.start = start          # 先頭命令の位置(insns 全体での添字)
        self.insns = list(insns)    # このブロックの命令(ラベルは含まない)
        self.labels = list(labels or ())   # このブロックの先頭に付いたラベル
        self.func = func            # 属する関数名

    @property
    def last(self):
        return self.insns[-1] if self.insns else ''

    def __repr__(self):
        head = self.labels[0] if self.labels else f'#{self.index}'
        return f'<Block {self.index} {head} {len(self.insns)}命令>'


# ---------------------------------------------------------------
# 前処理(完成済み)
# ---------------------------------------------------------------


def strip_asm(lines):
    """アセンブリから命令だけを取り出し、ラベルの飛び先を表に作る。

    返り値は (insns, labels)。
        insns  … 命令の文字列リスト(空白は詰めてある)
        labels … ラベル名 → そのラベルが指す命令の位置

    ディレクティブ(`.globl` など)とコメントは落とす。
    `.data` / `.bss` 節は `.text` が現れるまで読み飛ばす。
    """
    insns = []
    labels = {}
    pending = []
    started = False
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s == '.text':
            started = True
            continue
        if not started:
            continue                       # .data / .bss 節
        if s.endswith(':'):
            pending.append(s[:-1])
            continue
        if s.startswith('.'):
            continue                       # .globl などのディレクティブ
        for name in pending:
            labels[name] = len(insns)
        pending.clear()
        insns.append(s)
    return insns, labels


def is_terminator(insn):
    """この命令でブロックが終わるなら True(完成済み)。"""
    return bool(TERMINATOR.match(insn))


def branch_target(insn):
    """分岐・ジャンプの飛び先ラベル。飛び先を持たなければ None(完成済み)。"""
    if not is_terminator(insn):
        return None
    mnemonic = insn.split()[0]
    if mnemonic in ('ret', 'jr', 'jalr'):
        return None
    m = TARGET.search(insn)
    return m.group(1) if m else None


# ---------------------------------------------------------------
# Step 1: リーダを見つける
# ---------------------------------------------------------------


def find_leaders(insns, labels):
    """基本ブロックの先頭になる命令の位置(insns の添字)の集合を返す。"""
    # TODO(Step 1)
    #
    # リーダの規則は3つ。
    #   (a) 最初の命令(insns が空でなければ 0)
    #   (b) ラベルが指す命令。labels の値がそれ(len(insns) と等しいこともある。
    #       末尾のラベルは命令を指していないので入れない)
    #   (c) 分岐・ジャンプ・ret の**次**の命令。
    #       is_terminator(insns[i]) が真で i + 1 < len(insns) なら i + 1
    #
    # call はリーダを作らない(呼び出しから戻ってきて次の命令へ進むため)。
    # TERMINATOR に call が入っていないのはそのため。
    raise NotImplementedError("Step 1: find_leaders を実装する")


# ---------------------------------------------------------------
# Step 2: ブロックに切る
# ---------------------------------------------------------------


def build_blocks(insns, leaders, labels=None):
    """リーダの位置で命令列を切り分け、Block のリストを返す。"""
    # TODO(Step 2)
    #
    # 方針:
    #   - leaders を昇順に並べる
    #   - n 番目のリーダから、次のリーダの手前まで(最後なら末尾まで)が1ブロック
    #   - Block(番号, 先頭位置, 命令のリスト, labels=そこに付いたラベル) を作る
    #
    # ラベルの対応づけには次の表を使うとよい(位置 → その位置に付いたラベル)。
    #   label_at = {}
    #   for name, pos in (labels or {}).items():
    #       label_at.setdefault(pos, []).append(name)
    #
    # ブロック番号は 0 から順に振る。insns が空ならブロックも空。
    raise NotImplementedError("Step 2: build_blocks を実装する")


# ---------------------------------------------------------------
# Step 3: 辺を張る
# ---------------------------------------------------------------


def build_edges(blocks, labels):
    """ブロック番号 → 次に実行されうるブロック番号のリスト。"""
    # TODO(Step 3)
    #
    # 各ブロックの**最後の命令**を見て、次に何が起きるかを決める。
    #
    #   ret / jr          … 関数から出る            → 後続なし
    #   j L / jal L       … 必ず L へ               → L のブロックだけ
    #   beqz rX, L など   … 飛ぶか、飛ばずに次へ    → L のブロックと、次のブロック
    #   それ以外          … 次がリーダだったので切れただけ → 次のブロック
    #
    # ラベル L がどのブロックかは、labels[L] で命令の位置を引き、
    # その位置を先頭に持つブロックを探せばよい。
    #   start_of = {b.start: b.index for b in blocks}
    #
    # 飛び先の取り出しには branch_target(insn) を使う。
    # 同じ後続が2回入らないように注意する(重複は取り除く)。
    #
    # 返り値はすべてのブロック番号を鍵に持つ辞書
    # (後続が無いブロックも空リストで入れる)。
    raise NotImplementedError("Step 3: build_edges を実装する")


# ---------------------------------------------------------------
# 組み立てと可視化(完成済み)
# ---------------------------------------------------------------


def assign_functions(blocks, labels):
    """各ブロックがどの関数に属するかを記録する(`.` で始まらないラベル)。"""
    func_at = {pos: name for name, pos in labels.items()
               if not name.startswith('.')}
    current = None
    for b in blocks:
        if b.start in func_at:
            current = func_at[b.start]
        b.func = current
    return blocks


def build_cfg(lines):
    """アセンブリの行リストから (blocks, edges) を作る。"""
    insns, labels = strip_asm(lines)
    leaders = find_leaders(insns, labels)
    blocks = build_blocks(insns, leaders, labels)
    edges = build_edges(blocks, labels)
    assign_functions(blocks, labels)
    return blocks, edges


def blocks_of(blocks, func):
    """特定の関数に属するブロックだけを取り出す。"""
    return [b for b in blocks if b.func == func]


def back_edges(blocks, edges):
    """後方辺(ループの戻り)を集める。

    ここでは支配関係を計算せず、「自分より前のブロックへ戻る辺」を後方辺とみなす。
    いまのコンパイラが出す while / for はこの簡易判定で正しく拾える。
    """
    return [(n, s) for n, succs in sorted(edges.items())
            for s in succs if s <= n]


def _escape(text):
    return (text.replace('\\', '\\\\').replace('"', '\\"')
            .replace('<', '\\<').replace('>', '\\>')
            .replace('{', '\\{').replace('}', '\\}'))


def to_dot(blocks, edges, annot=None, func=None):
    """Graphviz の dot 形式で書き出す(完成済み)。

    annot に {ブロック番号: 追加の文字列} を渡すと、各ブロックに注記を付ける
    (O4 で live_in / live_out を表示するために使う)。
    """
    target = [b for b in blocks if func is None or b.func == func]
    keep = {b.index for b in target}
    out = ['digraph cfg {', '  node [shape=box fontname="monospace" fontsize=10];']
    for b in target:
        head = ' '.join(b.labels) or f'B{b.index}'
        body = '\\l'.join(_escape(i) for i in b.insns)
        note = (annot or {}).get(b.index)
        text = f'{_escape(head)}\\l{body}\\l'
        if note:
            # 注記の改行は Graphviz の左寄せ改行 \l に変換する
            note_text = _escape(note).rstrip('\n').replace('\n', '\\l') + '\\l'
            text = f'{text}|{note_text}'
            out.append(f'  b{b.index} [shape=record label="{{{text}}}"];')
        else:
            out.append(f'  b{b.index} [label="{text}"];')
    for n, succs in sorted(edges.items()):
        if n not in keep:
            continue
        for s in succs:
            if s in keep:
                style = ' [style=dashed]' if s <= n else ''
                out.append(f'  b{n} -> b{s}{style};')
    out.append('}')
    return '\n'.join(out) + '\n'
