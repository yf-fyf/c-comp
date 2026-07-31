#!/usr/bin/env python3
"""S2: int を32bitで折り返す(スケルトン)

emit される命令行を、結果の型に応じて 32bit 版へ書き換える。

RV64 には、64bit 版と 32bit 版の算術命令がある。
    add  a0, a1, a0     64bit で足す
    addw a0, a1, a0     下位32bitで足し、結果を符号拡張する(int の意味)

いまのコンパイラは常に 64bit 版を出しているので、
int の桁あふれが C のとおりに折り返さない。

実装する順番:
    Step 1: narrow

確認:
    python3 check.py
    python3 golden.py
"""

# 32bit 版がある算術命令(w を付けると下位32bitで計算し符号拡張する)
#
# addi は「アドレス計算」にも使われる(addi a0, s0, -24 など)ので入れない。
# 入れてしまうとスタック上のアドレスが 32bit に切り詰められて壊れる。
NARROWABLE = {
    'add', 'sub', 'mul', 'div', 'rem', 'neg',
}


def is_int_ty(ty):
    """ty_str が32bitで扱う型か(完成済み)。"""
    return ty in ('int', 'char')


def narrow(line, ty):
    """Step 1: 命令行 line を、結果の型 ty に応じて書き換えて返す。

    ty は「いま生成している式の型」で、ラッパーが渡してくれる。
    ポインタ型や None(型が決まらない場面)のときは何もしない。

    方針:
    1. ty が None、または is_int_ty(ty) でなければ line をそのまま返す
    2. 行の前後の空白を取り、空行・ラベル(':' で終わる)・
       ディレクティブ('.' で始まる)なら そのまま返す
    3. 先頭の語(ニーモニック)を取り出し、NARROWABLE になければそのまま返す
    4. ニーモニックの直後に 'w' を足した行を返す
       (元のインデントは保つ。'  add a0, a1, a0' → '  addw a0, a1, a0')
    """
    raise NotImplementedError("Step 1: narrow を実装する")
