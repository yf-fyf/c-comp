# 実装ガイド（メンテナ用）

教材の開発・保守を行う際の規約・手順・参考情報。
学習者向けの実装規約は [`../workbook/docs/conventions.md`](../workbook/docs/conventions.md) を参照。

---

## ディレクトリ構成

```
.
├── README.md              # プロジェクト入口
├── AGENTS.md              # AI エージェント向けガイド
├── LICENSE
├── Makefile               # サイト・図・公開物のビルド
├── design/                # 設計・運用文書（教える側・改変する側向け）
│   ├── curriculum.md      # カリキュラム設計書
│   ├── maintaining.md     # このファイル
│   ├── quality_guide.md   # 教材品質管理・AIレビュー手順
│   └── webapps.md         # 補助ウェブアプリの企画書（企画段階）
├── materials/             # 資料の Markdown 原稿
│   ├── sessions/          # 実装のコマ1〜15 + 発表・振り返りのコマ16 の原稿 NN_xxx.md
│   ├── advanced/          # 発展教材の原稿 <回ID>_xxx.md
│   ├── tools/             # 補助ツールガイドの原稿
│   └── figures/           # 図の TikZ ソースと生成 SVG（sessions・advanced 共用）
│       └── ast/           # AST 図（parse_viewer + graphviz で生成）
├── site/                  # 資料サイトの構成・テンプレート・スタイル
│   ├── nav.yaml           # サイト構成の単一の出典
│   ├── template.html      # pandoc の HTML テンプレート
│   ├── boxes.lua          # ::: の変換・図と .md リンクの書き換え
│   └── style.css          # 配色は latex/figure-preamble.tex と揃える
├── latex/                 # 図の共通プリアンブル（figure-preamble.tex のみ）
├── tools/                 # サイト・図・公開物・ウェブアプリの生成スクリプト
├── web/                   # 補助ウェブアプリ（企画: design/webapps.md、構成: web/README.md）
│   ├── core/              # OCaml 言語処理コア（workbook/ocaml/support を流用）
│   ├── examples/asm/      # RV64 シミュレータの手書きサンプル
│   └── app/               # TypeScript + Vite フロントエンド
└── workbook/              # 学習者向け配布物。この中だけで演習が完結する
    ├── README.md          # 最短の導線（詳細は docs/ へ送る）
    ├── docs/              # 学習者向けドキュメント。「読むもの」と「引くもの」に分ける
    │   ├── README.md          # 索引
    │   ├── getting_started.md # 進め方・環境・全コマ一覧（読む）
    │   ├── conventions.md     # Python 実装の約束ごと（読む）
    │   ├── testing.md         # テストとデバッグ（test_runner・テスト形式・症状から原因を絞る）
    │   ├── language_spec.md   # Core プロファイル（引く）
    │   ├── rv64_reference.md  # ABI・スタックフレーム・命令（引く）
    │   └── code_example.md    # 到達目標コード例（コマ1〜15、引く）
    ├── scaffold/          # 提供スキャフォールド（Lexer/Parser/AST/テストランナー）
    ├── sessions/          # 通常回 NN_xxx/（starter・テスト。資料はサイト）
    ├── final/             # コマ15で作る最終統合版
    ├── ocaml/             # OCaml 版参考実装（コマ1〜15、完成相当）
    ├── advanced/          # 発展教材。1トピック=1ディレクトリのフラット構成
    │   ├── README.md      # 全トピック一覧・カテゴリ別の解説
    │   ├── optcc.py       # O 系列の共有ラッパー
    │   ├── count_insns.py # B 系列の共有ツール
    │   └── <回ID>_xxx/    # 例: O3_isel/、P1_selfhost/（C 移植・セルフホスト）
    ├── guides/            # 補助ツールガイドへの導線
    └── docker/rv64/       # 推奨実行環境
```

### 発展教材の命名規則

`advanced/` はカテゴリ階層を持たず、トピックを直接並べる。
カテゴリは回 ID の頭文字が表す（F=フロントエンド、B=最適化入門、O=最適化、
R=ランタイム、S=意味論、L=言語機能、Q=品質、P=移植・セルフホスト）。

原稿 `materials/advanced/O3_isel.md` と配布物 `workbook/advanced/O3_isel/` は
**一対一で対応する**。`site/nav.yaml` はこの対応をそのまま使うため、
新しいトピックを追加するときも写像表の更新は要らない。

トップレベルは役割で6分割している。

| ディレクトリ | 役割 | 読む人 |
|--------------|------|--------|
| `design/` | 設計思想・保守手順・品質管理 | 教える側・教材を改変する人 |
| `materials/` | 資料の原稿（サイトの元） | 教材を書く人 |
| `workbook/` | 演習の配布物 | 学習者 |
| `site/` + `latex/` + `tools/` | サイトと図のビルドシステム | 教材を書く人 |
| `web/` | 補助ウェブアプリ（ブラウザで使う学習支援） | 学習者・教える側 |
| `../c-comp-design/teacher/` | Private リポジトリ内の完成解答・品質記録・隠しテスト | メンテナ |

### 設計資料と配布物の書き分け

同じ事実を両方に置かない。`design/` には**なぜそうしたか**だけを書き、
事実の一覧（全コマ表・到達目標・参考文献・コマンド手順）は `workbook/` 側を単一の出典とする。

| 情報 | 正規の置き場所 |
|------|---------------|
| 全コマ一覧・到達目標 | `workbook/docs/getting_started.md` |
| 参考文献と読むタイミング | `workbook/docs/getting_started.md` |
| Docker の使い方 | `workbook/docs/getting_started.md`（設定とトラブルシュートは `workbook/docker/rv64/README.md`） |
| テストの走らせ方・テスト形式 | `workbook/docs/testing.md` |
| RV64 の ABI・アラインメント規則 | `workbook/docs/rv64_reference.md` |
| 発展課題の一覧と前提（Python→C 移植対応表・C 実装の規約を含む） | `workbook/advanced/README.md` |
| サイトの章立てとページの並び | `site/nav.yaml` |

`materials/` は資料の原稿、`workbook/` は学習者向け配布物として扱う。
学習者経路を確認するときは、原則として `workbook/` 内だけを参照する。

通常回は `workbook/sessions/NN_xxx/mycc.py` を編集し、コマ15で `workbook/final/mycc.py` に統合する構成である。

### 用語と表記の統一

同一概念の呼び方を1つに決め、ここだけに書く。他文書に再掲しない
（`tools/check_docs.py` の `style` チェックが違反を検出する）。

| 対象 | 正 | 誤（避ける） | 備考 |
|------|----|----|------|
| 回の呼称 | `コマN`（例: コマ2、コマ15） | `第NN回`・`第N回` | H1 見出しが全16本で「コマN:」に統一されているため、本文もこれに寄せる |
| ゼロ埋め | ゼロ埋めしない（`コマ2`。`コマ03` は使わない） | `コマ08`・`コマ06` 等 | ディレクトリ名・ファイル名（`03_variables` 等）は従来どおりゼロ埋めのまま変更しない。対象は本文中の表記だけ |
| コマとNの間の空白 | 詰める（`コマ2`） | `コマ 3`・`コマ　3`（全角/半角空白・中黒スペース） | |
| 呼称（人） | 学習者 | 学生 | 公開文書の多数派に合わせる。私有側 `teacher/quality/` の記録も対象に含める（`teacher/answers/` は対象外） |
| スキャフォールド／scaffold | 地の文では「スキャフォールド」（カタカナ）。ディレクトリ名・ファイルパス（`scaffold/`）・コマンド例・インラインコード・コードブロックの中身は実体を指すのでローマ字のまま変更しない | 地の文での英字 `scaffold` | `workbook/advanced/`・`materials/advanced/` にも適用する |
| 丸括弧（`workbook/advanced/`・`materials/advanced/` 限定） | 地の文では全角（） | 地の文での半角 `()` | Big-O 記法（`O(n³)` 等）・`LL(1)` のような確立した記法、Markdown リンク／画像の `](...)`、インラインコード・コードブロックの中身、`golden.py` などが実際に印字するリテラル出力の引用は対象外。他の通常回・学習者向け文書には適用しない（この節の対象外） |
| 他トピックの参照呼称（`workbook/advanced/`・`materials/advanced/` 限定） | `発展課題 XN`（例: 発展課題 L2、発展課題 P1） | `発展 XN` | 各資料末尾の見出し「## 発展課題」（トピック内の追加課題節）とは別物。見出しはそのまま変更しない |
| 「選択制」の明記（`materials/advanced/` 限定） | 書かない（全廃） | `（選択制）` | 索引 `workbook/advanced/README.md` が「いずれも選択制」と既に宣言しているため、各トピックでの繰り返しは冗長 |
| B ファミリの呼称（`materials/advanced/B*.md` 限定） | `最適化入門発展シリーズ`（索引・B1 の見出しに合わせる） | `バックエンド発展シリーズ` | 索引 `workbook/advanced/README.md` のカテゴリ表と B1 の見出しが「最適化入門」で一致しているため、そちらに寄せる |
| 「black box」の訳語 | ブラックボックス（カタカナの借用語） | 黒箱 | 「黒箱」は英語 "black box" の逐語訳(calque)で、日本語の技術文書としては不自然。T98 でリポジトリ全体の既知の出現を置換済み |

advanced 側の「Xシリーズの第N回」（F/O/S/R/Q/B の各ファミリ内での位置づけ）は、
「回の呼称」行（コマ1〜15 を指す `第NN回` の禁止）とは無関係の別の数え方であり、
対象外（そのまま使ってよい）。

---

## 資料サイト

`materials/` の原稿と `workbook/docs/` を pandoc で HTML にして GitHub Pages へ出す。
構成は `site/nav.yaml` が単一の出典で、ページのタイトルは原稿の先頭 H1 から取る。

| 依存 | 何に要るか |
|------|-----------|
| pandoc、PyYAML | サイトの生成（`make site` / `make serve`） |
| LuaLaTeX、poppler-utils の `pdftocairo`、Graphviz | 図の生成（`make figures`） |

**図の SVG はコミット対象**なので、図を触らないなら TeX は要らない。

```bash
make site                # .site/ に全ページを生成
make serve               # 生成して http://127.0.0.1:8000/ で配信（Ctrl-C で終了）
make serve PORT=9000
make serve HOST=tailscale   # 別端末から Tailscale 経由で見る
make serve HOST=0.0.0.0     # 全インターフェース
make check-links         # 内部リンク切れを検査
make check-docs          # 原稿・配布物の整合（check-deps・check-concepts も一緒に走る）
make check-deps          # 発展課題の依存関係の整合（下記）
make check-concepts      # 概念導入台帳と原稿 frontmatter の整合（下記）
make figures             # 図の SVG を作り直す（図を触ったときだけ）
make clean               # .site/ と .pages/ を消す（コミット済みの SVG は消さない）
python3 tools/build_site.py --only 03_arith # 1ページだけ作り直す
```

CI（`.github/workflows/ci.yml`）は push のたびに `make site` と `make check-links` を通す。
**CI が入れる pandoc はディストリ版なので手元より古いことがある。**
テンプレートやフィルタで新しい機能を使ったときは、CI の `pandoc --version` の出力と
突き合わせて切り分ける。

ページ間のリンクは `sessions/02_arithmetic_codegen/` のディレクトリ形式なので、
`file://` で開いても辿れない。ローカルで見るときは必ず `make serve` を使う。

既定は `127.0.0.1` だけに開く。別端末から見るときは `HOST` を指定する。
`HOST=tailscale` は起動のたびに `tailscale ip -4` を引いて `tailscale0` のアドレスだけに
バインドする。`HOST=0.0.0.0` は全インターフェースなので、**LAN や docker bridge からも見える**。
認証は無いので、公開したい範囲に合わせて選ぶこと。

`make serve` は原稿を保存すると作り直し、ブラウザを自動で再読み込みする。
再ビルドの範囲は変更内容で変わる。

| 変えたもの | 作り直す範囲 |
|------------|--------------|
| 原稿 `.md` 1本 | そのページだけ（先頭 H1 を変えた場合は全ページ） |
| `site/style.css` | CSS のコピーのみ |
| `site/template.html`・`site/boxes.lua`・`site/nav.yaml` | 全ページ |

`web/app/dist/` があれば `/tools/` として一緒に配信するので、
ヘッダの「補助ツール」からの導線もローカルで確認できる。無い場合は `make web` で作る。

---

## テスト

```bash
# 通常回（workbook/ から実行）
cd workbook
python3 scaffold/test_runner.py sessions/02_arithmetic_codegen
python3 scaffold/test_runner.py            # final/mycc.py + final/tests

# OCaml 参考実装
cd workbook/ocaml && dune build
cd workbook/ocaml && python3 run_tests.py    # 各回を sessions/*/tests に掛ける

# 発展教材（各 topic ディレクトリから）
python3 check.py
python3 golden.py   # README で指定されている場合
```

---

## 教材追加の手順

1. `materials/sessions/`（または `materials/advanced/`）に Markdown 原稿を書く
2. 図が必要なら `materials/figures/` に TikZ ソースを追加し（`latex/figure-preamble.tex` を
   `\input` する）、`make figures` で SVG を生成してコミットする
3. `workbook/` 側に README・starter・テストを追加する。README には資料ページへのリンクを入れる
4. **`site/nav.yaml` の該当セクションに原稿のパスを1行足す**
5. 発展教材なら `workbook/advanced/README.md` の全トピック表にも1行足す。
   トピックの「## この回の位置づけ」の固定表（`必須の前提` ほか）を原稿と配布物の両方に置き、
   `fixed17` の初出は原稿側から索引の定義（`#fixed17`）へ張る
6. `make site && make check-links` で生成とリンクを確認し、`make check-docs` を通す
7. [`quality_guide.md`](./quality_guide.md) に従いレビューする

教材を改名・削除したときも 4・5 を忘れないこと。
`nav.yaml` に載せ忘れた原稿は次で検出できる。

```bash
python3 - <<'EOF'
import pathlib, yaml
nav = yaml.safe_load(open("site/nav.yaml", encoding="utf-8"))
listed = {p for s in nav["sections"] for p in s["pages"]}
found = {str(p) for p in pathlib.Path("materials").glob("*/*.md")}
print("未掲載:", sorted(found - listed) or "なし")
EOF
```

### 発展課題の依存関係（`make check-deps`）

`tools/check_advanced_deps.py` が、次の3つの情報源が互いに一致しているかを見る。
手書きの依存図が実態からずれるのを止めるための検査で、`make check-docs` からも走る。

| 情報源 | 場所 |
|--------|------|
| 一覧表 | `workbook/advanced/README.md` の「## 全トピック一覧」 |
| 位置づけブロック | 各トピックの「## この回の位置づけ」（配布物と原稿の2部） |
| 依存グラフ | 同 README の「### 依存関係」のコードブロック |

依存グラフに描くのは**直接の前提だけ**である。ここでいう直接とは、
位置づけブロックの「必須の前提」から作ったトピック間のグラフを**推移簡約**したもの、
という機械的な定義になっている。間接の前提を図に描き足しても、直接の辺を消しても、
どちらも検出される。前提を1つ書き換えたら、一覧表・原稿・配布物・図の4か所をそろえること。

### 概念導入台帳（`make check-concepts`）

通常回の原稿は先頭に YAML frontmatter を持ち、`introduces:`（その回が新しく導入する概念）と
`requires:`（前提となる概念）を列挙する。frontmatter は pandoc がメタデータとして消費するので
生成ページには出ない。単一の出典は
[`curriculum.md` の「9. 概念導入台帳」](./curriculum.md#9-概念導入台帳introduces--requires)である。

`tools/check_concepts.py` が、台帳と全回の frontmatter が一致しているかを見る。
`requires:` は台帳からの**導出値**（各概念の前提の和集合 − 同じ回で導入する概念）なので、
手で足し引きしてはならない。概念を1つ足すときは台帳に1行足し、
`make check-concepts` が示す差分どおりに原稿の frontmatter を直す。

---

## 公開時の除外と旧リポジトリとの対応

### 公開時の除外

完成解答・隠しテスト・品質記録は、兄弟の Private リポジトリ
`../c-comp-design/teacher/` だけで管理する。公開リポジトリ `c-comp` には置かない。

GitHub Pages は `main` ブランチのルートを配信する。`main` は開発ブランチではなく、
手動リリースで生成した公開物だけを置くブランチである。公開物は次の許可リストに限る。

```text
index.html                # サイトのトップ
assets/                   # スタイルシート
figures/                  # 図の SVG
sessions/ advanced/ docs/ guides/   # 資料のページ
tools/                    # ビルド済みの補助ウェブアプリ
downloads/*.zip           # workbook/ 全体の配布アーカイブ
LICENSE
THIRD_PARTY_NOTICES.md
.nojekyll
```

公開前には次を必ず行う。

1. 学習者の個人情報が含まれていないことを確認する。
   個人情報はそもそもこのリポジトリに置かない運用とし、授業ログは親リポジトリ側（`../logs/`）だけで管理する。
2. `make pages VERSION=<version>` で `.pages/` を生成し、資料のページ、ZIP、補助ツールを確認する。
3. `main` を直接編集せず、`dev` の手動リリース workflow だけで更新する。

### 内部タスク番号を公開領域に残さない

`c-comp-design/tasks/TODO.md`（およびその archive）が使う内部タスク番号（`T49` 等）は
private な計画管理リポジトリだけの内部参照であり、公開リポジトリ `c-comp` の読者が
知る必要のある情報ではない。今後のコミットメッセージ・コード中のコメント・
コミット対象のファイルには書かない。過去に紛れ込んだ履歴は書き換えない。

### GitHub の初期設定

初回コミットを `dev` に push したら、GitHub 側で次を設定する。

1. `dev` を既定ブランチにする。
2. **Settings > Actions > General** で workflow の `Read and write permissions` を許可する。
3. **Settings > Pages** で `Deploy from a branch`、ブランチ `main`、フォルダ `/(root)` を選ぶ。
   `main` は最初の **Release Pages** 成功後に作成されるため、その後で設定する。
4. `main` の branch protection は通常利用者の直接 push を禁止し、
   `github-actions[bot]` にだけ release workflow 用の push を許可する。
5. `dev` は通常のレビュー・CI対象ブランチとして保護する。

**Release Pages** は `dev` を表示中に手動起動し、`v0.1.0` のような版番号を入力する。
workflow はテスト、Web ビルド、公開物の許可リスト検査、ZIP 検査を通過したときだけ
`main` を更新する。`main` を手で修正した場合、次回リリースで失われる。

### 旧リポジトリとの対応

このリポジトリは授業運用側の親リポジトリ（`incremental_c/`）から再構成した。
`../c-comp-design/teacher/` に置いた完成解答・品質記録の旧記述は、次の対応で読み替える。

| 旧（親リポジトリ） | 新（このリポジトリ） |
|--------------------|----------------------|
| `c-comp/` | `workbook/` |
| `c-comp-design/teacher/ocaml_reference/` | `workbook/ocaml/` |
| `c-comp/advanced/<カテゴリ>/<旧ID>_xxx/` | `workbook/advanced/<新ID>_xxx/`（フラット構成） |

発展課題の回 ID の対応（ディレクトリ名は `workbook/advanced/`・`c-comp-design/teacher/answers/` と一致する）:

| 旧ID | 新ID | | 旧ID | 新ID |
|------|------|-|------|------|
| `b1_fold_peephole` | `B1_fold_peephole` | | `o1_measure`〜`o7_layout` | `O1_measure`〜`O7_layout`（大文字化のみ） |
| `b2_regalloc` | `B2_regalloc` | | `f0_cyk`〜`f4_parser_decl` | `F0_cyk`〜`F4_parser_decl`（大文字化のみ） |
| `b3_tailcall` | `B3_tailcall` | | `q1_typecheck` | `Q1_typecheck` |
| `d3_struct` | `S3_struct` | | `r1_nolibc`〜`r3_malloc` | `R1_nolibc`〜`R3_malloc`（大文字化のみ） |
| `d4_initializer` | `L2_compound_assign`（主題変更） | | `m1_shortcircuit` | `S1_shortcircuit` |
| `v1_variadic` | `L3_variadic` | | `m2_int32` / `m3_ptrdiff` | `S2_int32` / `L1_ptrdiff` |

2026-08-01 に、S / L の判定基準（索引の「S と L の判定基準」節）に合わせて2本を移した。
番号は入れ替えで、欠番は作っていない。公開 URL とディレクトリ名も同時に変わる。

| 2026-08-01 より前 | 現在 | ラッパー |
|-------------------|------|----------|
| `S3_ptrdiff` | `L1_ptrdiff` | `semcc.py` → `langcc.py`（環境変数も `SEMCC_*` → `LANGCC_*`） |
| `L1_struct` | `S3_struct` | `langcc.py` → `semcc.py`（環境変数も `LANGCC_*` → `SEMCC_*`） |

学習者向けの移行案内は非公開リポジトリの `../c-comp-design/teacher/handouts/migration_2026-08-01.md`
にあり、必要な学習者にはメンテナが個別に渡す（公開サイトには置かない）。

---

## 教材の品質管理

教材を作成、レビュー、公開、改善するときは
[`quality_guide.md`](./quality_guide.md) に従う。

教材別の品質状態、レビュー証拠、公開判断は
`../c-comp-design/teacher/quality/template.md` から記録を作り、
`../c-comp-design/teacher/quality/records/` に保存する。
