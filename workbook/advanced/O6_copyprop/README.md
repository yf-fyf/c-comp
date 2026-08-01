# O6: コピー伝播と死コード除去（2コマ）

この回の資料は [https://yf-fyf.github.io/c-comp/advanced/O6_copyprop/](https://yf-fyf.github.io/c-comp/advanced/O6_copyprop/) にあります。

## 今日のゴール

O4 が残した `mv a0, s1` の連なりを消す。
そして「**同じパスでも、前に何を掛けたかで効果が変わる**」ことを測って確かめる。

## この回の位置づけ

| 項目 | 内容 |
|------|------|
| 必須の前提 | O1（測定基盤）、O2（フローグラフ）、O4（これが無いと消す対象の `mv` が出てこない）、O5（生存解析） |
| 推奨の前提 | O3（命令選択）。実質必須に近い。資料の「測ってみると」の比較表が「isel だけ」を基準にしているので、O3 が無いと表と突き合わせられない |
| 改変しない | `mycc.py`、`scaffold/`、`optcc.py` |
| 編集する | `copyprop.py`、`dce.py` |
| 完了条件 | `check.py` の全 Step が PASS になり、`golden.py` が `fixed17` 全通と4構成の比較表を報告する |
| コマ数 | 2 |
| 備考 | 最適化発展シリーズの第6回。コマ1は `copyprop.py`（Step 1〜3）、コマ2は `dce.py`（Step 4〜6） |

## 2コマの区切り

| コマ | やること | 到達点 |
|------|----------|--------|
| 1 | Step 1〜3（`copyprop.py`） | `check.py` の Step 1〜3 が PASS。命令数はまだ減らない |
| 2 | Step 4〜6（`dce.py`） | `golden.py` が4構成の比較表を出す |

コマ1の終わりで区切れます。コピー伝播だけでは命令が減らないので、
**そこで止めると効果がゼロに見える** —— それ自体がコマ2への動機になります。

## 編集するファイル

- `copyprop.py`（Step 1: `replace_uses`、Step 2: `copy_prop_block`、Step 3: `run`）
- `dce.py`（Step 4: `has_side_effect`、Step 5: `is_dead`、Step 6: `run`）

## 動かし方

```bash
B=../O1_measure/bench/loop_sum.c
python3 ../optcc.py --regalloc --passes isel,copyprop,dce $B
python3 ../optcc.py --regalloc --passes isel              $B
python3 ../optcc.py            --passes isel,copyprop,dce $B
```

3つ目（レジスタ割り当てなし）がほとんど何も減らないことを、自分で確かめてください。

## テスト

```bash
python3 check.py     # 各関数の単体テスト(未実装は SKIP)
python3 golden.py    # fixed17 + 4構成の比較表
```
