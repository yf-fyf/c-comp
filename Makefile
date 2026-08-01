.PHONY: site serve check-links check-docs check-code-examples figures web web-test sim-test ocaml-test pages clean

HOST ?= 127.0.0.1
PORT ?= 8000

# 資料サイトを .site/ に生成する（依存: pandoc + PyYAML）。
# 図はコミット済みの SVG を使うので TeX は要らない。
site:
	python3 tools/build_site.py

# ローカル確認用。原稿を保存すると作り直してブラウザを再読み込みする
# 例: make serve PORT=9000
#     make serve HOST=tailscale   別端末から Tailscale 経由で見る
#     make serve HOST=0.0.0.0     全インターフェース（LAN からも見える）
serve:
	python3 tools/build_site.py --serve --host $(HOST) --port $(PORT)

check-links:
	python3 tools/build_site.py --check-links

# 原稿・配布物の整合を機械的に検査する（テスト表の実体・旧仕様語・nav.yaml 掲載漏れ・
# code_example.md のコード・規約文書が挙げる識別子の実在）。
# 除外リストは tools/doc_check_allowlist.yaml（理由つき）。
check-docs:
	python3 tools/check_docs.py

# code_example.md の C コードを実際に処理系へ通し、期待する終了コード・標準出力まで
# 照合する（check-docs の codeexec を実行形態で走らせる）。
# 依存: dune + menhir（参考実装のビルド）、riscv64-linux-gnu-gcc、qemu-riscv64。
check-code-examples:
	cd workbook/ocaml && dune build
	python3 tools/check_docs.py --only codeexec

# 図を SVG で生成する（依存: lualatex + poppler-utils + Graphviz）。
# 生成物はコミット対象なので、図を触るときだけ実行する。
figures:
	python3 tools/build_figures.py

# 補助ウェブアプリ（web/README.md 参照。依存: opam の js_of_ocaml 系 + node）
web:
	cd workbook/ocaml && dune build          # プリセット生成に参照実装を使う
	python3 tools/build_web_examples.py
	cd web/core && dune build --profile release
	cd web/app && npm ci && npm run build

# GitHub Pages 用の許可リスト済み静的公開物を .pages/ に生成する。
# 例: make pages VERSION=v0.1.0
pages: web
ifndef VERSION
	@echo "使い方: make pages VERSION=v0.1.0"
	@exit 1
else
	python3 tools/build_pages.py $(VERSION)
endif

web-test:
	cd web/core && dune build && python3 golden_test.py
	cd web/app && npm run test

# シミュレータを qemu と突き合わせる（依存: riscv64-linux-gnu-gcc + qemu-riscv64）
sim-test:
	cd workbook/ocaml && dune build
	cd web/app && npm run test:qemu

# OCaml 参考実装の回帰テスト（依存: riscv64-linux-gnu-gcc + qemu-riscv64）
ocaml-test:
	cd workbook/ocaml && dune build && python3 run_tests.py -q

# 生成物のうちコミットしないものだけ消す。
# 図の SVG はコミット対象なので触らない（作り直すなら make figures）。
clean:
	rm -rf .site .pages
