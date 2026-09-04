# Q1: 型検査パス — 実行する前に間違いを見つける

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/Q1_typecheck/](https://yf-fyf.github.io/c-comp/advanced/Q1_typecheck/) にあります。

## 今日のゴール

コード生成の前に AST を検査し、未定義の変数・未定義の関数・引数の個数違い・
代入できない左辺を **まとめて** 報告するパスを書きます。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ12 まで |
| 推奨の前提 | コマ15（`golden.py` の正常系コーパスに `final/tests`（`fixed17`）が含まれるので、未了だとその分だけ確認できない） |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `checkcc.py`（配布済み・完成品） |
| 編集する | `typecheck.py` |
| 完了条件 | `check.py` がエラーコーパスの全件で `*.expected` と一致し、`golden.py` が正常系のテスト入力全体で誤検出ゼロを報告する |
| コマ数 | 1 |
| 備考 | 品質発展シリーズの第1回。コンパイラ本体には手を入れず、独立したパスとして追加する |

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

土台のコンパイラを差し替えたいときは環境変数 `CHECKCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
