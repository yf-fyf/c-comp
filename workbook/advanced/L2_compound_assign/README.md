# L2: 複合代入 — 左辺を1回しか評価しない

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L2_compound_assign/](https://yf-fyf.github.io/c-comp/advanced/L2_compound_assign/) にあります。

## 今日のゴール

`x += 3;` `p -= 1;` `x %= 5;` のような複合代入（`+= -= *= /= %=`）を、
字句・構文・コード生成の3段すべてで動くようにする。

複合代入は `language_spec.md` の外側にある機能です。この回で追加する構文と意味論は
資料の「L2 が追加する仕様」節が定義します。

`x = x + 3` への書き換え（脱糖）では駄目で、`*bump() += 10` のように
左辺が副作用を持つと `bump()` が2回呼ばれてしまいます。
「複合代入の左辺は1回だけ評価される」がこの回の中心的な規則です。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ13（グローバル変数）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（`lexer.py`・`parser.py` を含む）、ラッパー `langcc.py`（配布済み・完成品） |
| 編集する | `compound.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が複合代入のテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の外側**。`language_spec.md` は演算子節の「除外」に複合代入を挙げている。追加する構文と意味論は資料の「L2 が追加する仕様」節が定義する |
| 備考 | 言語機能発展シリーズ。複合代入は `language_spec.md` の外側にある機能で、追加する構文と意味論は資料の「L2 が追加する仕様」節が定義する |

## 編集するファイル

- `compound.py`（Step 1: extend_puncts、Step 2: gen_compound_assign、Step 3: scale_rhs_for_ptr）

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 複合代入のテスト + fixed17
```

`tests/*.c` は標準トラックの字句では読めないソースなので、
web の golden テストでは skip として数えられます（失敗ではありません）。

土台のコンパイラを差し替えたいときは環境変数 `LANGCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
