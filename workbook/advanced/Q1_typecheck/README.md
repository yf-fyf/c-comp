# Q1: 型検査パス — 実行する前に間違いを見つける

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/Q1_typecheck/](https://yf-fyf.github.io/c-comp/advanced/Q1_typecheck/) にあります。

## 今日のゴール

コード生成の前に AST を検査し、未定義の変数・未定義の関数・引数の個数違い・
代入できない左辺を **まとめて** 報告するパスを書く。

前提はコマ12 まで。**`mycc.py` は書き換えません**（`checkcc.py` が差し込みます）。

## 編集するファイル

- `typecheck.py`（Step 1: check_var、Step 2: check_call、Step 3: check_assign、
  Step 4: check_incdec）

## 動かし方

```bash
python3 checkcc.py --check-only tests/undefined_var.c   # 検査だけ
python3 checkcc.py ../../final/tests/f09_recur.c     # 検査してからコンパイル
```

## テスト

```bash
python3 check.py     # エラーコーパス(`tests/*.c` と `*.expected` の一致)
python3 golden.py    # 正常系(講義のテスト入力101本で誤検出ゼロ)
```

`check.py` を全 PASS にしてから `golden.py` を回します。
