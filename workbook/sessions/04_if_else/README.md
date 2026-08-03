# コマ4: if/else + 比較演算

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/04_if_else/](https://yf-fyf.github.io/c-comp/sessions/04_if_else/) にあります。

## 今日のゴール

条件分岐と比較演算、そして三項演算子を実装する。条件式の結果に応じて、then側かelse側のどちらかの文だけを実行できるようにする。

## 実装する主な機能

- 比較演算（`>` `==` `<=` など）をコード生成する
- if文・if/else文・else ifをコード生成する
- 入れ子の if 文とブロックを扱う
- 三項演算子（`a > b ? a : b`）をコード生成する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/04_if_else
```
