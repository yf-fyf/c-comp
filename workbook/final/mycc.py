#!/usr/bin/env python3
"""コマ16の統合先: Python 版 C サブセットコンパイラ。

通常回では `sessions/NN_xxx/mycc.py` を編集する。
コマ16では、第15回までに作った完成版をこのファイルへ統合する。

統合後は次のコマンドで final/tests を実行する。

    python3 scaffold/test_runner.py
"""

import sys


def main() -> None:
    print(
        "final/mycc.py is the integration target for session 16. "
        "Copy your completed compiler here, then run: python3 scaffold/test_runner.py",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
