#!/usr/bin/env python3
"""
講義資料の静的サイトを pandoc で生成する。

使い方:
    python3 tools/build_site.py                  # 全ページを .site/ へ
    python3 tools/build_site.py --output DIR     # 出力先を変える
    python3 tools/build_site.py --only 03_arith  # ID の前方一致で絞る(見た目の確認用)
    python3 tools/build_site.py --check-links    # 生成済みサイトの内部リンクを検査
    python3 tools/build_site.py --serve          # 配信 + 変更監視 + 自動リロード
    python3 tools/build_site.py --serve --host tailscale   # 別端末から Tailscale 経由で見る

構成は site/nav.yaml が単一の出典。ページのタイトルは原稿の先頭 H1 から取る。
出力は <section>/<stem>/index.html。stem が README のものは <section>/index.html。

ページ間のリンクは <section>/<stem>/ のディレクトリ形式なので、file:// では辿れない。
ローカルで見るときは --serve を使う。

依存: pandoc、PyYAML。図は tools/build_figures.py が生成した SVG を使う。
"""

from __future__ import annotations

import argparse
import html
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
NAV = SITE / "nav.yaml"
TEMPLATE = SITE / "template.html"
FILTER = SITE / "boxes.lua"
STYLE = SITE / "style.css"
SCRIPT = SITE / "lightbox.js"
FIGURES = ROOT / "materials" / "figures"

PANDOC = "pandoc"
MARKDOWN = ("markdown+pipe_tables+fenced_code_blocks+backtick_code_blocks"
            "+fenced_divs+implicit_figures")


class Page:
    """サイトの1ページ。source が None のものは build_site.py が本文を作る。"""

    def __init__(self, section: dict, slug: str, source: Path | None = None,
                 title: str | None = None):
        self.source = source
        self.section_slug = section["slug"]
        self.section_title = section["title"]
        self.slug = slug
        # README はセクションの入口
        self.is_index = slug == "index"
        self.out_dir = (Path(self.section_slug) if self.is_index
                        else Path(self.section_slug) / slug)
        self.url = self.out_dir.as_posix() + "/"
        self.depth = len(self.out_dir.parts)
        self.title = title or (read_title(source) if source else None) or slug

    @property
    def base(self) -> str:
        return "../" * self.depth


def strip_frontmatter(lines: list[str]) -> list[str]:
    """先頭の YAML frontmatter(introduces / requires の台帳)を落とす"""
    if not lines or lines[0].strip() != "---":
        return lines
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return lines[i + 1:]
    return lines


def read_title(path: Path) -> str | None:
    """原稿の先頭 H1 をタイトルとして読む(Markdown 記法は落とす)"""
    for line in strip_frontmatter(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if line.startswith("# "):
            return re.sub(r"[`*_]", "", line[2:]).strip()
        if line and not line.startswith(("<!--", "---", ":::")):
            # 本文が始まったら H1 は無い
            break
    return None


def load_nav() -> dict:
    with NAV.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_pages(nav: dict) -> list[Page]:
    pages: list[Page] = []
    for section in nav["sections"]:
        members: list[Page] = []
        for entry in section["pages"]:
            source = ROOT / entry
            if not source.is_file():
                raise SystemExit(f"nav.yaml: 原稿がない: {entry}")
            stem = source.stem
            members.append(Page(section, "index" if stem == "README" else stem, source))
        # README を持たないセクションには入口ページを用意する。
        # topnav とパンくずが <section>/ を指すので、無いとリンク切れになる。
        if not any(p.is_index for p in members):
            members.insert(0, Page(section, "index", title=section["title"]))
        pages.extend(members)
    return pages


def link_map(pages: list[Page]) -> dict[str, str]:
    """原稿のリポジトリ相対パス -> サイトのルート相対 URL"""
    return {p.source.relative_to(ROOT).as_posix(): p.url
            for p in pages if p.source is not None}


def topnav_html(nav: dict, base: str, current_slug: str | None = None) -> str:
    """常設のナビはこれだけ。セクション内の移動は前後ナビと入口ページが担う。

    並びと群分けは nav.yaml が出典。group が変わる位置に区切り線を挟み、
    「教材｜引くもの｜道具」の3群に見せる。
    """
    parts: list[str] = []
    prev_group: str | None = None

    def add(item: str, group: str | None) -> None:
        nonlocal prev_group
        if parts and group != prev_group:
            parts.append('<span class="sep" aria-hidden="true"></span>')
        prev_group = group
        parts.append(item)

    for section in nav["sections"]:
        mark = ' aria-current="page"' if section["slug"] == current_slug else ""
        add(f'<a href="{base}{section["slug"]}/"{mark}>'
            f'{html.escape(section["title"])}</a>', section.get("group"))
    for link in nav.get("external_links", []):
        add(f'<a href="{base}{link["url"]}">{html.escape(link["title"])}</a>',
            link.get("group"))
    return "".join(parts)


def breadcrumb_html(nav: dict, page: Page) -> str:
    base = page.base
    crumbs = [f'<a href="{base}">ホーム</a>']
    if not page.is_index:
        crumbs.append(
            f'<a href="{base}{page.section_slug}/">{html.escape(page.section_title)}</a>'
        )
    else:
        crumbs.append(html.escape(page.section_title))
    return " / ".join(crumbs)


def pager_html(pages: list[Page], page: Page) -> str:
    """前後ナビ。サイドバーが無いので、セクション一覧へ戻る道もここに置く。

    前後は同一セクション内に閉じる。docs は「引くもの」で読む順序が無く、
    セクションを跨ぐ「次へ」は読書順の誤示唆になるため。
    """
    members = [p for p in pages if p.section_slug == page.section_slug]
    index = members.index(page)
    parts = []
    if index > 0:
        prev = members[index - 1]
        parts.append(
            f'<a class="prev" href="{page.base}{prev.url}">'
            f'<span class="label">前へ</span>{html.escape(prev.title)}</a>'
        )
    if not page.is_index:
        parts.append(
            f'<a class="index" href="{page.base}{page.section_slug}/">'
            f'<span class="label">一覧</span>{html.escape(page.section_title)}</a>'
        )
    if index < len(members) - 1:
        nxt = members[index + 1]
        parts.append(
            f'<a class="next" href="{page.base}{nxt.url}">'
            f'<span class="label">次へ</span>{html.escape(nxt.title)}</a>'
        )
    return "".join(parts)


def run_pandoc(source: Path, destination: Path, *, variables: dict[str, str],
               metadata: dict, extra: list[str] | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as meta_file:
        json.dump(metadata, meta_file, ensure_ascii=False)
        meta_path = Path(meta_file.name)
    try:
        cmd = [
            PANDOC, str(source),
            "--from", MARKDOWN,
            "--to", "html5",
            "--standalone",
            f"--template={TEMPLATE}",
            f"--lua-filter={FILTER}",
            f"--metadata-file={meta_path}",
            "--toc", "--toc-depth=2",
            "--mathml",
            "--highlight-style=tango",
            "--wrap=preserve",
            "-o", str(destination),
        ]
        for key, value in variables.items():
            cmd += ["--variable", f"{key}={value}"]
        cmd += extra or []

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SystemExit(f"[FAIL] {source}\n{result.stderr.strip()}")
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines():
                print(f"  [warn] {source.name}: {line}")
    finally:
        meta_path.unlink(missing_ok=True)


def card_list(pages: list[Page], section_slug: str, base: str) -> list[str]:
    """セクションに属するページへのカード一覧"""
    lines = ['<ul class="cards">']
    for page in pages:
        if page.section_slug != section_slug or page.is_index:
            continue
        lines.append(
            f'<li><a href="{base}{page.url}">'
            f'<span class="card-title">{html.escape(page.title)}</span></a></li>'
        )
    lines.append("</ul>")
    return lines


def section_index_markdown(nav: dict, page: Page) -> str:
    """README を持たないセクションの入口。ページ一覧はテンプレート側が足す。"""
    section = next(s for s in nav["sections"] if s["slug"] == page.section_slug)
    lines = [f'# {section["title"]}', ""]
    if section.get("summary"):
        lines += [section["summary"], ""]
    return "\n".join(lines) + "\n"


def needs_child_list(page: Page, members: list[Page]) -> bool:
    """セクション入口から子ページへ辿れるか。

    README をそのまま入口にしているセクションでは、README が一覧を持っているとは
    限らない（発展課題の一覧表はディレクトリ名をコードスパンで書いていてリンクではない）。
    全部リンクしているセクションだけ、重複を避けて一覧を足さない。
    """
    if page.source is None:
        return True
    text = page.source.read_text(encoding="utf-8")
    return any(
        member.source is not None and member.source.name not in text
        for member in members
        if not member.is_index
    )


def render_page(nav: dict, pages: list[Page], page: Page, output: Path,
                links: dict[str, str], release: str = "") -> None:
    destination = output / page.out_dir / "index.html"
    blob = f'{nav["repo_url"]}/blob/{nav["repo_branch"]}/'
    variables = {
        "base": page.base,
        "site-title": nav["title"],
        "repo-url": nav["repo_url"],
        "topnav": topnav_html(nav, page.base, page.section_slug),
        "breadcrumb": breadcrumb_html(nav, page),
        "pager": pager_html(pages, page),
        "source-url": "",
        "release": release,
        "childlist": "",
    }
    if page.is_index:
        members = [p for p in pages if p.section_slug == page.section_slug]
        if needs_child_list(page, members):
            variables["childlist"] = (
                '<h2>このセクションのページ</h2>'
                + "".join(card_list(pages, page.section_slug, page.base))
            )
    metadata = {
        "figbase": page.base + "figures",
        "blobbase": blob,
        "srcdir": "",
        "linkmap": {k: page.base + v for k, v in links.items()},
    }

    if page.source is not None:
        variables["source-url"] = blob + page.source.relative_to(ROOT).as_posix()
        metadata["srcdir"] = page.source.parent.relative_to(ROOT).as_posix()
        run_pandoc(page.source, destination, variables=variables, metadata=metadata)
    else:
        # 生成したセクション入口。目次だけなので本文の目次は出さない
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "index.md"
            source.write_text(section_index_markdown(nav, page), encoding="utf-8")
            run_pandoc(source, destination, variables=variables, metadata=metadata,
                       extra=["--variable", "toc="])

    print(f"[ OK ] {page.out_dir.as_posix()}/  ({page.title})")


def download_markdown(release: str | None) -> list[str]:
    """公開物を組み立てるときだけ ZIP へのリンクを出す"""
    lines = ["## 演習環境", ""]
    if release:
        archive = f"downloads/c-comp-workbook-{release}.zip"
        lines += [
            "starter・テスト・Docker 環境・参考実装は ZIP で配布しています。",
            "資料はこのサイトを見てください。",
            "",
            '<ul class="cards">',
            f'<li><a href="{archive}"><span class="card-title">演習環境をダウンロード</span>'
            f'<span class="card-desc">{html.escape(release)} / workbook 一式</span></a></li>',
            "</ul>",
            "",
        ]
    else:
        lines += [
            "starter・テスト・Docker 環境・参考実装は、公開サイトから ZIP で配布しています。",
            "",
        ]
    return lines


def archive_markdown(release: str | None) -> list[str]:
    """公開物を組み立てるときだけ、旧版アーカイブへの時限的な導線を出す。

    ローカル `make site`/`make serve` の出力には `archive/` が存在しないため、
    release 未指定時は何も出さない（内部リンク切れを避ける）。
    今学期の履修者の移行が済んだら、この関数と呼び出し元の1行を削除する。
    """
    if not release:
        return []
    return [
        "::: note",
        "旧版(2026-07-29 公開)の資料が必要な場合は"
        "[旧版アーカイブ](archive/v0.1.0/)を参照してください。"
        "言語仕様は現行版と異なります。この導線は移行期間限定で、今後削除されます。",
        ":::",
        "",
    ]


def home_markdown(nav: dict, pages: list[Page], release: str | None = None) -> str:
    lines = [f'# {nav["title"]}', "", nav["description"], ""]
    lines += [
        "この演習は、C 言語サブセットのコンパイラを**動く状態を保ちながら**段階的に作り上げます。",
        "前半は Python でコンパイラの論理だけに集中し、後半は動く Python 版を参照実装として",
        "C へ移植します。生成したアセンブリは毎回 qemu で実行して確かめます。",
        "",
        "::: important",
        "はじめての方は [進め方ガイド](docs/getting_started/) から読んでください。",
        "環境の用意・全コマの一覧・到達目標をまとめてあります。",
        ":::",
        "",
    ]
    lines += download_markdown(release)
    lines += archive_markdown(release)
    # 主動線の通常回だけカードを直載せする。他セクションは入口への誘導に留め、
    # 一覧は各セクション入口ページに一本化する（トップを全目録にしない）。
    for section in nav["sections"]:
        members = [p for p in pages if p.section_slug == section["slug"]]
        if not members:
            continue
        lines += [f'## {section["title"]}', ""]
        if section.get("summary"):
            lines += [section["summary"], ""]
        if section["slug"] == "sessions":
            lines += card_list(pages, section["slug"], "")
        else:
            lines += [f'[一覧を見る →]({section["slug"]}/)', ""]
        lines.append("")
    lines += [
        "## 補助ツール",
        "",
        "ブラウザで動く学習支援アプリです。環境構築の前でも触れます。",
        "",
        '<ul class="cards">',
        '<li><a href="tools/app.html?mode=build"><span class="card-title">作る</span>'
        '<span class="card-desc">C ソースから構文木・S 式・トークン列と RV64 アセンブリを表示する</span></a></li>',
        '<li><a href="tools/app.html?mode=run"><span class="card-title">動かす</span>'
        '<span class="card-desc">アセンブリを1命令ずつ実行してレジスタとスタックを見る</span></a></li>',
        "</ul>",
        "",
    ]
    return "\n".join(lines)


def render_home(nav: dict, pages: list[Page], output: Path,
                release: str = "", version: str | None = None) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "index.md"
        source.write_text(home_markdown(nav, pages, version), encoding="utf-8")
        run_pandoc(
            source, output / "index.html",
            variables={
                "base": "",
                "site-title": nav["title"],
                # 所属科目は見出しの枠内にだけ出す。render_page へは渡さないので
                # 上部バー・<title>・フッタ・各コマのページには出ない。
                "site-subtitle": nav.get("subtitle", ""),
                "repo-url": nav["repo_url"],
                "topnav": topnav_html(nav, ""),
                "breadcrumb": "",
                "pager": "",
                "source-url": "",
                "release": release,
            },
            metadata={"description": nav["description"]},
            extra=["--variable", "toc="],
        )
    print("[ OK ] index.html")


# assets/ へそのまま置く静的ファイル。template.html がこの名前で読み込む
STATIC_ASSETS = (STYLE, SCRIPT)


def copy_static(output: Path) -> None:
    (output / "assets").mkdir(parents=True, exist_ok=True)
    for source in STATIC_ASSETS:
        shutil.copy2(source, output / "assets" / source.name)


def copy_figures(output: Path) -> None:
    destination = output / "figures"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(FIGURES, destination,
                    ignore=shutil.ignore_patterns("*.tex", "*.pdf"))


def copy_legal(output: Path) -> None:
    """フッタが参照する LICENSE / LICENSE-MATERIALS / THIRD_PARTY_NOTICES.md を出力先に置く。

    tools/build_pages.py（リリース組み立て）でも同じファイルをコピーしているが、
    build_site.py 単体のプレビュー（make serve 等）でもフッタのリンクが
    404 にならないよう、ここでも出力先に置く。
    """
    for name in ("LICENSE", "LICENSE-MATERIALS", "THIRD_PARTY_NOTICES.md"):
        source = ROOT / name
        if source.is_file():
            shutil.copy2(source, output / name)


def copy_assets(output: Path) -> None:
    copy_static(output)
    copy_figures(output)
    copy_legal(output)


# ── ローカル確認用の開発サーバ ──

WEB_DIST = ROOT / "web" / "app" / "dist"
POLL_INTERVAL = 0.7
RELOAD_SNIPPET = (b'<script>new EventSource("/__reload")'
                  b'.onmessage=function(){location.reload()}</script>')


def link_tools(output: Path) -> None:
    """補助ウェブアプリのビルド結果を .site/tools として見せる"""
    destination = output / "tools"
    if destination.is_symlink():
        destination.unlink()
    elif destination.exists():
        shutil.rmtree(destination)
    if not WEB_DIST.is_dir():
        print("[note] web/app/dist が無いので /tools/ は出ない（make web で作れる）")
        return
    destination.symlink_to(WEB_DIST)


class Reloader:
    """再ビルドの世代番号。SSE の待ち受けを起こすのに使う。"""

    def __init__(self) -> None:
        self.generation = 0
        self._condition = threading.Condition()

    def bump(self) -> None:
        with self._condition:
            self.generation += 1
            self._condition.notify_all()

    def wait(self, seen: int, timeout: float) -> int:
        with self._condition:
            if self.generation == seen:
                self._condition.wait(timeout)
            return self.generation


def make_handler(output: Path, reloader: Reloader, inject: bool):
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(output), **kwargs)

        def log_message(self, *args) -> None:
            pass  # 静かにする。再ビルドのログだけ見えていればよい

        def end_headers(self) -> None:
            # 付けないと再ビルドしてもブラウザが古い HTML を出す
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self) -> None:
            if self.path.split("?")[0] == "/__reload":
                self._stream_reload()
                return
            target = Path(self.translate_path(self.path))
            if target.is_dir():
                if not self.path.split("?")[0].endswith("/"):
                    super().do_GET()  # 末尾スラッシュへリダイレクトさせる
                    return
                target = target / "index.html"
            if inject and target.suffix == ".html" and target.is_file():
                self._send_html(target)
                return
            super().do_GET()

        def _send_html(self, path: Path) -> None:
            body = path.read_bytes()
            marker = b"</body>"
            if marker in body:
                body = body.replace(marker, RELOAD_SNIPPET + marker, 1)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _stream_reload(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            seen = reloader.generation
            try:
                while True:
                    current = reloader.wait(seen, 15.0)
                    if current != seen:
                        seen = current
                        self.wfile.write(b"data: reload\n\n")
                    else:
                        self.wfile.write(b": ping\n\n")  # 接続を保つ
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ValueError):
                pass  # ブラウザが閉じただけ

    return Handler


def source_snapshot(pages: list[Page]) -> dict[Path, float]:
    watched = [TEMPLATE, FILTER, STYLE, SCRIPT, NAV]
    watched += [p.source for p in pages if p.source is not None]
    snapshot = {}
    for path in watched:
        try:
            snapshot[path] = path.stat().st_mtime
        except OSError:
            pass
    return snapshot


def figures_mtime() -> float:
    return max((p.stat().st_mtime for p in FIGURES.rglob("*.svg")), default=0.0)


def rebuild_all(output: Path, state: dict) -> None:
    state["nav"] = load_nav()
    state["pages"] = build_pages(state["nav"])
    state["links"] = link_map(state["pages"])
    copy_static(output)
    for page in state["pages"]:
        render_page(state["nav"], state["pages"], page, output, state["links"])
    render_home(state["nav"], state["pages"], output)
    state["snapshot"] = source_snapshot(state["pages"])


def rebuild_changed(output: Path, state: dict) -> bool:
    """変わったものだけ作り直す。全ページ作り直すと 55 本分待たされる。"""
    changed = False

    figures = figures_mtime()
    if figures > state["figures"]:
        state["figures"] = figures
        copy_figures(output)
        print("[更新] 図")
        changed = True

    current = source_snapshot(state["pages"])
    previous = state["snapshot"]
    dirty = [p for p, mtime in current.items() if previous.get(p) != mtime]
    vanished = [p for p in previous if p not in current]
    state["snapshot"] = current
    if not dirty and not vanished:
        return changed

    # 静的資産だけが変わったならコピーし直すだけでよい（ページの再生成は要らない）
    if set(dirty) <= set(STATIC_ASSETS) and not vanished:
        copy_static(output)
        print("[更新] " + "・".join(p.name for p in dirty))
        return True

    # 構成やテンプレートが変わると全ページに響く
    if vanished or {TEMPLATE, FILTER, NAV} & set(dirty):
        rebuild_all(output, state)
        print("[更新] 全ページ")
        return True

    if set(dirty) & set(STATIC_ASSETS):
        copy_static(output)
        print("[更新] " + "・".join(p.name for p in dirty if p in STATIC_ASSETS))
        changed = True

    for source in dirty:
        page = next((p for p in state["pages"] if p.source == source), None)
        if page is None:
            continue
        # H1 が変わると前後ナビ・セクション入口・トップページの見出しに響く
        if (read_title(source) or page.slug) != page.title:
            rebuild_all(output, state)
            print("[更新] 全ページ（タイトルが変わったため）")
            return True
        render_page(state["nav"], state["pages"], page, output, state["links"])
        changed = True

    return changed


def tailscale_address() -> str | None:
    """tailscale0 の IPv4 を実行時に引く。環境固有の値は持ち歩かない。"""
    if shutil.which("tailscale") is None:
        return None
    try:
        result = subprocess.run(["tailscale", "ip", "-4"],
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return lines[0] if lines else None


def resolve_host(host: str) -> str:
    """`tailscale` という論理名だけ実アドレスへ置き換える"""
    if host != "tailscale":
        return host
    address = tailscale_address()
    if address is None:
        raise SystemExit(
            "tailscale のアドレスが引けない。"
            "tailscale が動いているか確かめるか、--host にアドレスを直接渡す"
        )
    return address


def announce(host: str, port: int) -> None:
    """到達できる URL を出す。端末に出すだけで、どこにも保存しない。"""
    if host in ("0.0.0.0", "::"):
        print(f"\n配信中: ポート {port}（全インターフェース）")
        print(f"  ローカル  : http://127.0.0.1:{port}/")
        address = tailscale_address()
        if address:
            print(f"  Tailscale : http://{address}:{port}/")
        print("  注意: LAN や docker のインターフェースからも見えます。"
              "Tailscale だけに絞るなら --host tailscale を使ってください。")
    else:
        shown = f"[{host}]" if ":" in host else host
        print(f"\n配信中: http://{shown}:{port}/")


def serve(nav: dict, pages: list[Page], links: dict[str, str], output: Path,
          host: str, port: int, watch: bool) -> int:
    link_tools(output)
    reloader = Reloader()
    state = {
        "nav": nav, "pages": pages, "links": links,
        "snapshot": source_snapshot(pages), "figures": figures_mtime(),
    }

    class DevServer(http.server.ThreadingHTTPServer):
        daemon_threads = True
        # --host :: のような IPv6 指定を通す
        address_family = socket.AF_INET6 if ":" in host else socket.AF_INET

    server = DevServer((host, port), make_handler(output, reloader, inject=watch))
    threading.Thread(target=server.serve_forever, daemon=True).start()

    announce(host, port)
    if watch:
        print("原稿を保存すると作り直してブラウザを再読み込みします。Ctrl-C で終了。")
    else:
        print("Ctrl-C で終了。")

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            if not watch:
                continue
            try:
                if rebuild_changed(output, state):
                    reloader.bump()
            except SystemExit as error:
                print(f"[FAIL] {error}")  # 監視は止めない
    except KeyboardInterrupt:
        print("\n終了します")
    finally:
        server.shutdown()
    return 0


HREF_RE = re.compile(r'(?:href|src)="([^"#][^"]*)"')

# tools/build_pages.py が公開時に足すもの。"tools"・"downloads" は単体のサイトビルドには
# 存在しない。"LICENSE"・"LICENSE-MATERIALS"・"THIRD_PARTY_NOTICES.md" は copy_legal() が
# 単体ビルドでも出力先へ置くが、check_links() 側の除外はどちらのビルド経路でも安全なので
# 変更していない。
ASSEMBLED = {"tools", "downloads", "LICENSE", "LICENSE-MATERIALS", "THIRD_PARTY_NOTICES.md"}


def check_links(output: Path) -> int:
    """生成された HTML の内部リンクが実在するか調べる"""
    broken: list[str] = []
    root = output.resolve()
    for page in sorted(root.rglob("*.html")):
        for target in HREF_RE.findall(page.read_text(encoding="utf-8")):
            if re.match(r"^(?:[a-z]+:|//|#)", target):
                continue
            # resolve() はシンボリックリンクを辿るので使わない。
            # make serve が張る .site/tools は web/app/dist を指しており、
            # 辿るとサイト外に出て ASSEMBLED の除外が効かなくなる。
            resolved = Path(os.path.normpath(page.parent / target.split("#")[0]))
            try:
                relative = resolved.relative_to(root)
            except ValueError:
                broken.append(f"{page.relative_to(root)} -> {target} (サイト外)")
                continue
            if relative.parts and relative.parts[0] in ASSEMBLED:
                continue
            if resolved.is_dir():
                resolved = resolved / "index.html"
            if not resolved.exists():
                broken.append(f"{page.relative_to(root)} -> {target}")
    if broken:
        print(f"\n内部リンク切れ {len(broken)} 件:")
        for item in broken:
            print(f"  {item}")
        return 1
    print("\n内部リンク切れなし")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".site")
    parser.add_argument("--only", help="ページ ID の前方一致で絞る")
    parser.add_argument("--release", help="公開物として組み立てるときの版（例 v0.1.0）。"
                                          "ZIP へのリンクと版表記を出す")
    parser.add_argument("--revision", help="--release と一緒に脚注へ出すリビジョン")
    parser.add_argument("--check-links", action="store_true",
                        help="生成せず、既存の出力の内部リンクだけ調べる")
    parser.add_argument("--serve", action="store_true",
                        help="ビルドしたあと配信する（ローカル確認用）")
    parser.add_argument("--host", default="127.0.0.1",
                        help="--serve の待ち受けアドレス。"
                             "0.0.0.0 で全インターフェース、"
                             "tailscale で tailscale0 のアドレスだけ（既定: 127.0.0.1）")
    parser.add_argument("--port", type=int, default=8000, help="--serve の待ち受けポート")
    parser.add_argument("--no-watch", action="store_true",
                        help="--serve のとき変更監視と自動リロードをしない")
    args = parser.parse_args()

    if args.serve and args.only:
        print("--serve は全ページを対象にする（--only とは併用しない）", file=sys.stderr)
        return 2

    if args.check_links:
        if not args.output.is_dir():
            print(f"出力がない: {args.output}", file=sys.stderr)
            return 2
        return check_links(args.output)

    if shutil.which(PANDOC) is None:
        print("pandoc が見つからない", file=sys.stderr)
        return 2

    nav = load_nav()
    pages = build_pages(nav)
    links = link_map(pages)

    targets = pages
    if args.only:
        targets = [p for p in pages if p.slug.startswith(args.only)]
        if not targets:
            print(f"該当ページがない: {args.only}", file=sys.stderr)
            return 2

    release = ""
    if args.release:
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
        parts = [f"Release {args.release}"]
        if args.revision:
            parts.append(f"source {args.revision}")
        parts.append(stamp)
        release = html.escape(" / ".join(parts))

    args.output.mkdir(parents=True, exist_ok=True)
    copy_assets(args.output)
    for page in targets:
        render_page(nav, pages, page, args.output, links, release)
    if not args.only:
        render_home(nav, pages, args.output, release, args.release)

    print(f"\n[DONE] {len(targets)} ページ -> {args.output}")

    if args.serve:
        return serve(nav, pages, links, args.output,
                     resolve_host(args.host), args.port, not args.no_watch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
