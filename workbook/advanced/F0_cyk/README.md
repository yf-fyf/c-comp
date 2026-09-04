# F0: 字句解析と構文解析 — CYK 法で数式を解く

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/F0_cyk/](https://yf-fyf.github.io/c-comp/advanced/F0_cyk/) にあります。

## 今日のゴール

数式の文字列をトークン列に区切り（字句解析）、CYK 法で構文木を組み立て（構文解析）、
木を評価して値を出すところまでを、独立した小さなプログラムで体験します。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | コマ1（`eval_ast`）まで |
| 推奨の前提 | — |
| 改変しない | `mycc.py`、`scaffold/`（この回はコンパイラ本編と独立している） |
| 編集する | `cyk.py` |
| 完了条件 | `check.py` の全 Step が PASS になる（このトピックに `golden.py` は無い） |
| コマ数 | 1 |
| 備考 | フロントエンド発展シリーズの第0回。対象にする言語は、整数と `+` `*` `(` `)` だけの数式である |

## 編集するファイル

- `cyk.py`（Step 1〜5 の TODO を上から順に実装する）

## 動かし方

```bash
python3 cyk.py '1 + 2 * 3'
python3 cyk.py --table '1 + 2 * 3'   # CYK の表も表示する
```

## テスト

```bash
python3 check.py
```

Step ごとに PASS / FAIL / SKIP が表示されます。
未実装の Step は SKIP になるので、途中まででも確認できます。
