#!/usr/bin/env python3
"""O1: 最適化の測り方(スケルトン)

最適化の効果を測る物差しを2つ作る。

    静的命令数: 出力されたアセンブリに命令が何個あるか
    動的命令数: 実行時に命令が何回実行されたか

ループの中の1命令は何度も実行されるので、この2つは大きく食い違う。
以降の最適化の回は、すべてこの物差しで効果を語る。

実装する順番:
    Step 1: count_static
    Step 2: count_dynamic の数え上げ部分

確認:
    python3 check.py
    python3 golden.py
"""

import re
import subprocess

QEMU = "qemu-riscv64"
NM = "nm"

TRACE_PC = re.compile(r"\[[^/]*/([0-9a-f]+)/")


def count_static(asm):
    """Step 1: アセンブリのテキストから静的命令数を数える。

    方針: 1行ずつ見て、次のものは命令ではないので数えない。
      - 空行
      - ラベル(':' で終わる行)
      - ディレクティブ('.' で始まる行。.text / .globl / .word など)
      - コメント('#' で始まる行)
    残りが命令である。
    """
    raise NotImplementedError("Step 1: count_static を実装する")


def our_symbol_ranges(binary, names):
    """自作関数の [開始, 終了) アドレス範囲を求める(完成済み)。"""
    out = subprocess.run([NM, "-n", str(binary)], capture_output=True, text=True).stdout
    syms = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] in ("t", "T"):
            syms.append((int(parts[0], 16), parts[2]))
    syms.sort()
    ranges = []
    for i, (addr, name) in enumerate(syms):
        if name in names:
            end = syms[i + 1][0] if i + 1 < len(syms) else addr + 0x1000
            ranges.append((addr, end))
    return ranges


def in_ranges(pc, ranges):
    """PC が自作コードの範囲に入っているか(完成済み)。"""
    for lo, hi in ranges:
        if lo <= pc < hi:
            return True
    return False


def count_dynamic(binary, names, timeout=120):
    """qemu で実行し、自作コードの実行命令数を数える。

    -one-insn-per-tb で1命令=1トレースにし、-d exec のログ行を数える。
    ログは巨大になるのでファイルに落とさず、パイプで読みながら数える。
    """
    ranges = our_symbol_ranges(binary, names)
    proc = subprocess.Popen(
        [QEMU, "-one-insn-per-tb", "-d", "exec,nochain", str(binary)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
    )
    # TODO(Step 2): proc.stderr を1行ずつ読んで数える
    #
    # ログは1命令につき1行、次の形で出てくる。
    #   Trace 0: 0x7fe... [.../000000000001038c/.../...] _start
    #                          ↑ 実行した命令のアドレス(PC)
    #
    # 方針:
    #   - "Trace" で始まらない行は無視する
    #   - total を1増やす(プログラム全体の実行命令数)
    #   - TRACE_PC.search(line) で PC を取り出し(16進の文字列)、
    #     in_ranges(int(pc, 16), ranges) が真なら ours を1増やす
    #     (自作コードの中で実行された命令だけを数える。
    #      そうしないと libc の起動処理14万命令に埋もれてしまう)
    #   - 最後に proc.wait(timeout=timeout) してから (ours, total) を返す
    raise NotImplementedError("Step 2: count_dynamic の数え上げを実装する")


def function_names(asm):
    """アセンブリから自作関数の名前を集める(完成済み)。"""
    names = set()
    for line in asm.splitlines():
        s = line.strip()
        if s.startswith('.globl '):
            names.add(s.split()[1])
    return names
