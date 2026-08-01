#!/usr/bin/env python3
"""補助ウェブアプリのプリセットを生成する。

- examples.json      AST ビジュアライザ用。workbook/**/tests/*.c をそのまま収録する
- sim-examples.json  RV64 シミュレータ用。web/examples/asm/*.s（手書き）と、
                     参照実装 koma16 が出したアセンブリ（ゲート付き）

教材を単一の出典にするため、アプリ側にサンプルを手書きしない（design/webapps.md 1章）。
手書きのアセンブリだけは例外で、理由は web/examples/README.md に書いてある。

使い方:
    python3 tools/build_web_examples.py            # dev/ から実行
出力:
    web/app/public/examples.json      （生成物。コミットしない）
    web/app/public/sim-examples.json  （同上）
"""

import contextlib
import io
import json
import pathlib
import re
import subprocess
import sys

DEV = pathlib.Path(__file__).resolve().parents[1]
WORKBOOK = DEV / "workbook"
PUBLIC = DEV / "web" / "app" / "public"
OUT = PUBLIC / "examples.json"
SIM_OUT = PUBLIC / "sim-examples.json"
HANDWRITTEN = DEV / "web" / "examples" / "asm"
KOMA16 = WORKBOOK / "ocaml" / "_build" / "default" / "sessions" / "lecture16.exe"

sys.path.insert(0, str(WORKBOOK / "scaffold"))
from lexer import preprocess, tokenize  # noqa: E402
from parser import parse  # noqa: E402

GLOBS = ["sessions/*/tests/*.c", "final/tests/*.c", "advanced/*/tests/*.c"]


def accepts(path: pathlib.Path) -> bool:
    """スキャフォールドのパーサが受理するか（拒否時は sys.exit するので子プロセス不要の判定に置き換える）"""
    source = path.read_text(encoding="utf-8")
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parse(tokenize(preprocess(source, str(path)), str(path)))
        return True
    except SystemExit:
        return False
    except Exception:
        return False


def group_label(rel: pathlib.Path) -> str:
    # sessions/03_arithmetic_codegen/tests/x.c -> "03_arithmetic_codegen"
    # final/tests/x.c -> "final" / advanced/S1_shortcircuit/tests/x.c -> "S1_shortcircuit"
    parts = rel.parts
    return parts[1] if parts[0] in ("sessions", "advanced") else parts[0]


def build_sim_examples() -> tuple[int, int]:
    """シミュレータ用プリセット。手書き分と、参照実装の出力（ゲート付き）"""
    items: list[dict] = []

    for f in sorted(HANDWRITTEN.glob("*.s")):
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^#\s*@title\s+(.*)$", text, re.MULTILINE)
        desc = re.search(r"^#\s*@desc\s+(.*)$", text, re.MULTILINE)
        items.append(
            {
                "label": f.stem,
                "group": "サンプル",
                "description": title.group(1).strip() if title else f.stem,
                "note": desc.group(1).strip() if desc else "",
                "source": text,
                "gated": False,
            }
        )

    # 参照実装の出力。既に workbook/ocaml/ として配布済みのものだが、
    # ワンクリックで答えが見える導線になるので gated にする（webapps.md 5-2）
    n_ref = 0
    if KOMA16.is_file():
        for pattern in ("sessions/*/tests/*.c", "final/tests/*.c"):
            for f in sorted(WORKBOOK.glob(pattern)):
                extra = []
                files_list = f.with_suffix(".files")
                if files_list.exists():
                    extra = [
                        str(f.parent / n)
                        for n in files_list.read_text().split()
                        if n.strip()
                    ]
                try:
                    # #include "lib.h" は cwd 相対で探すので workbook から実行する
                    asm = subprocess.run(
                        [str(KOMA16), str(f), *extra],
                        cwd=WORKBOOK, capture_output=True, text=True, timeout=20,
                    )
                except subprocess.TimeoutExpired:
                    continue
                if asm.returncode != 0 or not asm.stdout.strip():
                    continue
                rel = f.relative_to(WORKBOOK)
                items.append(
                    {
                        "label": str(rel),
                        "group": "参照実装の出力（解答例）",
                        "description": f"{rel.parts[1] if rel.parts[0] == 'sessions' else 'final'} / {f.name}",
                        "note": "",
                        "source": f"# {rel} を参照実装（OCaml 版 koma16）でコンパイルした結果\n{asm.stdout}",
                        "gated": True,
                    }
                )
                n_ref += 1

    SIM_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIM_OUT.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(items) - n_ref, n_ref


def main() -> None:
    groups: dict[str, list[dict]] = {}
    n_skip = 0
    for pattern in GLOBS:
        for f in sorted(WORKBOOK.glob(pattern)):
            rel = f.relative_to(WORKBOOK)
            if not accepts(f):
                n_skip += 1
                continue
            groups.setdefault(group_label(rel), []).append(
                {
                    "label": f.name,
                    "path": str(rel),
                    "source": f.read_text(encoding="utf-8"),
                }
            )
    data = [{"group": g, "items": items} for g, items in groups.items()]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(g["items"]) for g in data)
    print(f"{OUT.relative_to(DEV)}: {len(data)} グループ {total} ファイル（除外 {n_skip}）")

    n_hand, n_ref = build_sim_examples()
    note = "" if KOMA16.is_file() else "（参照実装が未ビルド: cd workbook/ocaml && dune build）"
    print(f"{SIM_OUT.relative_to(DEV)}: 手書き {n_hand} / 参照実装 {n_ref}{note}")


if __name__ == "__main__":
    main()
