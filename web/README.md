# 補助ウェブアプリ

教材のウェブ公開に併設する学習支援アプリ。設計方針とアプリ案の全体像は
[`../design/webapps.md`](../design/webapps.md) を参照。

学習者の自習を主目的とする、共通の作業画面（`app.html`）です。
Cソースを残したまま、観察する表示を切り替えます。

| 表示 | URL | 内容 |
|------|-----|------|
| 構造を見る | `app.html?view=ast` | 構文木 / S式 / トークン。ノードとCの範囲、生成した命令の対応を確認する |
| 命令を読む | `app.html?view=asm` | 共通のコンパイル結果を広く表示する |
| 実行を追う | `app.html?view=run` | 同じ命令を実行し、レジスタ・スタック・標準出力・教育的警告を確認する |

ASTは入力に合わせて更新します。［コンパイル］は命令生成と実行準備をまとめて行い、
構造・命令・実行の観察欄の直上から操作できます。
命令は［すすむ］・［実行］で進めます。Cから生成した命令を実行中にCを編集すると、
観察結果を残して停止し、再コンパイルまで実行を進められません。
［アセンブリを読み込む］から自分のコンパイラの出力を貼付け・ファイル・サンプルで読み込めます。
読み込んだ命令はCとは別の入力として扱い、Cとの対応を表示しません。

構造の表示形式は［AST 木］・［トークン］・［S 式］で切り替えます。
その下の［対応する命令を表示］を選ぶと、生成した命令を追加表示できます。
ASTノードを選び、その式・文が生成した命令を見比べられます。

`index.html` はこの学習ツールへの入口です。教材のCは `?c=<パス>`、アセンブリの
サンプルは `?asm=<ラベル>` で指定できます。URLはサンプルと表示の指定であり、編集内容や
実行途中の状態を保存するものではありません。既存の `?mode=build|run&example=...` も受け付けます。

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
    ├── index.html / app.html
    ├── src/app-*.ts # 統合ページ（app-main / ast-view / run-view）
    ├── src/sim/     # シミュレータ（assembler / machine / libc / checks）
    ├── src/shell.ts # 共通ヘッダ（資料へのリンク・文字サイズ）
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
| シミュレータ | workbook のテストを qemu の実測値と照合。ストリームI/Oと補助ソースの除外理由を表示 | `make sim-test` |
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

- 命令（`add addi and beqz call div j la lb ld li lw mul neg not or rem ret
  sb sd seqz sll slli slt snez sra srai sub sw xor xori`）と `mv` `bnez`
- ディレクティブ（`.text .globl .data .bss .byte .word .dword .zero .balign`）。
  `.balign`はデータのラベル番地を揃える。`slli` / `srai`でcharへの縮小・符号拡張も実行できる
- libc シム: `printf`（`%d %u %x %c %s %%`）/ `malloc` / `exit` / `strlen` / `strcmp` / `strchr`。
  **プログラム側が同名の関数を定義していればそちらが優先される**ので、
  発展課題 R2_printf・R3_malloc の自前実装もそのまま動く
- `main` から開始するときは `argc=1`、`argv[0]="program"`、`argv[1]=NULL` を用意する。
  引数配列と文字列は書き換え可能な領域に置く。QEMU照合では同じ実行ファイル名を `argv[0]` に指定する
- `ecall` は `a7=64`（write）と `a7=93`（exit）のみ。発展課題 R1_nolibc 用

未対応の記法は黙って無視せず、行番号を添えて拒否する。
ストリームI/O（`fdopen` / `fprintf` / `fopen` / `fread` / `fclose`）は未対応である。
`make sim-test` はこれらの外部呼び出しを使う入力と、エントリポイントのない補助ソースを
理由つきで除外する。プログラム側で同名の関数を定義した場合は照合する。
コンパイル・リンク・実行時の失敗と不一致は検査失敗として扱う。

## wasm への移行（未了）

採用案は wasm_of_ocaml（`design/webapps.md` 3.2 の案①）だが、opam の
`binaryen-bin.119` がビルドできず、現在はフォールバックの案②（js_of_ocaml のみ）で
動いている。binaryen（Arch では `pacman -S binaryen`）が使えるようになったら、
`web/core/js/dune` の `(modes js)` を `(modes js wasm)` に変えるだけで移行できる。
