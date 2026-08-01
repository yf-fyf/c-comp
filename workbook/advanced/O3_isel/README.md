# O3: 命令選択 — 複数の命令を1つに畳む

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O3_isel/](https://yf-fyf.github.io/c-comp/advanced/O3_isel/) にあります。

## 今日のゴール

「アドレス計算 + ロード」を、RV64 の `offset(base)` 形式のロード1命令に畳む。
`fixed17` を通したまま、静的・動的の両方で命令数を減らす。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | O1（測定基盤。`golden.py` が `measure.py` と `O1_measure/bench/` を使う） |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `isel.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `fixed17` 全通と静的・動的の命令数削減を報告する |
| コマ数 | 2 |
| 備考 | 最適化発展シリーズの第3回。O2・O4・O5 とは独立している。索引の一覧表では2コマぶんとしているが、O4・O6 と違って資料に明示の区切りは置いていない |

## 編集するファイル

- `isel.py`（Step 1: fold_load、Step 2: is_dead_after、
  Step 3: fold_store / fold_mul_to_shift、Step 4: run）

## 動かし方

```bash
python3 ../optcc.py --passes isel ../O1_measure/bench/matmul.c
python3 ../optcc.py --passes '' ../O1_measure/bench/matmul.c   # 最適化なし
```

## テスト

```bash
python3 check.py     # 各置き換えの単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 + ベンチマーク + 静的/動的の削減
```

土台のコンパイラを差し替えたいときは環境変数 `OPTCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
