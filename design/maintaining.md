# 実装ガイド（メンテナ用）

教材の開発・保守を行う際の規約・手順・参考情報。
学習者向けの実装規約は [`../workbook/docs/conventions.md`](../workbook/docs/conventions.md) を参照。

---

## ディレクトリ構成

```
.
├── README.md              # プロジェクト入口
├── index.md               # HackMD 用ルートページ（公開資料一覧。手書き）
├── AGENTS.md              # AI エージェント向けガイド
├── LICENSE
├── Makefile               # PDF ビルド
├── design/                # 設計・運用文書（教える側・改変する側向け）
│   ├── curriculum.md      # カリキュラム設計書
│   ├── maintaining.md     # このファイル
│   ├── quality_guide.md   # 教材品質管理・AIレビュー手順
│   └── webapps.md         # 補助ウェブアプリの企画書（企画段階）
├── materials/             # handout の Markdown 原稿
│   ├── sessions/          # 通常回（コマ1〜16）の原稿 NN_xxx.md
│   ├── advanced/          # 発展教材の原稿 <回ID>_xxx.md
│   ├── tools/             # 補助ツールガイドの原稿
│   └── figures/           # 図の TikZ ソースと生成 PDF（sessions・advanced 共用）
│       └── ast/           # AST 図（parse_viewer + graphviz で生成）
├── latex/                 # Pandoc + LuaLaTeX テンプレート
├── tools/                 # PDF ビルドスクリプト・ウェブアプリの生成スクリプト
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
    │   ├── debugging.md       # 症状から原因を絞る（読む）
    │   ├── language_spec.md   # Core プロファイル（引く）
    │   ├── rv64_reference.md  # ABI・スタックフレーム・命令（引く）
    │   ├── testing.md         # test_runner・テスト形式（引く）
    │   └── code_example.md    # 到達目標コード例（コマ1〜16、引く）
    ├── scaffold/          # 提供スキャフォールド（Lexer/Parser/AST/テストランナー）
    ├── sessions/          # 通常回 NN_xxx/（資料・starter・テスト）
    ├── final/             # コマ16で作る最終統合版
    ├── ocaml/             # OCaml 版参考実装（コマ2〜16、完成相当）
    ├── advanced/          # 発展教材。1トピック=1ディレクトリのフラット構成
    │   ├── README.md      # 全トピック一覧・カテゴリ別の解説
    │   ├── optcc.py       # O 系列の共有ラッパー
    │   ├── count_insns.py # B 系列の共有ツール
    │   └── <回ID>_xxx/    # 例: O3_isel/、S1_shortcircuit/
    ├── porting/           # C 移植・セルフホスト（C 実装の規約と移植対応表もここ）
    ├── guides/            # 補助ツールガイド（PDF）
    └── docker/rv64/       # 推奨実行環境
```

### 発展教材の命名規則

`advanced/` はカテゴリ階層を持たず、トピックを直接並べる。
カテゴリは回 ID の頭文字が表す（F=フロントエンド、B=最適化入門、O=最適化、
R=ランタイム、S=意味論、L=言語機能、Q=品質）。

原稿 `materials/advanced/O3_isel.md` と配布物 `workbook/advanced/O3_isel/` は
**一対一で対応する**。`tools/build_advanced_pdfs.py` はこの対応をそのまま使うため、
新しいトピックを追加するときも写像表の更新は要らない。

トップレベルは役割で6分割している。

| ディレクトリ | 役割 | 読む人 |
|--------------|------|--------|
| `design/` | 設計思想・保守手順・品質管理 | 教える側・教材を改変する人 |
| `materials/` | handout の原稿（PDF の元） | 教材を書く人 |
| `workbook/` | 演習の配布物 | 学習者 |
| `latex/` + `tools/` | PDF ビルドシステム | 教材を書く人 |
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
| Python→C 移植対応表・C 実装の規約 | `workbook/porting/README.md` |
| 発展課題の一覧と前提 | `workbook/advanced/README.md` |

`index.md`（HackMD 用ルートページ）は単体で読めることを優先するため、
この原則の例外として一覧を再掲してよい。

`materials/` は handout の原稿、`workbook/` は学習者向け配布物として扱う。
学習者経路を確認するときは、原則として `workbook/` 内だけを参照する。

通常回は `workbook/sessions/NN_xxx/mycc.py` を編集し、コマ16で `workbook/final/mycc.py` に統合する構成である。

---

## PDF ビルド

リポジトリルートから実行する。依存: pandoc、LuaLaTeX（Noto Sans CJK JP / Inconsolata フォント）、Graphviz。

```bash
make figures             # 図 PDF（materials/figures/）
make handouts            # 通常回 handout（workbook/sessions/NN_xxx/handout.pdf）
make handout SESSION=04_variables   # 個別生成
make advanced-handouts   # 発展教材 handout
make tool-pdfs           # 補助ツールガイド PDF
make clean               # 生成 PDF の削除
```

生成物（handout.pdf・図 PDF）はコミット対象とする。
ビルド環境がなくても教材を利用できるようにするためである。

---

## テスト

```bash
# 通常回（workbook/ から実行）
cd workbook
python3 scaffold/test_runner.py sessions/03_arithmetic_codegen
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
2. 図が必要なら `materials/figures/` に TikZ ソースを追加する（`latex/figure-preamble.tex` を `\input` する）
3. `workbook/` 側に README・starter・テストを追加する
4. `make handout SESSION=...` で PDF を生成し、`workbook/` 側に配置されることを確認する
5. **`index.md` の該当する表に1行足す**（HackMD 用ルートページは手書きなので自動追従しない）
6. 発展教材なら `workbook/advanced/README.md` の全トピック表にも1行足す
7. [`quality_guide.md`](./quality_guide.md) に従いレビューする

教材を改名・削除したときも 5・6 を忘れないこと。掲載漏れは次で検出できる。

```bash
# disk 上の PDF がすべて index.md に載っているか
python3 - <<'EOF'
import pathlib
t = pathlib.Path("index.md").read_text()
pdfs = sorted(str(p) for p in pathlib.Path("workbook").rglob("*.pdf"))
print("未掲載:", [p for p in pdfs if p not in t] or "なし")
EOF
```

---

## HackMD 用ルートページ（`index.md`）

`index.md` は公開資料の一覧ページで、[HackMD](https://hackmd.io/) に貼って使うことを想定している。
PDF はリポジトリ側に置いたまま、HackMD 側からは絶対 URL で参照する。

`index.md` 内のリンクは `{{BASE_URL}}` プレースホルダになっている。**公開時に置換が必要**である。

```bash
# 例: GitHub の blob URL に置換する
sed -i 's|{{BASE_URL}}|https://github.com/<user>/<repo>/blob/main|g' index.md
```

blob 形式のベース URL にすると PDF と Markdown の両方が同じベースで開ける。
GitHub Pages 形式にすると `.md` が HTML にならないので、仕様・参考文書へのリンクが素のテキストで表示される。

置換したら、冒頭の `:::warning`（リンクが未設定であることの注意書き）を削除してから HackMD に貼る。

参照先がすべて実在するかは次で確認できる。

```bash
python3 - <<'EOF'
import re, pathlib
t = pathlib.Path("index.md").read_text()
refs = re.findall(r'\{\{BASE_URL\}\}/([^\s)]+)', t)
print("実在しない:", [u for u in refs if not pathlib.Path(u).exists()] or "なし")
EOF
```

---

## 公開時の除外と旧リポジトリとの対応

### 公開時の除外

完成解答・隠しテスト・品質記録は、兄弟の Private リポジトリ
`../c-comp-design/teacher/` だけで管理する。公開リポジトリ `c-comp` には置かない。

GitHub Pages は `main` ブランチのルートを配信する。`main` は開発ブランチではなく、
手動リリースで生成した公開物だけを置くブランチである。公開物は次の許可リストに限る。

```text
index.html
handouts/                 # workbook/ 内の handout.pdf と guides の PDF
tools/                    # ビルド済みの補助ウェブアプリ
downloads/*.zip           # workbook/ 全体の配布アーカイブ
docs/debugging.md
LICENSE
THIRD_PARTY_NOTICES.md
.nojekyll
```

公開前には次を必ず行う。

1. 学習者・学生の個人情報が含まれていないことを確認する。
   個人情報はそもそもこのリポジトリに置かない運用とし、授業ログは親リポジトリ側（`../logs/`）だけで管理する。
2. `python3 tools/build_pages.py <version>` で `.pages/` を生成し、PDF、ZIP、補助ツールを確認する。
3. `main` を直接編集せず、`dev` の手動リリース workflow だけで更新する。
4. HackMD に掲載する場合だけ、`index.md` の `{{BASE_URL}}` を置換する（前節参照）。

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
| `d3_struct` | `L1_struct` | | `r1_nolibc`〜`r3_malloc` | `R1_nolibc`〜`R3_malloc`（大文字化のみ） |
| `d4_initializer` | `L2_initializer` | | `m1_shortcircuit` | `S1_shortcircuit` |
| `v1_variadic` | `L3_variadic` | | `m2_int32` / `m3_ptrdiff` | `S2_int32` / `S3_ptrdiff` |

---

## 教材の品質管理

教材を作成、レビュー、公開、改善するときは
[`quality_guide.md`](./quality_guide.md) に従う。

教材別の品質状態、レビュー証拠、公開判断は
`../c-comp-design/teacher/quality/template.md` から記録を作り、
`../c-comp-design/teacher/quality/records/` に保存する。
