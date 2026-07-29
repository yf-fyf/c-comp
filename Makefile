.PHONY: handouts handout advanced-handouts figures tool-pdfs site serve web web-test sim-test ocaml-test pages clean

SESSION ?=
HOST ?= 127.0.0.1
PORT ?= 8000

handouts: figures
	python3 tools/build_session_pdfs.py

advanced-handouts: figures
	python3 tools/build_advanced_pdfs.py

handout: figures
ifdef SESSION
	python3 tools/build_session_pdfs.py $(SESSION)
else
	@echo "使い方: make handout SESSION=04_variables"
	@exit 1
endif

figures:
	python3 tools/build_figure_pdfs.py

tool-pdfs:
	python3 tools/build_tool_pdfs.py

# 資料サイト（依存: pandoc + PyYAML）。図は生成済みの SVG を使う
site:
	python3 tools/build_site.py

# ローカル確認用。原稿を保存すると作り直してブラウザを再読み込みする
# 例: make serve PORT=9000
#     make serve HOST=tailscale   別端末から Tailscale 経由で見る
#     make serve HOST=0.0.0.0     全インターフェース（LAN からも見える）
serve:
	python3 tools/build_site.py --serve --host $(HOST) --port $(PORT)

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

clean:
	rm -f workbook/sessions/*/handout.pdf
	rm -f workbook/advanced/*/*/handout.pdf
	rm -f workbook/guides/*.pdf
	rm -f materials/figures/*.pdf
	rm -f materials/figures/ast/*.pdf
