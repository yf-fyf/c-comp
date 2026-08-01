# L1: ポインタ同士の引き算 — 差は「要素いくつ分か」

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L1_ptrdiff/](https://yf-fyf.github.io/c-comp/advanced/L1_ptrdiff/) にあります。

## 今日のゴール

`p - q` を、アドレスの差（バイト数）ではなく「要素いくつ分か」を返すように直す。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ13（`malloc`）まで。差の考え方そのものはポインタ演算までで足りるが、`tests/count.c` が `malloc` を、`tests/use_result.c` が `struct` と `malloc` を使う。完了条件のうち `golden.py` は完成した `final/mycc.py` を土台に `fixed17` を回すので、やり切るにはコマ16 も要る |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `langcc.py`（配布済み・完成品） |
| 編集する | `ptrdiff.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が「修正なしで落ち、修正ありで通る」ことと `fixed17` 全通を報告する |
| コマ数 | 1 |
| 仕様との関係 | **仕様の外側**。`language_spec.md` は「ポインタ同士の減算…はない」と明示的に除外している。「要素いくつ分か」を返す意味はこの回で自分で決めて足す。判定基準どおりの **L 系**である |
| 備考 | 言語機能発展シリーズ。L2・L3 とは独立している。3本の中では最も小さい |

> **この回は 2026-08-01 に `S3_ptrdiff/` から `L1_ptrdiff/` へ改名した。**
> ラッパーも S ファミリの `semcc.py` から L ファミリの `langcc.py` に変わっている。
> 経緯と手元での対処は [`../../docs/migration.md`](../../docs/migration.md) にある。

## 編集するファイル

- `ptrdiff.py`（Step 1: is_ptr_diff、Step 2: gen_ptr_diff）

## テスト

```bash
python3 check.py     # 判定と生成命令列を確認(未実装は SKIP)
python3 golden.py    # 修正なしで落ち、修正ありで通ること + fixed17
```

土台のコンパイラを差し替えたいときは環境変数 `LANGCC_COMPILER` を設定します
（命名規則は [`../README.md`](../README.md) の「環境変数の名前」を参照）。
