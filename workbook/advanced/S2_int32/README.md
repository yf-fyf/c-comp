# S2: `int` は32ビット — 桁あふれを正しく折り返す

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/S2_int32/](https://yf-fyf.github.io/c-comp/advanced/S2_int32/) にあります。

## 今日のゴール

`int` の演算を32bit命令(`addw` など)で行い、桁あふれが C のとおりに折り返すようにする。

前提はコマ10 まで。**`mycc.py` は書き換えません**（`semcc.py` が `emit` を包みます）。

## 編集するファイル

- `narrow.py`（Step 1: narrow）

## テスト

```bash
python3 check.py     # narrow の入出力を直接確認(未実装は SKIP)
python3 golden.py    # 折り返しのテスト + fixed15
```

`tests/pointer_ok.c` は「直しすぎ(アドレス計算まで32bit化)」を検出するための安全網です。
