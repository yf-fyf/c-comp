# コマ6: while / for / break / continue

この回の資料は [https://yf-fyf.github.io/c-comp/sessions/06_loops/](https://yf-fyf.github.io/c-comp/sessions/06_loops/) にあります。

## 今日のゴール

ループとジャンプ制御、そして前置 `++`/`--` を実装する。条件判定・反復・途中脱出・スキップを正しく生成できるようにする。

## 実装する主な機能

- while文・for文をコード生成する
- break文・continue文を扱う
- 入れ子ループとループ内の if を扱う
- 前置 `++`/`--` をコード生成する

## 編集するファイル

- `mycc.py`

## テスト

```bash
python3 scaffold/test_runner.py sessions/06_loops
```
