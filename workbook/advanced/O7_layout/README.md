# O7: ブロック整列とループ回転

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O7_layout/](https://yf-fyf.github.io/c-comp/advanced/O7_layout/) にあります。

## 今日のゴール

ループが**毎回実行している「条件へ戻るジャンプ」**を消す。
静的命令数はほとんど変わらないのに、動的命令数が減ることを測って確かめる。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | O1（測定基盤。動的命令数の物差しが要る）、O2（`loop_headers` が `cfg.py` の後方辺を使う） |
| 推奨の前提 | O3（命令選択）。実質必須に近い。「動かし方」も「測ってみると」も `--passes isel,layout` を O1 の全構成の基準表の `+isel` 列と比べるので、O3 が無いと基準がそろわない |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `layout.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `fixed17` 全通と動的命令数の削減を報告する |
| コマ数 | 1 |
| 備考 | 最適化発展シリーズの第7回。この回は静的命令数では効果が見えない。Step 3 の `remove_jump_to_next` は B1 の Step 3 と同名・同一の最適化である |

## 編集するファイル

- `layout.py`（Step 1: `invert_branch`、Step 2: `rotate_one` / `rotate_loops`、
  Step 3: `remove_jump_to_next`、Step 4: `run`）

ループの入口を探す `loop_headers` は、O2 の `cfg.py` の**後方辺**を使って
書いてあります（完成済み）。O2 が未完成だと、ここで止まります。

Step 3 の `remove_jump_to_next` は、**B1 の Step 3 と同名・同一の最適化**です。
B1 を先にやっているなら `peephole.py` の実装をそのまま持ち込めます。
それでもこの回に要るのは、ループ回転が新しい「次の行へのジャンプ」を作るからです。

## 動かし方

```bash
python3 ../optcc.py --passes isel,layout ../O1_measure/bench/loop_sum.c
python3 ../optcc.py --passes isel        ../O1_measure/bench/loop_sum.c   # 回転なし
```

## テスト

```bash
python3 check.py     # 反転表と回転の単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 + ベンチマーク + 静的/動的の比較
```

`golden.py` は**動的命令数で合否を判定**します。この回は静的では効果が見えません。
