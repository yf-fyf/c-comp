#!/usr/bin/env python3
"""コマ15の統合先: Python 版 C サブセットコンパイラ。

通常回では `sessions/NN_xxx/mycc.py` を編集する。
コマ15では、コマ14までの importlib 継承チェーンをたどり、全ハンドラを
このファイル1つのクラスへ展開する(コマ14の mycc.py をそのままコピーしても、
importlib の基準パスが変わるため動かない)。

統合後は次のコマンドで final/tests を実行する。

    python3 scaffold/test_runner.py
"""

import sys


def main() -> None:
    print(
        "final/mycc.py is the integration target for session 15. "
        "Do not copy sessions/14_preprocess_multifile/mycc.py as-is — "
        "flatten the importlib inheritance chain (sessions 01-14) into this "
        "single file, then run: python3 scaffold/test_runner.py",
        file=sys.stderr,
    )
    raise SystemExit(1)


if __name__ == "__main__":
    main()
