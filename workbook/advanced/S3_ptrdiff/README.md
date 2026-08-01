# S3: ポインタ同士の引き算 — 差は「要素いくつ分か」

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/S3_ptrdiff/](https://yf-fyf.github.io/c-comp/advanced/S3_ptrdiff/) にあります。

## 今日のゴール

`p - q` を、アドレスの差（バイト数）ではなく「要素いくつ分か」を返すように直す。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ10（ポインタ演算）まで |
| 推奨の前提 | コマ16（`golden.py` は `final/mycc.py` を土台に `fixed17` を回すため、未了だと安全網の確認まで進めない） |
| 改変しない | `mycc.py`、`scaffold/`、ラッパー `semcc.py`（配布済み・完成品） |
| 編集する | `ptrdiff.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が「修正なしで落ち、修正ありで通る」ことと `fixed17` 全通を報告する |
| コマ数 | 1 |
| 備考 | 意味論発展シリーズの第3回。3本の中では最も小さい |

## 編集するファイル

- `ptrdiff.py`（Step 1: is_ptr_diff、Step 2: gen_ptr_diff）

## テスト

```bash
python3 check.py     # 判定と生成命令列を確認(未実装は SKIP)
python3 golden.py    # 修正なしで落ち、修正ありで通ること + fixed17
```
