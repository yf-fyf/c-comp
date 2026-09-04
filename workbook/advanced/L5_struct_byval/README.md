# L5: 構造体の値渡し・値返し — 呼び出し規約を自分で決める

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L5_struct_byval/](https://yf-fyf.github.io/c-comp/advanced/L5_struct_byval/) にあります。

## 今日のゴール

`int sum(struct Point p)` のように構造体を**値で受け取り**、
`struct Point make(int x, int y)` のように構造体を**値で返せる**ようにします。

構造体の値渡し・値返しは `language_spec.md` が構文レベルで禁じている機能です。
この回で追加する構文と意味論、そして**呼び出し規約そのもの**は
資料の「L5 が追加する仕様」節が定義します。

`q = p;`（S3）はレジスタに載らないものを**同じ関数の中で**運ぶ話でした。
この回はそれを**関数の境界をまたいで**運びます。
境界をまたぐと「どちらがコピーするのか」「戻り値の置き場を誰が用意するのか」
という、言語仕様には書かれていない取り決め —— 呼び出し規約 —— を決める必要が出てきます。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ12（構造体）まで、および [S3](../S3_struct/)（構造体の代入）。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（`lexer.py`・`parser.py` を含む）、ラッパー `langcc.py`（配布済み・完成品） |
| 編集する | `byval.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が値渡し・値返しのテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の外側**。`language_spec.md` は `param ::= scalar_type IDENT`・`ret_type ::= scalar_type \| 'void'` と定めて struct 値の実引数・戻り値を構文レベルで禁じている。追加する構文と意味論は資料の「L5 が追加する仕様」節が定義する |
| 備考 | 言語機能発展シリーズ。L 系列で**最も重い**回で、L3（可変長引数の定義側）と並ぶ。コード生成が呼び出し規約そのものに踏み込む |

## 編集するファイル

- `byval.py`（Step 1: copy_struct、Step 2: gen_arg、Step 3: gen_param_prologue、Step 4: gen_sret_call、Step 5: gen_struct_return）

Step 1〜3 まで書けば**値渡し**が、Step 4〜5 まで書けば**値返し**が動きます。

## テスト

```bash
python3 check.py     # Step ごとの単体テスト(未実装は SKIP)
python3 golden.py    # 値渡し・値返しのテスト + fixed17
```

`check.py` は出た命令列を小さな RV64 シミュレータで実際に走らせ、
「コピーが本当に起きたか」「呼び出し元が無傷か」をメモリの内容で確かめます。

`tests/*.c` は標準トラックの構文では読めないソースなので、
web の golden テストでは skip として数えられます（失敗ではありません）。

土台のコンパイラを差し替えたいときは環境変数 `LANGCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
