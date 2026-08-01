# R3: 自前 malloc — ヒープを自分で管理する

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/R3_malloc/](https://yf-fyf.github.io/c-comp/advanced/R3_malloc/) にあります。

## 今日のゴール

`malloc` を自分で書く。バンプ割り当て → ヘッダ付きの再利用まで作り、
コマ13 の連結リストを自前アロケータの上で動かす。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ13（`malloc` と連結リスト）まで |
| 推奨の前提 | コマ16（実質必須に近い。`check.py` が `final/mycc.py` で `tests/*.c` をコンパイルするので、無いと実行できない） |
| 改変しない | `mycc.py`、`scaffold/` |
| 編集する | `mymalloc.c` |
| 完了条件 | `check.py` の全 Step が PASS になる（このトピックに `golden.py` は無い） |
| コマ数 | 1 |
| 備考 | ランタイム発展シリーズの第3回。R1・R2 とは独立している（libc は使ってよい） |

## 編集するファイル

- `mymalloc.c`（Step 1: 切り出し、Step 2: 再利用、Step 3: 使用量）

## テスト

```bash
python3 check.py
```

| テスト | 確認内容 |
|--------|---------|
| `list_build.c` | 自前 malloc で連結リストが作れる |
| `reuse.c` | 解放したブロックが再利用される |
| `exhaust.c` | 使い切ったら 0 を返す |
