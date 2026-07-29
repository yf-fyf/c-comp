# S3: ポインタ同士の引き算 — 差は「要素いくつ分か」

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

`p - q` を、アドレスの差(バイト数)ではなく「要素いくつ分か」を返すように直す。

前提はコマ10 まで。**`mycc.py` は書き換えません**（`semcc.py` が差し替えます）。

## 編集するファイル

- `ptrdiff.py`（Step 1: is_ptr_diff、Step 2: gen_ptr_diff）

## テスト

```bash
python3 check.py     # 判定と生成命令列を確認(未実装は SKIP)
python3 golden.py    # 修正なしで落ち、修正ありで通ること + fixed15
```
