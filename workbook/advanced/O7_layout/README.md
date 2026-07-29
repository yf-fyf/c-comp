# O7: ブロック整列とループ回転

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O7_layout/](https://yf-fyf.github.io/c-comp/advanced/O7_layout/) にあります。

## 今日のゴール

ループが**毎回実行している「条件へ戻るジャンプ」**を消す。
静的命令数はほとんど変わらないのに、動的命令数が減ることを測って確かめる。

前提は O1(測定基盤)と O2(フローグラフ)。**`mycc.py` は書き換えません**。

## 編集するファイル

- `layout.py`(Step 1: `invert_branch`、Step 2: `rotate_one` / `rotate_loops`、
  Step 3: `remove_jump_to_next`、Step 4: `run`)

ループの入口を探す `loop_headers` は、O2 の `cfg.py` の**後方辺**を使って
書いてあります(完成済み)。O2 が未完成だと、ここで止まります。

## 動かし方

```bash
python3 ../optcc.py --passes isel,layout ../O1_measure/bench/loop_sum.c
python3 ../optcc.py --passes isel        ../O1_measure/bench/loop_sum.c   # 回転なし
```

## テスト

```bash
python3 check.py     # 反転表と回転の単体テスト(未実装は SKIP)
python3 golden.py    # fixed15 + ベンチマーク + 静的/動的の比較
```

`golden.py` は**動的命令数で合否を判定**します。この回は静的では効果が見えません。
