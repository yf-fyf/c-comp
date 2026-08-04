# S3: 構造体の代入 — レジスタに載らないものを運ぶ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/S3_struct/](https://yf-fyf.github.io/c-comp/advanced/S3_struct/) にあります。

## 今日のゴール

`q = p;` で構造体をまるごとコピーできるようにする。
ポインタ・フィールドを持つ構造体やポインタ経由の代入も動くようにする。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ12（構造体）まで。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ15 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `semcc.py`（配布済み・完成品） |
| 編集する | `structcopy.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が構造体代入のテストの通過と `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の内側**。`language_spec.md` は「struct 変数は宣言できるが、struct 値の代入・実引数・戻り値は不可」と定めているのに、実装は `q = p;` をエラーにせず受理して誤った答えを返す。判定基準どおりの **S 系**である |
| 備考 | 意味論発展シリーズの第3回。引数・戻り値の値渡しはこの回では扱わない（発展課題 L5 で実装する） |

> **この回は 2026-08-01 に `L1_struct/` から `S3_struct/` へ改名した。**
> ラッパーも L ファミリの `langcc.py` から S ファミリの `semcc.py` に変わっている。

## 編集するファイル

- `structcopy.py`（Step 1: is_struct_assign、Step 2: gen_struct_copy）

## テスト

```bash
python3 check.py     # 判定と生成命令列を確認(未実装は SKIP)
python3 golden.py    # 構造体代入のテスト + fixed17
```

土台のコンパイラを差し替えたいときは環境変数 `SEMCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
