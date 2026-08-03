#!/usr/bin/env python3
"""発展課題が土台にするコンパイラの健全性チェック（共有ツール）。

B・O・S・L 系列は、学習者が完成させた `final/mycc.py` を土台にして、
その出力を書き換えたりコード生成を差し替えたりする。

コマ15 の統合前は `final/mycc.py` が統合先のプレースホルダなので、
そのまま走らせると「最適化でテストが壊れた」ように見える失敗になる。
原因は自分のパスではなく土台なので、先にここで切り分ける。
"""

import subprocess
import sys
import tempfile
from pathlib import Path

PROBE = "int main() { return 0; }\n"


def ensure_base(compiler: Path, env_var: str) -> None:
    """土台のコンパイラが動くか確かめる。駄目なら理由と次の手を出して終了する。"""
    problem = None
    if not compiler.is_file():
        problem = f"土台のコンパイラが無い: {compiler}"
    else:
        with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False,
                                         encoding="utf-8") as probe_file:
            probe_file.write(PROBE)
            probe = Path(probe_file.name)
        try:
            result = subprocess.run(
                [sys.executable, str(compiler), str(probe)],
                capture_output=True, text=True,
            )
        finally:
            probe.unlink(missing_ok=True)
        if result.returncode != 0 or not result.stdout.strip():
            problem = f"土台のコンパイラが動かない: {compiler}"

    if problem is None:
        return

    print(problem, file=sys.stderr)
    print("golden.py は fixed17（final/tests の17件）を回すので、", file=sys.stderr)
    print("コマ15 で完成させた final/mycc.py が土台に要る。", file=sys.stderr)
    print("fixed17 には struct や malloc を使うテストが含まれるため、", file=sys.stderr)
    print("コマ14 までの mycc.py で代用することはできない。", file=sys.stderr)
    print(file=sys.stderr)
    print("コマ15 が済んでいないなら、check.py を全 PASS にするところまで進める", file=sys.stderr)
    print("（check.py は土台のコンパイラを使わない）。", file=sys.stderr)
    print("別の場所に完成した mycc.py があるなら、土台を差し替えられる:", file=sys.stderr)
    print(f"  {env_var}=/path/to/completed/mycc.py python3 golden.py", file=sys.stderr)
    raise SystemExit(2)
