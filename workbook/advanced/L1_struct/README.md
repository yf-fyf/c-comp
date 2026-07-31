# L1: 構造体の代入 — レジスタに載らないものを運ぶ

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/L1_struct/](https://yf-fyf.github.io/c-comp/advanced/L1_struct/) にあります。

## 今日のゴール

`q = p;` で構造体をまるごとコピーできるようにする。
ポインタ・フィールドを持つ構造体やポインタ経由の代入も動くようにする。

前提はコマ12 まで。**`mycc.py` は書き換えません**（`langcc.py` が差し替えます）。

引数・戻り値の値渡しは扱いません（発展課題で設計のみ）。

## 編集するファイル

- `structcopy.py`（Step 1: is_struct_assign、Step 2: gen_struct_copy）

## テスト

```bash
python3 check.py     # 判定と生成命令列を確認(未実装は SKIP)
python3 golden.py    # 構造体代入のテスト + fixed17
```
