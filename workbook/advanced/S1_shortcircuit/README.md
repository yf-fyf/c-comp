# S1: 短絡評価 — `&&` と `||` の本当の意味

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/S1_shortcircuit/](https://yf-fyf.github.io/c-comp/advanced/S1_shortcircuit/) にあります。

## 今日のゴール

`&&` / `||` を C の規格どおり「必要なときだけ右辺を評価する」形に直す。
`if (p != 0 && p->val > 0)` が書けるようになる。

前提はコマ8 まで。**`mycc.py` は書き換えません**（`semcc.py` が差し替えます）。

## 編集するファイル

- `shortcircuit.py`（Step 1: gen_and、Step 2: gen_or）

## テスト

```bash
python3 check.py     # 生成された命令列の構造を確認(未実装は SKIP)
python3 golden.py    # 短絡が要るテスト + fixed15
```
