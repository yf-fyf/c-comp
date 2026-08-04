# L4: sizeof 単項式 — 答えは合っているのに、間違っている

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L4_sizeof_expr/](https://yf-fyf.github.io/c-comp/advanced/L4_sizeof_expr/) にあります。

## 今日のゴール

`sizeof x` `sizeof *p` `sizeof (a + 1)` のような**式形式の `sizeof`** を追加する。
コマ9 で作った `sizeof(型名)` 形式はそのまま残し、両方を1トークンの先読みで見分ける。

`sizeof` 式は `language_spec.md` の外側にある機能です。この回で追加する構文と意味論は
資料の「L4 が追加する仕様」節が定義します。

中心にあるのは「**`sizeof` はオペランドを評価しない**」という規則です。
`sizeof bump()` は `bump()` を呼ばずに `4`（`int` のサイズ）になります。
オペランドをコード生成してしまうと、数だけは合っているのに `bump()` が呼ばれてしまう
—— L2 の「複合代入の左辺は1回だけ評価される」と同型の罠です。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ12（構造体）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（`lexer.py`・`parser.py` を含む）、ラッパー `langcc.py`（配布済み・完成品） |
| 編集する | `sizeofexpr.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が sizeof 式のテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の外側**。`language_spec.md` は `sizeof` を「型名形式のみ」と定め、除外機能の一覧に `sizeof` 式を挙げている。追加する構文と意味論は資料の「L4 が追加する仕様」節が定義する |
| 備考 | 言語機能発展シリーズ。L 系列で最も軽い入口で、字句の変更は無く、コード生成も1命令で終わる |

## 編集するファイル

- `sizeofexpr.py`（Step 1: static_type_of、Step 2: gen_sizeof_expr、Step 3: reject_incomplete）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # sizeof 式のテスト + fixed17
```

`tests/*.c` は標準トラックの構文では読めないソースなので、
web の golden テストでは skip として数えられます（失敗ではありません）。

土台のコンパイラを差し替えたいときは環境変数 `LANGCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
