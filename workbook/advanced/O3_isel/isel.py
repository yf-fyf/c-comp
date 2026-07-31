#!/usr/bin/env python3
"""O3: 命令選択(スケルトン)

複数の命令をまとめて、1命令で同じことをする。
RV64 のロード/ストアは offset(base) という形を持っているので、
直前のアドレス計算をその offset に畳み込める。

実装する順番:
    Step 1: fold_load
    Step 2: is_dead_after
    Step 3: fold_store / fold_mul_to_shift
    Step 4: run

確認:
    python3 check.py
    python3 golden.py
"""

import re

ADDI = re.compile(r'^\s*addi\s+(\w+),\s*(\w+),\s*(-?\d+)\s*$')
LOAD0 = re.compile(r'^\s*(ld|lw|lh|lb|lbu|lhu|lwu)\s+(\w+),\s*0\((\w+)\)\s*$')
STORE0 = re.compile(r'^\s*(sd|sw|sh|sb)\s+(\w+),\s*0\((\w+)\)\s*$')
LI = re.compile(r'^\s*li\s+(\w+),\s*(-?\d+)\s*$')
MUL = re.compile(r'^\s*mul\s+(\w+),\s*(\w+),\s*(\w+)\s*$')

IMM12_MIN, IMM12_MAX = -2048, 2047

# 制御が移る命令(ここで基本ブロックが切れる)
BRANCH = re.compile(r'^\s*(j|jal|jalr|ret|call|b\w+)\b')


def fits_imm12(n):
    return IMM12_MIN <= n <= IMM12_MAX


def is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def reads_reg(line, reg):
    """line がレジスタ reg を読むなら True(完成済み)。"""
    s = line.strip()
    if not s or s.endswith(':') or s.startswith('.') or s.startswith('#'):
        return False
    if s.startswith('call') or s.startswith('jal'):
        return True                      # 呼び出しは何を読むか分からない
    parts = s.split(None, 1)
    if len(parts) < 2:
        return False
    ops = [o.strip() for o in parts[1].split(',')]
    mnemonic = parts[0]
    # ロード/ストアの offset(base) の base は読む
    for o in ops:
        m = re.match(r'-?\d+\((\w+)\)$', o)
        if m and m.group(1) == reg:
            return True
    # 第1オペランドは、ストアと分岐以外では書き込み先
    start = 0 if (mnemonic.startswith('s') and '(' in parts[1]) or \
        mnemonic.startswith('b') else 1
    return any(o == reg for o in ops[start:])


def writes_reg(line, reg):
    """line がレジスタ reg に書き込むなら True(完成済み)。"""
    s = line.strip()
    if not s or s.endswith(':') or s.startswith('.') or s.startswith('#'):
        return False
    parts = s.split(None, 1)
    mnemonic = parts[0]
    if mnemonic.startswith('call') or mnemonic.startswith('jal'):
        return True                      # 呼び出しは a0 などを壊す
    if mnemonic.startswith('s') and len(parts) > 1 and '(' in parts[1]:
        return False                     # ストアはレジスタに書かない
    if mnemonic.startswith('b') or mnemonic in ('j', 'ret'):
        return False
    if len(parts) < 2:
        return False
    return parts[1].split(',')[0].strip() == reg


def is_dead_after(lines, pos, reg):
    """lines[pos] より後で reg が「読まれる前に上書きされる」なら True。

    同じ基本ブロックの中だけを見る簡易版。
    ブロックの終わり(分岐・ラベル)まで判断がつかなければ、安全側に False。
    """
    # TODO(Step 2)
    #
    # lines[pos] より後ろを1行ずつ見て、次のように判定する。
    #   - 空行やコメントは読み飛ばす
    #   - ラベル(':' で終わる)か BRANCH に一致したら、そこで基本ブロックが終わる。
    #     その先は別の経路から来るかもしれないので判断できない → False(安全側)
    #   - reads_reg(s, reg) が真 → まだ使われている → False
    #   - writes_reg(s, reg) が真 → 読まれる前に上書きされた → True(死んでいる)
    #   - 最後まで見て決まらなければ False
    raise NotImplementedError("Step 2: is_dead_after を実装する")


def fold_load(lines):
    """Step 1: addi rD, rS, N / load rD, 0(rD)  →  load rD, N(rS)

    変数を読むたびに出る形なので、これがいちばん効く。
    畳んでも rD には同じ値(読み出した値)が入るので、安全性の心配がない。

    方針:
    - 位置 i の行が ADDI に、i+1 の行が LOAD0 に一致するか調べる
    - 一致し、かつ次の3つを満たすなら畳む
        (a) ADDI の書き込み先 rD と、ロードのアドレス base が同じ
        (b) ロードの書き込み先も rD(値を同じレジスタに入れている)
        (c) fits_imm12(n) が真(offset は12ビットに収まる必要がある)
    - 畳んだ行は f'  {op} {rd}, {n}({rs})'。i を2進める
    - 一致しなければその行をそのまま出し、i を1進める
    - 返り値は (新しい行リスト, 変化があったか)
    """
    raise NotImplementedError("Step 1: fold_load を実装する")


def fold_store(lines):
    """addi rD, rS, N / store rV, 0(rD)  →  store rV, N(rS)

    rD はアドレス専用の一時レジスタなので、この後で使われていないことを確かめる。
    """
    # TODO(Step 3)
    #
    # fold_load とほぼ同じ形。ただし畳むと rD(アドレス)が消えるので、
    # is_dead_after(lines, i + 1, rd) で「この後 rD が使われない」ことを確かめる。
    #
    # この確認を忘れると、次のような並びまで畳んでしまい壊れる。
    #     addi sp, sp, -8
    #     sd a0, 0(sp)        ← 畳むと sp が変わらなくなり、スタックが壊れる
    #
    # 条件: rd == base、rv != rd、fits_imm12(n)、is_dead_after(...)
    # 畳んだ行は f'  {op} {rv}, {n}({rs})'
    raise NotImplementedError("Step 3: fold_store を実装する")


def fold_mul_to_shift(lines):
    """li rC, 2^k / mul rD, rX, rC  →  slli rD, rX, k"""
    # TODO(Step 3)
    #
    # ポインタの添字 p[i] は「i に要素サイズを掛ける」ので、
    # li a1, 4 / mul a0, a0, a1 の形が出る。4 は 2 の冪なので
    # slli a0, a0, 2(左に2ビットシフト)1命令で済む。
    #
    # 条件: mul の第3オペランドが li の書き込み先、第2オペランドはそれと別、
    #       is_power_of_two(val)、is_dead_after(...)
    # シフト量は val.bit_length() - 1(4 なら 2、8 なら 3)
    # 畳んだ行は f'  slli {rd}, {rx}, {シフト量}'
    raise NotImplementedError("Step 3: fold_mul_to_shift を実装する")


def run(lines):
    """Step 4: 変化がなくなるまで3つの畳み込みを繰り返す。

    ある畳み込みが別の畳み込みの機会を作ることがあるので、
    1周では終わらせず、何も変わらなくなるまで回す(B1 と同じ考え方)。

    返り値は行リスト(タプルではない)。optcc.py がこの形を期待している。
    """
    raise NotImplementedError("Step 4: run を実装する")
