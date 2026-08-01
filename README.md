# 実践・Cコンパイラ演習

C 言語サブセットのコンパイラを、**動く状態を保ちながら**段階的に作り上げる演習教材。

- **方針**: 「Python で理解 → C に移植」。前半は Python でコンパイラの論理だけに集中し、後半は動く Python 版を参照実装として C へ移植する
- **ターゲット**: RISC-V RV64（qemu で実行。実機不要）
- **到達点**: Python 版 C サブセットコンパイラの完成。その先は選択制の発展課題（フロントエンド自作・最適化・C 移植/セルフホストなど）に挑戦できる
- **対象**: C 言語既習・コンパイラ理論未習の学習者（大学2年生以上を想定）

## 特徴

- **1コマ1機能**: Ghuloum (2006) のインクリメンタル方式。各コマは資料を読んで実装し、その日のうちに動かして確認する粒度に分割してある
- **常に動く**: どの時点でも実行可能なコンパイラを維持する。生成アセンブリは毎回 qemu で実行して確かめる
- **Lexer/Parser は最初は黒箱**: 提供スキャフォールドを使い、コード生成から書き始める。フロントエンドの自作は発展課題として用意してある
- **発展教材**: フロントエンド自作・最適化（CFG・レジスタ割り当て・生存解析）・ランタイム自作（printf / malloc）・型検査・C 移植/セルフホストなど 26 テーマ
- **OCaml 参考実装つき**: 各回の完成形に相当する OCaml 版を同梱。詰まったときの言語横断ヒントとして使える

## はじめかた

学習者は [`workbook/`](./workbook/README.md) だけを見ればよい。演習はこの中で完結する。

リポジトリルートから実行する。

```bash
# 推奨: Docker で RV64 実行環境を用意
bash workbook/docker/rv64/run.sh

# コマ1の環境確認
bash workbook/docker/rv64/run.sh python3 sessions/01_environment/check.py
```

読む順序:

1. [`workbook/docs/getting_started.md`](./workbook/docs/getting_started.md) — 進め方ガイド（環境の用意・全16コマ一覧）
2. [コマ1の資料](https://yf-fyf.github.io/c-comp/sessions/01_environment/) — 資料サイトを順に読み進める
3. [`workbook/docs/language_spec.md`](./workbook/docs/language_spec.md) — 対象言語（Core プロファイル）の仕様

## リポジトリ構成

| パス | 内容 | 読む人 |
|------|------|--------|
| [`workbook/`](./workbook/README.md) | 演習の配布物（starter・テスト・実行環境・参考実装） | 学習者 |
| [`materials/`](./materials/) | 資料の Markdown 原稿と図の TikZ ソース | 教材を書く人 |
| [`design/`](./design/curriculum.md) | カリキュラム設計書・保守手順・品質管理ガイド | 教える側・改変する人 |
| [`site/`](./site/) / [`tools/`](./tools/) | 資料サイトのビルドシステム | 教材を書く人 |
| [`AGENTS.md`](./AGENTS.md) | AI コーディングエージェント向けガイド | — |

## 資料サイトを自前でビルドする場合

リポジトリルートから実行する。

```bash
make site      # .site/ に生成
make serve     # 生成して http://127.0.0.1:8000/ で配信（保存すると自動リロード）
```

必要なのは pandoc と PyYAML だけ。図の SVG はコミット済みのものを使う。
図の TikZ ソースを書き換えるときだけ、LuaLaTeX（Noto Sans CJK JP / Inconsolata）、
poppler-utils、Graphviz を用意して `make figures` を実行する。

## 公開とリリース

開発は既定ブランチの `dev` で行う。GitHub Pages 用の `main` は手動リリースで
生成する公開専用ブランチであり、直接編集しない。Pages には資料サイト、
ビルド済み補助ツール、`workbook/` 全体の ZIP を置く。

GitHub Actions の **Release Pages** を `dev` から手動実行し、`v0.1.0` のような
リリース番号を指定する。ローカルで公開物を確認する場合は、リポジトリルートから次を実行する。

```bash
make pages VERSION=v0.1.0
# .pages/index.html を開く。配信するのは .pages/ の内容だけ
```

完成解答・隠しテスト・品質記録は公開リポジトリに置かず、Private リポジトリ
`../c-comp-design/` で管理する。詳細は
[`design/maintaining.md`](./design/maintaining.md) を参照。

## ライセンス

MIT License。第三者依存の扱いは [`THIRD_PARTY_NOTICES.md`](./THIRD_PARTY_NOTICES.md) を参照。

## 参考文献

- Abdulaziz Ghuloum, "An Incremental Approach to Compiler Construction" (Scheme Workshop 2006)
- Rui Ueyama「低レイヤを知りたい人のための C コンパイラ作成入門」
