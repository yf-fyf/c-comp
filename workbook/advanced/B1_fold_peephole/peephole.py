#!/usr/bin/env python3
"""B1: ピープホール最適化パス(スケルトン)

アセンブリのテキストを受け取り、小さな「窓」のパターン置換で命令を減らして返す。
部品(ラベル判定など)と全体の駆動(optimize)は完成済み。
実装するのは3つの置換規則:

    Step 2: fuse_push_const_pop
    Step 3: remove_jump_to_next / remove_branch_to_next

単体で filter としても使える:
    python3 mycc.py test.c | python3 peephole.py
"""


# ---- 部品(完成済み) ----

def strip(line):
    return line.strip()


def jump_target(line):
    """'j .L3' のような行なら飛び先ラベル名を返す。違えば None。"""
    parts = line.split()
    if len(parts) == 2 and parts[0] == 'j':
        return parts[1]
    return None


def branch_target(line):
    """'beqz a0, .L3' のような行なら飛び先ラベル名を返す。違えば None。"""
    parts = line.split()
    if len(parts) == 3 and parts[0] == 'beqz':
        return parts[2]
    return None


def _falls_to_label(lines, i, label):
    """lines[i] の直後、命令を挟まずにラベル label: が現れるか(完成済み)。

    空行と他のラベルは読み飛ばして調べる。
    """
    j = i + 1
    while j < len(lines):
        s = lines[j].strip()
        if s == '':
            j += 1
            continue
        if s.endswith(':'):
            if s[:-1] == label:
                return True
            j += 1
            continue
        return False
    return False


# ---- Step 2: push / li / pop の圧縮 ----

def fuse_push_const_pop(lines):
    """「左辺を退避 → 定数をロード → 復元」の5命令を2命令にする。

      addi sp, sp, -8
      sd a0, 0(sp)          →   mv a1, a0
      li a0, <定数>         →   li a0, <定数>
      ld a1, 0(sp)
      addi sp, sp, 8

    右辺が定数のときはスタックに退避する必要がない。
    a1 に左辺を移してから定数をロードすれば同じ状態になる。

    方針:
    - 行リストを先頭から見ていき、位置 i からの5行(strip したもの)が
      上のパターンに一致するか調べる(3行目だけ 'li a0, ' で始まるかを見る)
    - 一致したら 'mv a1, a0' と li の行(インデント2スペース)を出力して
      i を5進める。一致しなければその行をそのまま出力して i を1進める
    - 返り値は (新しい行リスト, 変化があったか) のタプル
    """
    raise NotImplementedError("Step 2: fuse_push_const_pop を実装する")


# ---- Step 3: 無意味なジャンプの削除 ----

def remove_jump_to_next(lines):
    """直後のラベルへ飛ぶだけの j を削除する。

      j .L3          ←  この行を消す
    .L3:

    方針: 各行について jump_target() で飛び先を取り、
    _falls_to_label(lines, i, 飛び先) が True ならその行を出力しない。
    返り値は (新しい行リスト, 変化があったか)。
    """
    raise NotImplementedError("Step 3: remove_jump_to_next を実装する")


def remove_branch_to_next(lines):
    """直後のラベルへ飛ぶだけの beqz を削除する。

    remove_jump_to_next と同じ形で、branch_target() を使う。
    (分岐してもしなくても次の命令は同じなので、条件ごと消してよい)
    """
    raise NotImplementedError("Step 3: remove_branch_to_next を実装する")


# ---- 全体の駆動(完成済み) ----

def optimize(asm_text):
    """変化がなくなるまで(不動点まで)3つの規則を繰り返し適用する。

    ある規則の適用で別の規則が新たに使えるようになることがあるため、
    1周では終わらせず、何も変わらなくなるまで回す。
    """
    lines = asm_text.splitlines()
    while True:
        lines, c1 = fuse_push_const_pop(lines)
        lines, c2 = remove_jump_to_next(lines)
        lines, c3 = remove_branch_to_next(lines)
        if not (c1 or c2 or c3):
            break
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    import sys
    sys.stdout.write(optimize(sys.stdin.read()))
