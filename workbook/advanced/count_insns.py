#!/usr/bin/env python3
"""アセンブリの命令数を数える(B シリーズ共通ツール。完成済み)

使い方:
    python3 mycc.py test.c | python3 advanced/count_insns.py
    python3 count_insns.py out.s

空行・ラベル(':' で終わる行)・ディレクティブ('.' で始まる行)は数えない。
"""

import sys


def count(text):
    n = 0
    for line in text.splitlines():
        s = line.strip()
        if not s or s.endswith(':') or s.startswith('.') or s.startswith('#'):
            continue
        n += 1
    return n


def main():
    if len(sys.argv) > 1:
        for path in sys.argv[1:]:
            with open(path, encoding='utf-8') as f:
                print(f"{path}: {count(f.read())}")
    else:
        print(count(sys.stdin.read()))


if __name__ == "__main__":
    main()
