# O6: コピー伝播と死コード除去(2コマ)

この回の資料は `handout.pdf` を参照してください。

## 今日のゴール

O4 が残した `mv a0, s1` の連なりを消す。
そして「**同じパスでも、前に何を掛けたかで効果が変わる**」ことを測って確かめる。

## 前提

| 種別 | 内容 |
|------|------|
| **必須** | O2(`cfg.py`)、O5(`liveness.py`) |
| **必須** | O4(`regalloc.py`)—— これが無いと消す対象の `mv` が出てこない |
| **必須** | O1(`measure.py`)—— `golden.py` が効果の測定に使う |
| 推奨 | O3(命令選択) |

## 2コマの区切り

| コマ | やること | 到達点 |
|------|----------|--------|
| 1 | Step 1〜3(`copyprop.py`) | `check.py` の Step 1〜3 が PASS。命令数はまだ減らない |
| 2 | Step 4〜6(`dce.py`) | `golden.py` が4構成の比較表を出す |

コマ1の終わりで区切れます。コピー伝播だけでは命令が減らないので、
**そこで止めると効果がゼロに見える** —— それ自体がコマ2への動機になります。

## 編集するファイル

- `copyprop.py`(Step 1: `replace_uses`、Step 2: `copy_prop_block`、Step 3: `run`)
- `dce.py`(Step 4: `has_side_effect`、Step 5: `is_dead`、Step 6: `run`)

## 動かし方

```bash
B=../O1_measure/bench/loop_sum.c
python3 ../optcc.py --regalloc --passes isel,copyprop,dce $B
python3 ../optcc.py --regalloc --passes isel              $B
python3 ../optcc.py            --passes isel,copyprop,dce $B
```

3つ目(レジスタ割り当てなし)がほとんど何も減らないことを、自分で確かめてください。

## テスト

```bash
python3 check.py     # 各関数の単体テスト(未実装は SKIP)
python3 golden.py    # fixed15 + 4構成の比較表
```
