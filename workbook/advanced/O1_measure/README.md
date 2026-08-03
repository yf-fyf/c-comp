# O1: 最適化の測り方 — 静的と動的は別物

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O1_measure/](https://yf-fyf.github.io/c-comp/advanced/O1_measure/) にあります。

## 今日のゴール

最適化の効果を測る物差しを2つ作る（静的命令数と動的命令数）。
以降のすべての最適化の回が、この物差しとベンチマーク集を使う。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ15（完成した `final/mycc.py`） |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `measure.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` がベンチマークの正しさと静的／動的の表を報告する |
| コマ数 | 1 |
| 備考 | 最適化発展シリーズの第1回。以降のすべての回が、この物差しとベンチマーク集 `bench/` を使う。O 系列の命令数の基準表もこの回に置いてある |

## 編集するファイル

- `measure.py`（Step 1: count_static、Step 2: count_dynamic の数え上げ）

## テスト

```bash
python3 check.py     # 数え上げの単体テスト(未実装は SKIP)
python3 golden.py    # ベンチマークの正しさ + 静的/動的の表
```

## ベンチマーク集

`bench/` の5本（`loop_sum` / `matmul` / `fib_rec` / `bubble` / `strops`）は
以降の回でも共通で使います。正しさは `test_runner.py` で確認できます。

```bash
python3 ../../scaffold/test_runner.py \
    --compiler ../optcc.py --tests bench
```

土台のコンパイラを差し替えたいときは環境変数 `OPTCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。

## 命令数の基準表

O 系列の資料が出す「前 → 後」の表は、どれもこの回の資料にある
**全構成の基準表**（素 / +isel / +regalloc / +copyprop,dce / +layout の5構成）からの
差分です。数字が食い違って見えたら、まず基準表と突き合わせてください。
