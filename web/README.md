# 補助ウェブアプリ

教材のウェブ公開に併設する学習支援アプリ。設計方針とアプリ案の全体像は
[`../design/webapps.md`](../design/webapps.md) を参照。

| アプリ | ページ | 内容 |
|--------|--------|------|
| A1 AST ビジュアライザ | `ast.html` | C ソース → 構文木 / S 式 / トークン。ノードから対応するソース範囲を強調。資料の図と同じ木 |
| A2 RV64 シミュレータ | `sim.html` | アセンブリを1命令ずつ実行。レジスタ・スタック・標準出力・教育的警告 |

## 構成

```
web/
├── core/            # OCaml 言語処理コア（workbook/ocaml/support を流用）
│   ├── lib/         # ライブラリ本体
│   │   ├── support@     # -> ../../workbook/ocaml/support（シンボリックリンク。コピーしない）
│   │   └── astdump.ml   # S 式 / DOT / JSON / トークン列 / 行対応表
│   ├── cli/         # 黄金テスト用ネイティブ CLI（astdump_cli）
│   ├── js/          # ブラウザ向け API（js_of_ocaml。globalThis.myccCore を公開）
│   └── golden_test.py   # parse_viewer.py とのバイト一致検査
├── examples/asm/    # シミュレータの手書きサンプル（README.md に置く理由あり）
└── app/             # TypeScript + Vite フロントエンド
    ├── index.html / ast.html / sim.html
    ├── src/sim/     # シミュレータ（assembler / machine / libc / checks）
    ├── src/shell.ts # 共通ヘッダ（アプリ間ナビ・文字サイズ）
    ├── test/        # vitest と qemu 照合スクリプト
    └── public/      # 生成物置き場（core/api.bc.js と *-examples.json。コミットしない）
```

言語処理は OCaml、表示とターゲット環境の模倣は TypeScript という分担にしている
（`design/webapps.md` 3.1）。シミュレータが TypeScript 側にあるのはこの規則による。

AST ノードの位置は Menhir で構文要素全体の範囲を記録し、前処理器の区間マップを通して
CodeMirror の UTF-16 offset へ変換する。通常コードは文字単位で対応するが、マクロ展開結果と
include 先由来のノードは元エディタ上に同一の文字範囲がないためハイライトしない。
JSON / DOT の直列化と `astDot` API は内部処理・黄金テスト用に維持し、画面のタブには出さない。

## 正しさの担保

| 対象 | 方法 | コマンド |
|------|------|----------|
| AST 表示 | Python 版 `scaffold/parse_viewer.py` とバイト一致（全テスト × sexp/dot × 行番号有無） | `make web-test` |
| シミュレータ | qemu の実測値と終了コード・標準出力を突き合わせ（workbook 全テスト） | `make sim-test` |
| 手書きサンプル | 期待する終了コード・出力・警告が出るか | `make web-test`（vitest に同梱） |

## 開発

依存: opam（`js_of_ocaml` `js_of_ocaml-compiler` `js_of_ocaml-ppx`）、node。
`make sim-test` だけ `riscv64-linux-gnu-gcc` と `qemu-riscv64` を要する。

```bash
# プリセット生成（dev/ から。参照実装のビルドが要る）
cd workbook/ocaml && dune build
python3 tools/build_web_examples.py

# コアのビルド
cd web/core && dune build

# 開発サーバ
cd web/app && npm install && npm run dev

# 一括ビルド（dev/ から。web/app/dist/ に静的サイトができる）
make web
```

## シミュレータの対応範囲

参照コンパイラが実際に出すものに合わせてある。

- 命令 29 種（`add addi and beqz call div j la lb ld li lw mul neg not or rem ret
  sb sd seqz sll slt snez sra sub sw xor xori`）と `mv` `bnez`
- ディレクティブ 8 種（`.text .globl .data .bss .byte .word .dword .zero`）
- libc シム: `printf`（`%d %u %x %c %s %%`）/ `malloc` / `exit` / `strlen` / `strcmp` / `strchr`。
  **プログラム側が同名の関数を定義していればそちらが優先される**ので、
  発展課題 R2_printf・R3_malloc の自前実装もそのまま動く
- `ecall` は `a7=64`（write）と `a7=93`（exit）のみ。発展課題 R1_nolibc 用

未対応の記法は黙って無視せず、行番号を添えて拒否する。

## wasm への移行（未了）

採用案は wasm_of_ocaml（`design/webapps.md` 3.2 の案①）だが、opam の
`binaryen-bin.119` がビルドできず、現在はフォールバックの案②（js_of_ocaml のみ）で
動いている。binaryen（Arch では `pacman -S binaryen`）が使えるようになったら、
`web/core/js/dune` の `(modes js)` を `(modes js wasm)` に変えるだけで移行できる。
